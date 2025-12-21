"""Infer relationships between models."""

import re
import logging

from core.types import (
    InferredModel, InferredField, InferredRelation, InferredRelationType,
    InferredFieldType, ApiResourceContract, Evidence, EvidenceSource
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
        self,
        models: list[InferredModel],
        api_resources: list[ApiResourceContract]
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
        self, 
        model: InferredModel, 
        model_names: dict[str, str]
    ) -> list[InferredRelation]:
        """Infer relations from field patterns."""
        relations = []

        for field in model.fields:
            # Pattern: userId, authorId, postId
            if field.name.endswith('Id') and len(field.name) > 2:
                target_name = field.name[:-2].lower()
                if target_name in model_names:
                    relations.append(InferredRelation(
                        source_model=model.name,
                        target_model=model_names[target_name],
                        relation_type=InferredRelationType.MANY_TO_ONE,
                        source_field=field.name,
                        target_field='id',
                        evidence=field.evidence
                    ))

            # Pattern: relation type reference
            if field.field_type == InferredFieldType.RELATION and field.relation_to:
                target_lower = field.relation_to.lower()
                if target_lower in model_names:
                    rel_type = field.relation_type or InferredRelationType.MANY_TO_ONE
                    relations.append(InferredRelation(
                        source_model=model.name,
                        target_model=model_names[target_lower],
                        relation_type=rel_type,
                        source_field=field.name,
                        target_field='id',
                        evidence=field.evidence
                    ))

            # Self-referential: parentId
            if field.name in ('parentId', 'parent_id'):
                relations.append(InferredRelation(
                    source_model=model.name,
                    target_model=model.name,
                    relation_type=InferredRelationType.SELF_REFERENTIAL,
                    source_field=field.name,
                    target_field='id',
                    evidence=field.evidence
                ))

        return relations

    def _infer_from_api(
        self,
        api_resources: list[ApiResourceContract],
        model_names: dict[str, str]
    ) -> list[InferredRelation]:
        """Infer relations from API endpoint patterns."""
        relations = []

        for resource in api_resources:
            for endpoint in resource.endpoints:
                # Pattern: /users/:userId/posts
                parts = endpoint.path.strip('/').split('/')
                
                for i, part in enumerate(parts):
                    if part.startswith(':') and part.endswith('Id'):
                        parent_name = part[1:-2].lower()
                        
                        # Look for child resource
                        if i + 1 < len(parts):
                            child_name = parts[i + 1].rstrip('s').lower()
                            
                            if parent_name in model_names and child_name in model_names:
                                relations.append(InferredRelation(
                                    source_model=model_names[child_name],
                                    target_model=model_names[parent_name],
                                    relation_type=InferredRelationType.MANY_TO_ONE,
                                    source_field=f"{parent_name}Id",
                                    target_field='id',
                                    evidence=endpoint.evidence
                                ))

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
        self,
        relations: list[InferredRelation],
        model_names: dict[str, str]
    ) -> list[InferredRelation]:
        """Add inverse relations for bidirectional access."""
        all_relations = list(relations)
        existing = {(r.source_model, r.target_model, r.source_field) for r in relations}

        for rel in relations:
            if rel.relation_type == InferredRelationType.MANY_TO_ONE:
                # Add One-to-Many inverse
                inverse_key = (rel.target_model, rel.source_model, f"{rel.source_model.lower()}s")
                if inverse_key not in existing:
                    all_relations.append(InferredRelation(
                        source_model=rel.target_model,
                        target_model=rel.source_model,
                        relation_type=InferredRelationType.ONE_TO_MANY,
                        source_field=f"{rel.source_model.lower()}s",
                        target_field=rel.source_field,
                        evidence=rel.evidence
                    ))

        return all_relations

    def detect_many_to_many(
        self,
        models: list[InferredModel],
        relations: list[InferredRelation]
    ) -> list[InferredRelation]:
        """Detect many-to-many relationships requiring junction tables."""
        m2m_relations = []

        # Look for junction table patterns
        for model in models:
            # Pattern: model name like UserRole, PostTag
            if len(model.fields) <= 4:  # Junction tables are typically small
                fk_fields = [f for f in model.fields if f.name.endswith('Id')]
                if len(fk_fields) == 2:
                    # This is likely a junction table
                    model1 = fk_fields[0].name[:-2]
                    model2 = fk_fields[1].name[:-2]

                    m2m_relations.append(InferredRelation(
                        source_model=model1,
                        target_model=model2,
                        relation_type=InferredRelationType.MANY_TO_MANY,
                        source_field=f"{model2.lower()}s",
                        target_field=f"{model1.lower()}s",
                        through_model=model.name,
                        evidence=model.evidence
                    ))

        return m2m_relations