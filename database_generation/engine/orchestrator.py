# Orchestrator
"""
Agent Orchestrator - Coordinates the agent pipeline
"""

from typing import Dict, Any, Optional
from database_generation.db_types import (
    InputMetadata,
    PipelineContext,
    ForgeSchema,
    AgentResponse,
    AppType,
    EntityDef,
    FieldDef,
    FieldType,
    IndexDef,
    RelationshipDef,
    EnumDef,
    FieldReference,
    OnDeleteAction,
    RelationType,
    IndexType
)
from database_generation.prompts.agents import (
    CLASSIFIER_AGENT_XML,
    ARCHITECT_AGENT_XML,
    OPTIMIZER_AGENT_XML,
    SQL_WRITER_AGENT_XML
)
from database_generation.engine.ai_engine import ai_engine


class Orchestrator:
    """Orchestrates the agent pipeline"""
    
    def __init__(self):
        self.agents = {
            "classifier": CLASSIFIER_AGENT_XML,
            "architect": ARCHITECT_AGENT_XML,
            "optimizer": OPTIMIZER_AGENT_XML,
            "query_writer": SQL_WRITER_AGENT_XML
        }
    
    def run_pipeline(self, metadata: InputMetadata) -> PipelineContext:
        """
        Run the complete agent pipeline
        
        Args:
            metadata: Pre-scanned frontend metadata
        
        Returns:
            PipelineContext with all results
        """
        
        context = PipelineContext(input_metadata=metadata)
        
        # Stage 1: Classify application type
        print("🏷️  Running Classifier Agent...")
        classifier_result = self._run_classifier(context)
        context.agent_responses.append(classifier_result)
        
        if classifier_result.success:
            context.app_type = AppType(classifier_result.data.get("app_type", "unknown"))
        
        # Stage 2: Design schema
        print("📐 Running Architect Agent...")
        architect_result = self._run_architect(context)
        context.agent_responses.append(architect_result)
        
        if architect_result.success:
            context.schema = self._build_schema(architect_result.data, context)
        
        # Stage 3: Optimize schema
        print("⚡ Running Optimizer Agent...")
        optimizer_result = self._run_optimizer(context)
        context.agent_responses.append(optimizer_result)
        
        if optimizer_result.success:
            self._apply_optimizations(context, optimizer_result.data)
        
        return context
    
    def generate_ddl(self, context: PipelineContext, 
                     database_type: str, 
                     editor_type: str) -> Dict[str, Any]:
        """
        Generate DDL for specific database and editor
        
        Args:
            context: Pipeline context with schema
            database_type: Target database
            editor_type: Target editor format
        
        Returns:
            Generated DDL and metadata
        """
        
        if not context.schema:
            return {"error": "No schema available"}
        
        print(f"📝 Running Query Writer Agent for {database_type}...")
        
        input_data = {
            "schema": context.schema.model_dump(),
            "database_type": database_type,
            "editor_type": editor_type
        }
        
        result = ai_engine.run_with_retry(
            self.agents["query_writer"],
            input_data
        )
        
        context.agent_responses.append(AgentResponse(
            agent="query_writer",
            success="error" not in result,
            data=result
        ))
        
        return result
    
    def _run_classifier(self, context: PipelineContext) -> AgentResponse:
        """Run classifier agent"""
        
        input_data = {
            "entities": context.input_metadata.entities,
            "api_endpoints": context.input_metadata.api_endpoints,
            "forms": context.input_metadata.forms,
            "state_schemas": context.input_metadata.state_schemas,
            "relationships": context.input_metadata.relationships
        }
        
        result = ai_engine.run_with_retry(
            self.agents["classifier"],
            input_data
        )
        
        return AgentResponse(
            agent="classifier",
            success="error" not in result,
            data=result,
            reasoning=result.get("reasoning")
        )
    
    def _run_architect(self, context: PipelineContext) -> AgentResponse:
        """Run architect agent"""
        
        classifier_data = {}
        for resp in context.agent_responses:
            if resp.agent == "classifier" and resp.success:
                classifier_data = resp.data
                break
        
        input_data = {
            "app_type": context.app_type.value if context.app_type else "unknown",
            "metadata": context.input_metadata.model_dump(),
            "suggested_entities": classifier_data.get("suggested_entities", []),
            "missing_entities": classifier_data.get("missing_entities", [])
        }
        
        result = ai_engine.run_with_retry(
            self.agents["architect"],
            input_data
        )
        
        return AgentResponse(
            agent="architect",
            success="error" not in result and "entities" in result,
            data=result
        )
    
    def _run_optimizer(self, context: PipelineContext) -> AgentResponse:
        """Run optimizer agent"""
        
        if not context.schema:
            return AgentResponse(
                agent="optimizer",
                success=False,
                data={},
                errors=["No schema to optimize"]
            )
        
        input_data = {
            "schema": context.schema.model_dump(),
            "app_type": context.app_type.value if context.app_type else "unknown",
            "expected_scale": context.input_metadata.hints.get("scale", "medium")
        }
        
        result = ai_engine.run_with_retry(
            self.agents["optimizer"],
            input_data
        )
        
        return AgentResponse(
            agent="optimizer",
            success="error" not in result,
            data=result
        )
    
    def _build_schema(self, architect_data: Dict, context: PipelineContext) -> ForgeSchema:
        """Build ForgeSchema from architect output"""
        
        entities = []
        for entity_data in architect_data.get("entities", []):
            fields = []
            for field_data in entity_data.get("fields", []):
                
                reference = None
                if field_data.get("reference"):
                    ref = field_data["reference"]
                    reference = FieldReference(
                        entity=ref.get("entity", ""),
                        field=ref.get("field", "id"),
                        on_delete=OnDeleteAction(ref.get("on_delete", "cascade")),
                        on_update=OnDeleteAction(ref.get("on_update", "cascade"))
                    )
                
                field = FieldDef(
                    name=field_data.get("name", ""),
                    type=FieldType(field_data.get("type", "string")),
                    required=field_data.get("required", False),
                    unique=field_data.get("unique", False),
                    primary_key=field_data.get("primary_key", False),
                    length=field_data.get("length"),
                    precision=field_data.get("precision"),
                    scale=field_data.get("scale"),
                    enum_values=field_data.get("enum_values"),
                    default=field_data.get("default"),
                    default_function=field_data.get("default_function"),
                    reference=reference,
                    check=field_data.get("check"),
                    comment=field_data.get("comment")
                )
                fields.append(field)
            
            indexes = []
            for idx_data in entity_data.get("indexes", []):
                index = IndexDef(
                    name=idx_data.get("name"),
                    fields=idx_data.get("fields", []),
                    type=IndexType(idx_data.get("type", "btree")),
                    unique=idx_data.get("unique", False),
                    where=idx_data.get("where")
                )
                indexes.append(index)
            
            entity = EntityDef(
                name=entity_data.get("name", ""),
                fields=fields,
                indexes=indexes,
                timestamps=entity_data.get("timestamps", True),
                soft_delete=entity_data.get("soft_delete", False),
                comment=entity_data.get("comment")
            )
            entities.append(entity)
        
        relationships = []
        for rel_data in architect_data.get("relationships", []):
            relationship = RelationshipDef(
                type=RelationType(rel_data.get("type", "one_to_many")),
                from_entity=rel_data.get("from_entity", ""),
                from_field=rel_data.get("from_field", ""),
                to_entity=rel_data.get("to_entity", ""),
                to_field=rel_data.get("to_field", "id"),
                through_entity=rel_data.get("through_entity")
            )
            relationships.append(relationship)
        
        enums = []
        for enum_data in architect_data.get("enums", []):
            enum = EnumDef(
                name=enum_data.get("name", ""),
                values=enum_data.get("values", [])
            )
            enums.append(enum)
        
        return ForgeSchema(
            name=context.input_metadata.app_name + "_schema",
            app_type=context.app_type or AppType.UNKNOWN,
            entities=entities,
            relationships=relationships,
            enums=enums
        )
    
    def _apply_optimizations(self, context: PipelineContext, 
                             optimizer_data: Dict) -> None:
        """Apply optimizations to schema"""
        
        if not context.schema:
            return
        
        for opt in optimizer_data.get("optimizations", []):
            entity_name = opt.get("entity")
            
            # Find entity
            entity = next(
                (e for e in context.schema.entities if e.name == entity_name),
                None
            )
            
            if not entity:
                continue
            
            if opt.get("type") == "index" and opt.get("action") == "add":
                details = opt.get("details", {})
                new_index = IndexDef(
                    name=details.get("index_name"),
                    fields=details.get("fields", []),
                    type=IndexType(details.get("type", "btree")),
                    unique=details.get("unique", False),
                    where=details.get("partial")
                )
                entity.indexes.append(new_index)


# Singleton instance
orchestrator = Orchestrator()