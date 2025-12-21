"""Extract data models and types from frontend code."""

import re
import logging
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

        logger.info(f"Extracted {len(models)} data models")
        return models

    def _parse_type_symbol(self, symbol) -> DataModel | None:
        """Parse a type/interface symbol into a DataModel."""
        source = symbol.metadata.get('source', symbol.signature)
        if not source:
            return None

        match = re.search(r'\{([^}]+)\}', source, re.DOTALL)
        if not match:
            return None

        fields = []
        body = match.group(1)

        for m in re.finditer(r'(?:readonly\s+)?(\w+)\s*(\?)?\s*:\s*([^;,\n]+)', body):
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
            source=source
        )

    def _parse_field(self, name: str, type_str: str, is_optional: bool) -> FieldInfo | None:
        """Parse a field definition."""
        is_array = type_str.endswith('[]') or type_str.startswith('Array<')
        if is_array:
            type_str = re.sub(r'\[\]$', '', type_str)
            type_str = re.sub(r'^Array<(.+)>$', r'\1', type_str)

        is_nullable = '| null' in type_str or '| undefined' in type_str
        type_str = re.sub(r'\s*\|\s*(null|undefined)', '', type_str).strip()

        base_type = self._map_type(type_str)

        # Infer validation from name
        min_len = max_len = None
        pattern = None
        name_lower = name.lower()

        if 'email' in name_lower:
            pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        elif 'password' in name_lower:
            min_len = 8
        elif 'phone' in name_lower:
            pattern = r'^\+?[\d\s-]{10,}$'
        elif 'url' in name_lower:
            pattern = r'^https?://.+'

        return FieldInfo(
            name=name,
            field_type=base_type,
            required=not is_optional,
            array=is_array,
            nullable=is_nullable,
            min_length=min_len,
            max_length=max_len,
            pattern=pattern
        )

    def _map_type(self, ts_type: str) -> str:
        """Map TypeScript type to generic type."""
        mapping = {
            'string': 'string', 'number': 'number', 'boolean': 'boolean',
            'Date': 'datetime', 'any': 'json', 'object': 'json',
            'unknown': 'json', 'bigint': 'number',
        }
        
        if ts_type.lower() in mapping:
            return mapping[ts_type.lower()]
        if ts_type in mapping:
            return mapping[ts_type]
        if ts_type.startswith('Record<') or ts_type.startswith('Map<'):
            return 'json'
        if ts_type[0].isupper():
            return f'relation:{ts_type}'
        return 'string'

    def _is_data_model(self, model: DataModel) -> bool:
        """Check if this looks like a data model."""
        skip_suffixes = ['props', 'state', 'context', 'handler', 'config', 
                        'options', 'params', 'settings', 'theme', 'style']
        
        name_lower = model.name.lower()
        if any(name_lower.endswith(s) for s in skip_suffixes):
            return False

        field_names = {f.name.lower() for f in model.fields}
        indicators = {'id', 'uuid', 'name', 'email', 'title', 'description',
                     'createdat', 'created_at', 'updatedat', 'updated_at',
                     'userid', 'user_id', 'status'}
        
        return bool(field_names & indicators)

    def _is_model_class(self, symbol) -> bool:
        """Check if class is a data model."""
        if symbol.decorators:
            orm_decorators = ['Entity', 'Table', 'Model', 'Schema']
            return any(any(d in dec for d in orm_decorators) for dec in symbol.decorators)
        return False

    def _parse_class(self, symbol) -> DataModel | None:
        """Parse a class as a data model."""
        fields = []
        
        source = symbol.metadata.get('source', symbol.signature)
        for m in re.finditer(r'(?:@\w+\([^)]*\)\s*)*(\w+)\s*(?::\s*([^;=]+))?(?:\s*=\s*[^;]+)?;', source):
            name = m.group(1)
            type_str = m.group(2) or 'any'
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
            source=source
        )