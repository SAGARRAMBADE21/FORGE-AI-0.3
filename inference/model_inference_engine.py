"""Engine for inferring data models from frontend evidence."""

import logging
import re
from collections import defaultdict
from dataclasses import dataclass

from core.types import (
    Evidence,
    EvidenceSource,
    InferredField,
    InferredFieldType,
    InferredModel,
    InferredRelationType,
)
from core.utils import generate_id

logger = logging.getLogger(__name__)


@dataclass
class FieldCandidate:
    """Candidate field from evidence."""

    name: str
    field_type: InferredFieldType
    nullable: bool = False
    unique: bool = False
    indexed: bool = False
    evidence: list[Evidence] = None
    confidence: float = 0.0
    constraints: dict = None

    def __post_init__(self):
        if self.evidence is None:
            self.evidence = []
        if self.constraints is None:
            self.constraints = {}


class ModelInferenceEngine:
    """
    Infer data models from frontend evidence.

    Process:
    1. Collect evidence from multiple sources
    2. Cluster related evidence by model name
    3. Merge field definitions
    4. Resolve conflicts (deterministic first, LLM for ambiguous)
    5. Infer relationships
    """

    def __init__(self, llm_client=None):
        self._llm = llm_client

    async def infer_models(
        self, evidence_map: dict[str, list[Evidence]]
    ) -> list[InferredModel]:
        """Infer models from collected evidence."""
        models = []

        for model_name, evidences in evidence_map.items():
            model = await self._infer_single_model(model_name, evidences)
            if model and model.fields:
                models.append(model)

        # Post-process: identify common patterns
        models = self._add_common_fields(models)
        models = self._infer_indexes(models)

        logger.info(f"Inferred {len(models)} models")
        return models

    async def _infer_single_model(
        self, name: str, evidences: list[Evidence]
    ) -> InferredModel | None:
        """Infer a single model from its evidence."""
        if not evidences:
            return None

        # Collect all field candidates
        field_candidates: dict[str, list[FieldCandidate]] = defaultdict(list)

        for evidence in evidences:
            candidates = self._extract_field_candidates(evidence)
            for candidate in candidates:
                field_candidates[candidate.name].append(candidate)

        # Merge candidates into final fields
        fields = []
        for field_name, candidates in field_candidates.items():
            merged = await self._merge_field_candidates(field_name, candidates)
            if merged:
                fields.append(merged)

        if not fields:
            return None

        # Calculate overall confidence
        confidence = sum(e.confidence for e in evidences) / len(evidences)

        return InferredModel(
            name=name,
            fields=fields,
            primary_key="id",
            timestamps=self._should_have_timestamps(name, fields),
            soft_delete=self._should_have_soft_delete(name, fields),
            evidence=evidences,
            confidence=confidence,
        )

    def _extract_field_candidates(self, evidence: Evidence) -> list[FieldCandidate]:
        """Extract field candidates from a single evidence."""
        candidates = []

        if evidence.source == EvidenceSource.TYPESCRIPT_TYPE:
            candidates.extend(self._from_typescript(evidence))
        elif evidence.source == EvidenceSource.ZOD_SCHEMA:
            candidates.extend(self._from_zod(evidence))
        elif evidence.source == EvidenceSource.API_RESPONSE:
            candidates.extend(self._from_api(evidence))
        elif evidence.source == EvidenceSource.FORM_STATE:
            candidates.extend(self._from_form(evidence))
        elif evidence.source == EvidenceSource.VALIDATION_RULE:
            candidates.extend(self._from_validation(evidence))

        return candidates

    def _from_typescript(self, evidence: Evidence) -> list[FieldCandidate]:
        """Extract candidates from TypeScript type."""
        candidates = []
        fields = evidence.metadata.get("fields", [])

        for f in fields:
            field_type = self._map_ts_type(f.get("type", "string"))

            candidates.append(
                FieldCandidate(
                    name=f["name"],
                    field_type=field_type,
                    nullable=f.get("nullable", False) or not f.get("required", True),
                    evidence=[evidence],
                    confidence=evidence.confidence,
                )
            )

        return candidates

    def _from_zod(self, evidence: Evidence) -> list[FieldCandidate]:
        """Extract candidates from Zod schema."""
        candidates = []
        fields = evidence.metadata.get("fields", [])

        for f in fields:
            field_type = self._map_ts_type(f.get("type", "string"))

            candidates.append(
                FieldCandidate(
                    name=f["name"],
                    field_type=field_type,
                    nullable=not f.get("required", True),
                    evidence=[evidence],
                    confidence=evidence.confidence,
                    constraints=self._extract_zod_constraints(f),
                )
            )

        return candidates

    def _from_api(self, evidence: Evidence) -> list[FieldCandidate]:
        """Extract candidates from API response."""
        candidates = []

        # Infer fields from path params
        for param in evidence.metadata.get("path_params", []):
            if param.endswith("Id"):
                candidates.append(
                    FieldCandidate(
                        name=param,
                        field_type=InferredFieldType.STRING,
                        indexed=True,
                        evidence=[evidence],
                        confidence=0.6,
                    )
                )

        # Infer from response type if it's a known type
        response_type = evidence.metadata.get("response_type")
        if response_type:
            # Could do more sophisticated type analysis here
            pass

        return candidates

    def _from_form(self, evidence: Evidence) -> list[FieldCandidate]:
        """Extract candidates from form fields."""
        candidates = []
        fields = evidence.metadata.get("fields", [])

        for f in fields:
            field_type = self._map_input_type(f.get("input_type", "text"))

            constraints = {}
            if f.get("min_length"):
                constraints["min_length"] = f["min_length"]
            if f.get("max_length"):
                constraints["max_length"] = f["max_length"]
            if f.get("pattern"):
                constraints["pattern"] = f["pattern"]

            candidates.append(
                FieldCandidate(
                    name=f["name"],
                    field_type=field_type,
                    nullable=not f.get("required", False),
                    evidence=[evidence],
                    confidence=evidence.confidence,
                    constraints=constraints,
                )
            )

        return candidates

    def _from_validation(self, evidence: Evidence) -> list[FieldCandidate]:
        """Extract candidates from validation rules."""
        # Validation rules provide constraint info
        return []

    async def _merge_field_candidates(
        self, name: str, candidates: list[FieldCandidate]
    ) -> InferredField | None:
        """Merge multiple candidates into a single field."""
        if not candidates:
            return None

        # Skip internal fields
        if name in ("__typename", "_id"):
            return None

        # Group by type
        type_counts: dict[InferredFieldType, int] = defaultdict(int)
        for c in candidates:
            type_counts[c.field_type] += 1

        # Determine type by majority vote
        if len(type_counts) == 1:
            final_type = list(type_counts.keys())[0]
        else:
            # Check for conflicts that need LLM resolution
            final_type = await self._resolve_type_conflict(
                name, candidates, type_counts
            )

        # Merge nullable (any evidence of nullable = nullable)
        nullable = any(c.nullable for c in candidates)

        # Merge unique (any evidence of unique = unique)
        unique = any(c.unique for c in candidates)

        # Merge indexed
        indexed = any(c.indexed for c in candidates) or name.endswith("Id")

        # Merge constraints (union)
        constraints = {}
        for c in candidates:
            constraints.update(c.constraints)

        # Collect all evidence
        all_evidence = []
        for c in candidates:
            all_evidence.extend(c.evidence)

        # Calculate confidence
        confidence = sum(c.confidence for c in candidates) / len(candidates)

        return InferredField(
            name=name,
            field_type=final_type,
            nullable=nullable,
            unique=unique,
            indexed=indexed,
            constraints=constraints,
            evidence=all_evidence,
        )

    async def _resolve_type_conflict(
        self,
        field_name: str,
        candidates: list[FieldCandidate],
        type_counts: dict[InferredFieldType, int],
    ) -> InferredFieldType:
        """Resolve type conflict, using LLM if needed."""
        # First try deterministic resolution

        # If one type is clearly more common
        total = sum(type_counts.values())
        for field_type, count in type_counts.items():
            if count / total > 0.6:
                return field_type

        # Prefer more specific types
        priority = [
            InferredFieldType.UUID,
            InferredFieldType.DATETIME,
            InferredFieldType.DATE,
            InferredFieldType.DECIMAL,
            InferredFieldType.INTEGER,
            InferredFieldType.FLOAT,
            InferredFieldType.BOOLEAN,
            InferredFieldType.JSON,
            InferredFieldType.TEXT,
            InferredFieldType.STRING,
        ]

        for ptype in priority:
            if ptype in type_counts:
                return ptype

        # If still ambiguous and LLM available, ask it
        if self._llm:
            return await self._ask_llm_for_type(field_name, candidates)

        # Default to string
        return InferredFieldType.STRING

    async def _ask_llm_for_type(
        self, field_name: str, candidates: list[FieldCandidate]
    ) -> InferredFieldType:
        """Ask LLM to resolve type conflict."""
        # Build context
        context = f"Field name: {field_name}\n"
        context += "Evidence:\n"
        for c in candidates:
            context += f"- Type: {c.field_type.value}, Source: {c.evidence[0].source.value if c.evidence else 'unknown'}\n"

        prompt = f"""Given a field with conflicting type evidence, determine the most appropriate database type.

{context}

Choose from: string, text, integer, float, decimal, boolean, datetime, date, json, uuid

Return only the type name."""

        try:
            response = await self._llm.complete(prompt)
            type_str = response.strip().lower()
            return InferredFieldType(type_str)
        except Exception as e:
            logger.warning(f"LLM type resolution failed: {e}")
            return InferredFieldType.STRING

    def _map_ts_type(self, ts_type: str) -> InferredFieldType:
        """Map TypeScript type to field type."""
        ts_type_lower = ts_type.lower()

        mapping = {
            "string": InferredFieldType.STRING,
            "number": InferredFieldType.FLOAT,
            "boolean": InferredFieldType.BOOLEAN,
            "date": InferredFieldType.DATETIME,
            "json": InferredFieldType.JSON,
            "object": InferredFieldType.JSON,
            "any": InferredFieldType.JSON,
        }

        if ts_type_lower in mapping:
            return mapping[ts_type_lower]

        # Check for relation
        if ts_type.startswith("relation:"):
            return InferredFieldType.RELATION

        # Check for UUID patterns
        if "uuid" in ts_type_lower or "id" in ts_type_lower:
            return InferredFieldType.UUID

        return InferredFieldType.STRING

    def _map_input_type(self, input_type: str) -> InferredFieldType:
        """Map form input type to field type."""
        mapping = {
            "text": InferredFieldType.STRING,
            "email": InferredFieldType.STRING,
            "password": InferredFieldType.STRING,
            "textarea": InferredFieldType.TEXT,
            "number": InferredFieldType.INTEGER,
            "tel": InferredFieldType.STRING,
            "url": InferredFieldType.STRING,
            "date": InferredFieldType.DATE,
            "datetime-local": InferredFieldType.DATETIME,
            "checkbox": InferredFieldType.BOOLEAN,
            "select": InferredFieldType.STRING,
        }
        return mapping.get(input_type, InferredFieldType.STRING)

    def _extract_zod_constraints(self, field: dict) -> dict:
        """Extract validation constraints from Zod field."""
        # Could parse .min(), .max(), .email(), etc.
        return {}

    def _add_common_fields(self, models: list[InferredModel]) -> list[InferredModel]:
        """Add common fields like id, timestamps."""
        for model in models:
            field_names = {f.name for f in model.fields}

            # Add id if not present
            if "id" not in field_names:
                model.fields.insert(
                    0,
                    InferredField(
                        name="id",
                        field_type=InferredFieldType.UUID,
                        unique=True,
                        indexed=True,
                    ),
                )

            # Add timestamps if enabled
            if model.timestamps:
                if "createdAt" not in field_names and "created_at" not in field_names:
                    model.fields.append(
                        InferredField(
                            name="createdAt",
                            field_type=InferredFieldType.DATETIME,
                            nullable=False,
                        )
                    )
                if "updatedAt" not in field_names and "updated_at" not in field_names:
                    model.fields.append(
                        InferredField(
                            name="updatedAt",
                            field_type=InferredFieldType.DATETIME,
                            nullable=False,
                        )
                    )

        return models

    def _infer_indexes(self, models: list[InferredModel]) -> list[InferredModel]:
        """Infer indexes based on field patterns."""
        for model in models:
            for field in model.fields:
                # Index foreign keys
                if field.name.endswith("Id"):
                    field.indexed = True

                # Index common query fields
                if field.name in ("email", "username", "slug", "status"):
                    field.indexed = True

        return models

    def _should_have_timestamps(self, name: str, fields: list[InferredField]) -> bool:
        """Determine if model should have timestamps."""
        # Most models should have timestamps
        return True

    def _should_have_soft_delete(self, name: str, fields: list[InferredField]) -> bool:
        """Determine if model should have soft delete."""
        # Enable for user-facing models
        user_models = {"user", "post", "comment", "order", "product"}
        return name.lower() in user_models
