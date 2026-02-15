"""Extract data models and types from frontend code."""

import logging
import re
from pathlib import Path

from core.types import DataModel, FieldInfo, SymbolKind
from core.utils import generate_id
from indexers.unified_indexer import UnifiedIndexer

logger = logging.getLogger(__name__)


class TypeExtractor:
    """Extract data models from TypeScript types/interfaces."""

    def __init__(self, project_root: Path):
        self.root = project_root

    async def extract_all(self, indexer: UnifiedIndexer) -> list[DataModel]:
        """Extract all data models from indexed types."""
        models = []
        seen = set()

        # Extract from interfaces
        for sym in indexer.symbol_table.get_by_kind(SymbolKind.INTERFACE):
            model = self._parse_type_symbol(sym)
            if model and model.name not in seen and self._is_data_model(model):
                seen.add(model.name)
                models.append(model)

        # Extract from type aliases
        for sym in indexer.symbol_table.get_by_kind(SymbolKind.TYPE_ALIAS):
            model = self._parse_type_symbol(sym)
            if model and model.name not in seen and self._is_data_model(model):
                seen.add(model.name)
                models.append(model)

        # Extract from classes with decorators
        for sym in indexer.symbol_table.get_by_kind(SymbolKind.CLASS):
            if self._is_model_class(sym):
                model = self._parse_class(sym)
                if model and model.name not in seen:
                    seen.add(model.name)
                    models.append(model)

        # Extract from enums
        for sym in indexer.symbol_table.get_by_kind(SymbolKind.ENUM):
            enum_model = self._parse_enum(sym)
            if enum_model and enum_model.name not in seen:
                seen.add(enum_model.name)
                models.append(enum_model)

        # Extract Zod inferred types (z.infer<typeof xxxSchema>)
        zod_models = await self._extract_zod_inferred_types(indexer)
        for model in zod_models:
            if model.name not in seen:
                seen.add(model.name)
                models.append(model)

        # Extract Prisma model types
        prisma_models = await self._extract_prisma_types(indexer)
        for model in prisma_models:
            if model.name not in seen:
                seen.add(model.name)
                models.append(model)

        logger.info(f"Extracted {len(models)} data models")
        return models

    def _parse_enum(self, symbol) -> DataModel | None:
        """Parse an enum symbol into a DataModel with enum values."""
        source = symbol.metadata.get("source", symbol.signature)
        if not source:
            return None

        # Extract enum values
        fields = []
        for match in re.finditer(r'(\w+)\s*=\s*[\'"`]?([^\'"`\n,}]+)[\'"`]?', source):
            name, value = match.groups()
            fields.append(FieldInfo(
                name=name,
                field_type="enum_value",
                metadata={"value": value.strip()}
            ))

        if not fields:
            # Try const enum pattern: enum X { A, B, C }
            for match in re.finditer(r'^\s*(\w+)(?:\s*,)?$', source, re.MULTILINE):
                fields.append(FieldInfo(
                    name=match.group(1),
                    field_type="enum_value",
                ))

        if not fields:
            return None

        return DataModel(
            id=generate_id(),
            name=symbol.name,
            fields=fields,
            source_file=symbol.file,
            source=source,
        )

    async def _extract_zod_inferred_types(self, indexer: UnifiedIndexer) -> list[DataModel]:
        """Extract type definitions inferred from Zod schemas."""
        from config.settings import Language
        models = []

        for file_info in indexer.file_index.all_files():
            if file_info.language not in (Language.TYPESCRIPT, Language.TSX):
                continue

            content = indexer.get_file_content(file_info.path)
            if not content or "z.object" not in content:
                continue

            # Find: type User = z.infer<typeof userSchema>
            for match in re.finditer(
                r'type\s+(\w+)\s*=\s*z\.infer<typeof\s+(\w+)Schema>',
                content
            ):
                type_name = match.group(1)
                schema_name = match.group(2)

                # Find the corresponding schema definition
                schema_match = re.search(
                    rf'const\s+{schema_name}Schema\s*=\s*z\.object\(\s*\{{([^}}]+)\}}',
                    content,
                    re.DOTALL
                )
                if schema_match:
                    fields = self._parse_zod_schema_fields(schema_match.group(1))
                    if fields:
                        models.append(DataModel(
                            id=generate_id(),
                            name=type_name,
                            fields=fields,
                            source_file=file_info.path,
                            source=schema_match.group(0),
                        ))

        return models

    def _parse_zod_schema_fields(self, schema_body: str) -> list[FieldInfo]:
        """Parse fields from Zod schema body."""
        fields = []
        zod_type_map = {
            "string": "string", "number": "number", "boolean": "boolean",
            "date": "datetime", "array": "array", "object": "json",
            "enum": "enum", "bigint": "number", "uuid": "uuid",
        }

        for match in re.finditer(r'(\w+)\s*:\s*z\.(\w+)\(\)', schema_body):
            field_name = match.group(1)
            zod_type = match.group(2).lower()
            field_type = zod_type_map.get(zod_type, "string")

            is_optional = ".optional()" in schema_body[match.end():match.end()+20]

            fields.append(FieldInfo(
                name=field_name,
                field_type=field_type,
                required=not is_optional,
            ))

        return fields

    async def _extract_prisma_types(self, indexer: UnifiedIndexer) -> list[DataModel]:
        """Extract types imported from @prisma/client."""
        from config.settings import Language
        models = []

        for file_info in indexer.file_index.all_files():
            if file_info.language not in (Language.TYPESCRIPT, Language.TSX):
                continue

            content = indexer.get_file_content(file_info.path)
            if not content or "@prisma/client" not in content:
                continue

            # Find: import { User, Post } from '@prisma/client'
            for match in re.finditer(
                r"import\s*\{([^}]+)\}\s*from\s*['\"]@prisma/client['\"]",
                content
            ):
                imports = match.group(1)
                for type_match in re.finditer(r'(\w+)', imports):
                    type_name = type_match.group(1)
                    # Skip Prisma utility types
                    if type_name.startswith("Prisma") or type_name in ("$Enums",):
                        continue
                    # Create a placeholder model (actual fields from schema.prisma)
                    models.append(DataModel(
                        id=generate_id(),
                        name=type_name,
                        fields=[FieldInfo(name="id", field_type="string")],
                        source_file=file_info.path,
                        source=f"Prisma model: {type_name}",
                    ))

        return models


    def _parse_type_symbol(self, symbol) -> DataModel | None:
        """Parse a type/interface symbol into a DataModel."""
        source = symbol.metadata.get("source", symbol.signature)
        if not source:
            return None

        match = re.search(r"\{([^}]+)\}", source, re.DOTALL)
        if not match:
            return None

        fields = []
        body = match.group(1)

        for m in re.finditer(r"(?:readonly\s+)?(\w+)\s*(\?)?\s*:\s*([^;,\n]+)", body):
            name, optional, type_str = m.groups()
            field = self._parse_field(name, type_str.strip(), optional is not None)
            if field:
                fields.append(field)

        if not fields:
            return None

        return DataModel(
            id=generate_id(),
            name=symbol.name,
            fields=fields,
            source_file=symbol.file,
            source=source,
        )

    def _parse_field(
        self, name: str, type_str: str, is_optional: bool
    ) -> FieldInfo | None:
        """Parse a field definition."""
        is_array = type_str.endswith("[]") or type_str.startswith("Array<")
        if is_array:
            type_str = re.sub(r"\[\]$", "", type_str)
            type_str = re.sub(r"^Array<(.+)>$", r"\1", type_str)

        is_nullable = "| null" in type_str or "| undefined" in type_str
        type_str = re.sub(r"\s*\|\s*(null|undefined)", "", type_str).strip()

        base_type = self._map_type(type_str)

        # Infer validation from name
        min_len = max_len = None
        pattern = None
        name_lower = name.lower()

        if "email" in name_lower:
            pattern = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
        elif "password" in name_lower:
            min_len = 8
        elif "phone" in name_lower:
            pattern = r"^\+?[\d\s-]{10,}$"
        elif "url" in name_lower:
            pattern = r"^https?://.+"

        return FieldInfo(
            name=name,
            field_type=base_type,
            required=not is_optional,
            array=is_array,
            nullable=is_nullable,
            min_length=min_len,
            max_length=max_len,
            pattern=pattern,
        )

    def _map_type(self, ts_type: str) -> str:
        """Map TypeScript type to generic type."""
        mapping = {
            "string": "string",
            "number": "number",
            "boolean": "boolean",
            "Date": "datetime",
            "any": "json",
            "object": "json",
            "unknown": "json",
            "bigint": "number",
        }

        if ts_type.lower() in mapping:
            return mapping[ts_type.lower()]
        if ts_type in mapping:
            return mapping[ts_type]
        if ts_type.startswith("Record<") or ts_type.startswith("Map<"):
            return "json"
        if ts_type[0].isupper():
            return f"relation:{ts_type}"
        return "string"

    def _is_data_model(self, model: DataModel) -> bool:
        """
        Check if this looks like a data model using enhanced filtering.
        
        Uses centralized domain_model_filter with file path awareness.
        """
        from utils.domain_model_filter import is_domain_model
        
        # Use centralized filter with file path
        if not is_domain_model(model.name, model.source_file):
            return False
        
        # Additional field-based validation
        field_names = {f.name.lower() for f in model.fields}
        indicators = {
            # Common data model indicators
            "id",
            "uuid",
            "name",
            "email",
            "title",
            "description",
            "createdat",
            "created_at",
            "updatedat",
            "updated_at",
            "userid",
            "user_id",
            "status",
            # E-commerce specific indicators
            "price",
            "stock",
            "quantity",
            "category",
            "image",
            "total",
            "items",
            "product",
            "productid",
            "product_id",
            "orderid",
            "order_id",
            "shippingaddress",
            "shipping_address",
            "fullname",
            "full_name",
            "street",
            "city",
            "zipcode",
            "zip_code",
            "country",
            # Auth indicators (but not for form data!)
            "token",
            "role",
        }
        
        # Must have at least one domain model indicator field
        # BUT exclude if it has "password" field AND ends with FormData/Form
        has_password = "password" in field_names
        name_lower = model.name.lower()
        is_form_type = name_lower.endswith("formdata") or name_lower.endswith("form") or name_lower.endswith("schema")
        
        # If it's a form type with password, exclude it
        if is_form_type and has_password:
            return False
        
        return bool(field_names & indicators)

    def _is_model_class(self, symbol) -> bool:
        """Check if class is a data model."""
        if symbol.decorators:
            orm_decorators = ["Entity", "Table", "Model", "Schema"]
            return any(
                any(d in dec for d in orm_decorators) for dec in symbol.decorators
            )
        return False

    def _parse_class(self, symbol) -> DataModel | None:
        """Parse a class as a data model."""
        fields = []

        source = symbol.metadata.get("source", symbol.signature)
        for m in re.finditer(
            r"(?:@\w+\([^)]*\)\s*)*(\w+)\s*(?::\s*([^;=]+))?(?:\s*=\s*[^;]+)?;", source
        ):
            name = m.group(1)
            type_str = m.group(2) or "any"
            field = self._parse_field(name.strip(), type_str.strip(), False)
            if field:
                fields.append(field)

        if not fields:
            return None

        return DataModel(
            id=generate_id(),
            name=symbol.name,
            fields=fields,
            source_file=symbol.file,
            source=source,
        )
