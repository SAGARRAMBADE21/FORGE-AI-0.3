"""Collect evidence from frontend code for inference."""

import logging
import re
from pathlib import Path

from analyzers.frontend_analyzer import FrontendAnalyzer
from config.settings import Language
from core.types import (
    APICall,
    AuthPattern,
    DataModel,
    Evidence,
    EvidenceSource,
    FieldInfo,
    FormInfo,
)
from indexers.unified_indexer import UnifiedIndexer

logger = logging.getLogger(__name__)


class EvidenceCollector:
    """Collect evidence from multiple sources."""

    def __init__(self, indexer: UnifiedIndexer):
        self._indexer = indexer

    async def collect_all(self, analysis) -> dict[str, list[Evidence]]:
        """Collect all evidence organized by model name."""
        evidence_map: dict[str, list[Evidence]] = {}

        # From TypeScript types
        for model in analysis.data_models:
            self._add_type_evidence(model, evidence_map)

        # From API calls
        for api in analysis.api_calls:
            self._add_api_evidence(api, evidence_map)

        # From forms
        for form in analysis.forms:
            self._add_form_evidence(form, evidence_map)

        # From Zod schemas
        await self._collect_zod_evidence(evidence_map)

        # From state management
        await self._collect_state_evidence(evidence_map)

        logger.info(f"Collected evidence for {len(evidence_map)} potential models")
        return evidence_map

    def _add_type_evidence(self, model: DataModel, evidence_map: dict):
        """Add evidence from TypeScript type."""
        name = model.name
        if name not in evidence_map:
            evidence_map[name] = []

        evidence_map[name].append(
            Evidence(
                source=EvidenceSource.TYPESCRIPT_TYPE,
                file=model.source_file or "",
                line=0,
                content=model.source,
                confidence=0.9,
                metadata={
                    "fields": [
                        {
                            "name": f.name,
                            "type": f.field_type,
                            "required": f.required,
                            "array": f.array,
                            "nullable": f.nullable,
                        }
                        for f in model.fields
                    ],
                    "relationships": [
                        {"type": r.type, "target": r.target, "field": r.field}
                        for r in model.relationships
                    ],
                },
            )
        )

    def _add_api_evidence(self, api: APICall, evidence_map: dict):
        """Add evidence from API call."""
        # Extract model name from endpoint
        model_name = self._extract_model_from_endpoint(api.endpoint)
        if not model_name:
            return

        if model_name not in evidence_map:
            evidence_map[model_name] = []

        evidence_map[model_name].append(
            Evidence(
                source=EvidenceSource.API_RESPONSE,
                file=api.file,
                line=api.line,
                content=api.source,
                confidence=0.7,
                metadata={
                    "endpoint": api.endpoint,
                    "method": api.method.value,
                    "response_type": api.response_type,
                    "body_type": api.body_type,
                    "path_params": api.path_params,
                    "query_params": api.query_params,
                },
            )
        )

    def _add_form_evidence(self, form: FormInfo, evidence_map: dict):
        """Add evidence from form."""
        # Try to extract model name from form context
        model_name = self._extract_model_from_form(form)
        if not model_name:
            return

        if model_name not in evidence_map:
            evidence_map[model_name] = []

        evidence_map[model_name].append(
            Evidence(
                source=EvidenceSource.FORM_STATE,
                file=form.file,
                line=0,
                content=str(form.fields),
                confidence=0.6,
                metadata={
                    "fields": [
                        {
                            "name": f.name,
                            "input_type": f.field_type,
                            "required": f.required,
                            "min_length": f.min_length,
                            "max_length": f.max_length,
                            "pattern": f.pattern,
                        }
                        for f in form.fields
                    ],
                    "submit_endpoint": form.submit_endpoint,
                },
            )
        )

    async def _collect_zod_evidence(self, evidence_map: dict):
        """Collect evidence from Zod schemas."""
        for file_info in self._indexer.file_index.all_files():
            if file_info.language not in (Language.TYPESCRIPT, Language.TSX):
                continue

            content = self._indexer.get_file_content(file_info.path)
            if not content or "z.object" not in content:
                continue

            # Find Zod schema definitions
            for match in re.finditer(
                r"(?:const|let|export\s+const)\s+(\w+)Schema\s*=\s*z\.object\(\{([^}]+)\}",
                content,
                re.DOTALL,
            ):
                schema_name = match.group(1)
                schema_body = match.group(2)
                line_num = content[: match.start()].count("\n")

                # Capitalize first letter for model name
                model_name = schema_name[0].upper() + schema_name[1:]

                if model_name not in evidence_map:
                    evidence_map[model_name] = []

                # Parse Zod fields
                fields = self._parse_zod_fields(schema_body)

                evidence_map[model_name].append(
                    Evidence(
                        source=EvidenceSource.ZOD_SCHEMA,
                        file=file_info.path,
                        line=line_num,
                        content=match.group(0),
                        confidence=0.95,
                        metadata={"fields": fields},
                    )
                )

    def _parse_zod_fields(self, schema_body: str) -> list[dict]:
        """Parse Zod schema fields."""
        fields = []

        for match in re.finditer(r"(\w+)\s*:\s*z\.(\w+)\(\)", schema_body):
            field_name = match.group(1)
            zod_type = match.group(2)

            type_map = {
                "string": "string",
                "number": "integer",
                "boolean": "boolean",
                "date": "datetime",
                "array": "array",
                "object": "json",
            }

            fields.append(
                {
                    "name": field_name,
                    "type": type_map.get(zod_type, "string"),
                    "required": ".optional()"
                    not in schema_body[match.end() : match.end() + 20],
                }
            )

        return fields

    async def _collect_state_evidence(self, evidence_map: dict):
        """Collect evidence from state management."""
        for file_info in self._indexer.file_index.all_files():
            if file_info.language not in (Language.TYPESCRIPT, Language.TSX):
                continue

            content = self._indexer.get_file_content(file_info.path)
            if not content:
                continue

            # Zustand stores
            for match in re.finditer(r"create<(\w+)State>", content):
                model_name = match.group(1)
                line_num = content[: match.start()].count("\n")

                if model_name not in evidence_map:
                    evidence_map[model_name] = []

                evidence_map[model_name].append(
                    Evidence(
                        source=EvidenceSource.STATE_MANAGEMENT,
                        file=file_info.path,
                        line=line_num,
                        content=content[match.start() : match.start() + 200],
                        confidence=0.5,
                        metadata={"store_type": "zustand"},
                    )
                )

    def _extract_model_from_endpoint(self, endpoint: str) -> str | None:
        """Extract model name from API endpoint."""
        # /api/users -> User
        # /api/v1/products/:id -> Product
        parts = endpoint.strip("/").split("/")

        for part in reversed(parts):
            if part.startswith(":") or part.startswith("{"):
                continue
            if part in ("api", "v1", "v2", "v3"):
                continue

            # Singularize and capitalize
            name = part.rstrip("s")
            return name[0].upper() + name[1:] if name else None

        return None

    def _extract_model_from_form(self, form: FormInfo) -> str | None:
        """Extract model name from form context."""
        if form.submit_endpoint:
            return self._extract_model_from_endpoint(form.submit_endpoint)

        if form.component:
            # UserForm -> User, CreatePostForm -> Post
            name = form.component
            for suffix in ("Form", "Dialog", "Modal", "Create", "Edit", "Update"):
                name = name.replace(suffix, "")
            return name if name else None

        return None
