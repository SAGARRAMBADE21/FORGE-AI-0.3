"""Infer relationships between models."""

import logging
import re

from core.types import (
    ApiResourceContract,
    Evidence,
    EvidenceSource,
    InferredField,
    InferredFieldType,
    InferredModel,
    InferredRelation,
    InferredRelationType,
)

logger = logging.getLogger(__name__)


class RelationshipInferrer:
    """
    Infer relationships between models from:
    - Foreign key patterns (userId, postId)
    - Type annotations (User, Post[])
    - API endpoint patterns (/users/:userId/posts)
    - Form submissions
    """

    def __init__(self):
        pass

    async def infer_relationships(
        self, models: list[InferredModel], api_resources: list[ApiResourceContract]
    ) -> list[InferredRelation]:
        """Infer all relationships."""
        relations = []
        model_names = {m.name.lower(): m.name for m in models}

        # From field patterns
        for model in models:
            rels = self._infer_from_fields(model, model_names)
            relations.extend(rels)

        # From API patterns
        rels = self._infer_from_api(api_resources, model_names)
        relations.extend(rels)

        # Deduplicate and resolve
        relations = self._deduplicate(relations)

        # Add inverse relations
        relations = self._add_inverse_relations(relations, model_names)

        logger.info(f"Inferred {len(relations)} relationships")
        return relations

    def _infer_from_fields(
        self, model: InferredModel, model_names: dict[str, str]
    ) -> list[InferredRelation]:
        """Infer relations from field patterns."""
        relations = []

        for field in model.fields:
            # Pattern 1: userId, authorId, postId (camelCase)
            if field.name.endswith("Id") and len(field.name) > 2:
                target_name = field.name[:-2].lower()
                if target_name in model_names:
                    relations.append(
                        InferredRelation(
                            source_model=model.name,
                            target_model=model_names[target_name],
                            relation_type=InferredRelationType.MANY_TO_ONE,
                            source_field=field.name,
                            target_field="id",
                            evidence=getattr(field, 'evidence', []),
                        )
                    )

            # Pattern 2: user_id, author_id (snake_case)
            if field.name.endswith("_id") and len(field.name) > 3:
                target_name = field.name[:-3].lower()
                if target_name in model_names:
                    relations.append(
                        InferredRelation(
                            source_model=model.name,
                            target_model=model_names[target_name],
                            relation_type=InferredRelationType.MANY_TO_ONE,
                            source_field=field.name,
                            target_field="id",
                            evidence=getattr(field, 'evidence', []),
                        )
                    )

            # Pattern 3: Array types indicating One-to-Many - e.g., items: CartItem[]
            # Check if field name suggests plural (indicates array/collection)
            is_array_field = (
                field.name.endswith('s') or
                field.name.endswith('es') or
                field.name.endswith('ies') or
                field.name.lower() == 'items' or
                field.name.lower() == 'children'
            )
            
            if is_array_field and getattr(field, 'relation_to', None):
                target_lower = getattr(field, 'relation_to', None).lower()
                if target_lower in model_names:
                    relations.append(
                        InferredRelation(
                            source_model=model.name,
                            target_model=model_names[target_lower],
                            relation_type=InferredRelationType.ONE_TO_MANY,
                            source_field=field.name,
                            target_field=f"{model.name.lower()}Id",
                            evidence=getattr(field, 'evidence', []),
                        )
                    )

            # Pattern 4: Field name matches a model name (singular) - e.g., user: User
            field_lower = field.name.lower()
            if field_lower in model_names and getattr(field, 'field_type', None) == InferredFieldType.RELATION:
                relations.append(
                    InferredRelation(
                        source_model=model.name,
                        target_model=model_names[field_lower],
                        relation_type=InferredRelationType.MANY_TO_ONE,
                        source_field=f"{field.name}Id",
                        target_field="id",
                        evidence=getattr(field, 'evidence', []),
                    )
                )

            # Pattern 5: Field name is plural of a model - e.g., products: Product[]
            singular = self._singularize(field.name)
            if singular in model_names:
                relations.append(
                    InferredRelation(
                        source_model=model.name,
                        target_model=model_names[singular],
                        relation_type=InferredRelationType.ONE_TO_MANY,
                        source_field=field.name,
                        target_field=f"{model.name.lower()}Id",
                        evidence=getattr(field, 'evidence', []),
                    )
                )

            # Pattern 6: relation type reference (existing logic)
            if getattr(field, 'field_type', None) == InferredFieldType.RELATION and getattr(field, 'relation_to', None):
                target_lower = getattr(field, 'relation_to', None).lower()
                if target_lower in model_names:
                    rel_type = getattr(field, 'relation_type', None) or InferredRelationType.MANY_TO_ONE
                    relations.append(
                        InferredRelation(
                            source_model=model.name,
                            target_model=model_names[target_lower],
                            relation_type=rel_type,
                            source_field=field.name,
                            target_field="id",
                            evidence=getattr(field, 'evidence', []),
                        )
                    )

            # Pattern 7: Self-referential: parentId, parent_id
            if field.name in ("parentId", "parent_id"):
                relations.append(
                    InferredRelation(
                        source_model=model.name,
                        target_model=model.name,
                        relation_type=InferredRelationType.SELF_REFERENTIAL,
                        source_field=field.name,
                        target_field="id",
                        evidence=getattr(field, 'evidence', []),
                    )
                )

        return relations

    def _singularize(self, word: str) -> str:
        """Simple singularization for common patterns."""
        word_lower = word.lower()
        if word_lower.endswith("ies"):
            return word_lower[:-3] + "y"
        elif word_lower.endswith("es") and len(word_lower) > 3:
            return word_lower[:-2]
        elif word_lower.endswith("s") and not word_lower.endswith("ss"):
            return word_lower[:-1]
        return word_lower


    def _infer_from_api(
        self, api_resources: list[ApiResourceContract], model_names: dict[str, str]
    ) -> list[InferredRelation]:
        """Infer relations from API endpoint patterns."""
        relations = []

        for resource in api_resources:
            for endpoint in resource.endpoints:
                # Pattern: /users/:userId/posts
                parts = endpoint.path.strip("/").split("/")

                for i, part in enumerate(parts):
                    if part.startswith(":") and part.endswith("Id"):
                        parent_name = part[1:-2].lower()

                        # Look for child resource
                        if i + 1 < len(parts):
                            child_name = parts[i + 1].rstrip("s").lower()

                            if parent_name in model_names and child_name in model_names:
                                relations.append(
                                    InferredRelation(
                                        source_model=model_names[child_name],
                                        target_model=model_names[parent_name],
                                        relation_type=InferredRelationType.MANY_TO_ONE,
                                        source_field=f"{parent_name}Id",
                                        target_field="id",
                                        evidence=endpoint.evidence,
                                    )
                                )

        return relations

    def _deduplicate(self, relations: list[InferredRelation]) -> list[InferredRelation]:
        """Remove duplicate relations."""
        seen = set()
        unique = []

        for rel in relations:
            key = (rel.source_model, rel.target_model, rel.source_field)
            if key not in seen:
                seen.add(key)
                unique.append(rel)

        return unique

    def _add_inverse_relations(
        self, relations: list[InferredRelation], model_names: dict[str, str]
    ) -> list[InferredRelation]:
        """Add inverse relations for bidirectional access."""
        all_relations = list(relations)
        existing = {(r.source_model, r.target_model, r.source_field) for r in relations}

        for rel in relations:
            if rel.relation_type == InferredRelationType.MANY_TO_ONE:
                # Add One-to-Many inverse
                inverse_key = (
                    rel.target_model,
                    rel.source_model,
                    f"{rel.source_model.lower()}s",
                )
                if inverse_key not in existing:
                    all_relations.append(
                        InferredRelation(
                            source_model=rel.target_model,
                            target_model=rel.source_model,
                            relation_type=InferredRelationType.ONE_TO_MANY,
                            source_field=f"{rel.source_model.lower()}s",
                            target_field=rel.source_field,
                            evidence=rel.evidence,
                        )
                    )

        return all_relations

    def detect_many_to_many(
        self, models: list[InferredModel], relations: list[InferredRelation]
    ) -> list[InferredRelation]:
        """Detect many-to-many relationships requiring junction tables."""
        m2m_relations = []

        # Look for junction table patterns
        for model in models:
            # Pattern: model name like UserRole, PostTag
            if len(model.fields) <= 4:  # Junction tables are typically small
                fk_fields = [f for f in model.fields if f.name.endswith("Id")]
                if len(fk_fields) == 2:
                    # This is likely a junction table
                    model1 = fk_fields[0].name[:-2]
                    model2 = fk_fields[1].name[:-2]

                    m2m_relations.append(
                        InferredRelation(
                            source_model=model1,
                            target_model=model2,
                            relation_type=InferredRelationType.MANY_TO_MANY,
                            source_field=f"{model2.lower()}s",
                            target_field=f"{model1.lower()}s",
                            through_model=model.name,
                            evidence=model.evidence,
                        )
                    )

        return m2m_relations
