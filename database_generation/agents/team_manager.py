# Team manager agent
"""
Team Manager - Coordinates all agents
"""

import asyncio
from typing import Dict, List, Any, Optional
from database_generation.agents.base import BaseAgent, AgentRole
from database_generation.agents.message import Message, MessageBus, MessageType, message_bus
from database_generation.agents.lead_architect import LeadArchitectAgent
from database_generation.agents.data_modeler import DataModelerAgent
from database_generation.agents.dba_expert import DBAExpertAgent
from database_generation.agents.sql_writer import SQLWriterAgent
from database_generation.agents.reviewer import ReviewerAgent
from database_generation.agents.chat_agent import ChatAgent
from database_generation.db_types import ForgeSchema, InputMetadata


class TeamManager:
    """
    Team Manager - Coordinates the agent team
    
    Responsible for:
    - Creating and managing agents
    - Orchestrating workflows
    - Collecting results
    - Handling errors
    """
    
    def __init__(self):
        self.message_bus = message_bus
        self.agents: Dict[AgentRole, BaseAgent] = {}
        self.results: Dict[str, Any] = {}
        self._initialized = False
    
    def initialize(self):
        """Initialize all agents"""
        if self._initialized:
            return
        
        # Create agents
        self.agents = {
            AgentRole.LEAD_ARCHITECT: LeadArchitectAgent(),
            AgentRole.DATA_MODELER: DataModelerAgent(),
            AgentRole.DBA_EXPERT: DBAExpertAgent(),
            AgentRole.SQL_WRITER: SQLWriterAgent(),
            AgentRole.REVIEWER: ReviewerAgent(),
            AgentRole.CHAT_ASSISTANT: ChatAgent(),
        }
        
        # Subscribe manager to broadcasts
        self.message_bus.subscribe("manager", self._handle_broadcast)
        
        self._initialized = True
        print(f"✓ Initialized {len(self.agents)} agents")
    
    async def _handle_broadcast(self, message: Message):
        """Handle broadcast messages"""
        if message.type == MessageType.NOTIFICATION:
            self.results[message.subject] = message.content
    
    def get_agent(self, role: AgentRole) -> Optional[BaseAgent]:
        """Get agent by role"""
        return self.agents.get(role)
    
    async def run_pipeline(self, metadata: InputMetadata) -> Dict[str, Any]:
        """
        Run the full agent pipeline
        
        Flow:
        1. Lead Architect analyzes requirements
        2. Data Modeler designs schema
        3. DBA Expert optimizes
        4. SQL Writer generates SQL
        5. Reviewer validates
        """
        
        self.initialize()
        results = {
            "success": False,
            "stages": {},
            "schema": None,
            "sql": {},
            "errors": []
        }
        
        try:
            # Stage 1: Lead Architect Analysis
            print("🏗️  Stage 1: Lead Architect analyzing...")
            architect = self.agents[AgentRole.LEAD_ARCHITECT]
            
            analysis = await architect.analyze_application({
                "entities": metadata.entities,
                "api_endpoints": metadata.api_endpoints,
                "forms": metadata.forms,
                "relationships": metadata.relationships
            })
            
            results["stages"]["analysis"] = {
                "success": True,
                "app_type": analysis.get("analysis", {}).get("app_type"),
                "confidence": analysis.get("analysis", {}).get("confidence")
            }
            
            # Stage 2: Data Modeler Design
            print("📐 Stage 2: Data Modeler designing schema...")
            modeler = self.agents[AgentRole.DATA_MODELER]
            
            schema_design = await modeler.design_schema({
                "app_type": analysis.get("analysis", {}).get("app_type"),
                "metadata": metadata.model_dump(),
                "strategy": analysis.get("strategy", {})
            })
            
            results["stages"]["design"] = {
                "success": True,
                "entities": len(schema_design.get("entities", []))
            }
            
            # Stage 3: DBA Expert Optimization
            print("⚡ Stage 3: DBA Expert optimizing...")
            dba = self.agents[AgentRole.DBA_EXPERT]
            
            optimizations = await dba.optimize_schema({
                "schema": schema_design,
                "app_type": analysis.get("analysis", {}).get("app_type")
            })
            
            results["stages"]["optimization"] = {
                "success": True,
                "optimizations": len(optimizations.get("optimizations", []))
            }
            
            # Stage 4: SQL Writer Generation
            print("📝 Stage 4: SQL Writer generating DDL...")
            writer = self.agents[AgentRole.SQL_WRITER]
            
            for db_type in ["postgresql", "mysql", "mongodb"]:
                sql_result = await writer.generate_sql({
                    "schema": schema_design,
                    "optimizations": optimizations,
                    "database": db_type
                })
                results["sql"][db_type] = sql_result.get("ddl", "")
            
            results["stages"]["generation"] = {
                "success": True,
                "databases": list(results["sql"].keys())
            }
            
            # Stage 5: Reviewer Validation
            print("✅ Stage 5: Reviewer validating...")
            reviewer = self.agents[AgentRole.REVIEWER]
            
            review = await reviewer.review_schema({
                "schema": schema_design,
                "optimizations": optimizations
            })
            
            results["stages"]["review"] = {
                "success": True,
                "approved": review.get("approved", False),
                "score": review.get("score", 0),
                "issues": len(review.get("issues", []))
            }
            
            # Build final schema
            schema = modeler.build_schema(schema_design)
            results["schema"] = schema.model_dump()
            results["success"] = True
            
            print("✨ Pipeline completed successfully!")
            
        except Exception as e:
            results["errors"].append(str(e))
            print(f"❌ Pipeline error: {e}")
        
        return results
    
    async def chat(self, message: str, schema: ForgeSchema = None) -> Dict[str, Any]:
        """
        Process a chat message through the Chat Agent
        """
        self.initialize()
        
        chat_agent = self.agents[AgentRole.CHAT_ASSISTANT]
        
        result = await chat_agent.process_user_input({
            "message": message,
            "schema": schema.model_dump() if schema else None
        })
        
        return result
    
    def get_team_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        return {
            role.value: {
                "id": agent.id,
                "state": agent.state.value,
                "decisions": len(agent.memory.decisions)
            }
            for role, agent in self.agents.items()
        }
    
    def get_decisions(self) -> List[Dict[str, Any]]:
        """Get all decisions made by agents"""
        decisions = []
        for agent in self.agents.values():
            for decision in agent.memory.decisions:
                decisions.append({
                    "agent": agent.name,
                    "role": agent.role.value,
                    **decision
                })
        return sorted(decisions, key=lambda x: x.get("timestamp", ""))


# Singleton instance
team_manager = TeamManager()