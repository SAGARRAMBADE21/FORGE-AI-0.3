# Lead architect agent
"""
Lead Architect Agent - Makes high-level architectural decisions
"""

from typing import Optional, List, Dict, Any
from database_generation.agents.base import BaseAgent, AgentRole, AgentState
from database_generation.agents.message import Message, MessageType


class LeadArchitectAgent(BaseAgent):
    """
    Lead Architect Agent
    
    Responsibilities:
    - Analyze application requirements
    - Classify application type
    - Make high-level schema decisions
    - Coordinate other agents
    - Approve final designs
    """
    
    def __init__(self):
        super().__init__(AgentRole.LEAD_ARCHITECT, "LeadArchitect")
    
    @property
    def system_prompt(self) -> str:
        return """
<role>
You are the Lead Database Architect at FORGE, a senior technical leader with 20+ years of experience. 
You make high-level architectural decisions and coordinate your team of specialists.
</role>

<responsibilities>
1. Analyze application requirements from metadata
2. Classify application type (ecommerce, social, saas, content, marketplace)
3. Define high-level schema strategy
4. Delegate detailed work to specialists
5. Review and approve final designs
6. Resolve conflicts between team members
</responsibilities>

<decision_making>
When making decisions:
1. Consider scalability (millions of records)
2. Consider query patterns
3. Consider data integrity
4. Consider maintainability
5. Document your reasoning
</decision_making>

<output_format>
{
    "analysis": {
        "app_type": "type",
        "confidence": 0.0-1.0,
        "key_features": ["feature1", "feature2"],
        "scale_estimate": "small|medium|large|enterprise"
    },
    "strategy": {
        "approach": "description",
        "core_entities": ["entity1", "entity2"],
        "key_relationships": ["rel1", "rel2"],
        "special_considerations": ["consideration1"]
    },
    "delegation": {
        "data_modeler": "task description",
        "dba_expert": "task description"
    },
    "decisions": [
        {"decision": "what", "reasoning": "why"}
    ]
}
</output_format>

<app_type_patterns>
ECOMMERCE: products, cart, orders, checkout, payment, inventory, shipping
SOCIAL: posts, comments, likes, follows, feed, profile, share
SAAS: organization, team, subscription, billing, plan, permission
CONTENT: article, blog, category, tag, author, publish
MARKETPLACE: listing, seller, buyer, review, transaction, commission
</app_type_patterns>
"""
    
    @property
    def expertise(self) -> List[str]:
        return [
            "application analysis",
            "system architecture",
            "schema strategy",
            "team coordination",
            "technical leadership"
        ]
    
    async def handle_request(self, message: Message) -> Optional[Message]:
        """Handle incoming request"""
        
        subject = message.subject.lower()
        
        if "analyze" in subject or "classify" in subject:
            result = await self.analyze_application(message.content)
            return self.message_bus.respond(message, result)
        
        elif "review" in subject or "approve" in subject:
            result = await self.review_design(message.content)
            return self.message_bus.respond(message, result)
        
        elif "strategy" in subject:
            result = await self.define_strategy(message.content)
            return self.message_bus.respond(message, result)
        
        return None
    
    async def analyze_application(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze application and classify type"""
        
        self.state = AgentState.WORKING
        
        result = await self.think(
            "Analyze this application metadata and classify it",
            {"metadata": metadata}
        )
        
        # Record decision
        if "analysis" in result:
            self.make_decision(
                f"Classified as {result['analysis'].get('app_type', 'unknown')}",
                f"Based on patterns: {result['analysis'].get('key_features', [])}"
            )
        
        return result
    
    async def define_strategy(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Define high-level schema strategy"""
        
        self.state = AgentState.WORKING
        
        result = await self.think(
            "Define a database schema strategy for these requirements",
            {"requirements": requirements}
        )
        
        return result
    
    async def review_design(self, design: Dict[str, Any]) -> Dict[str, Any]:
        """Review and approve a schema design"""
        
        self.state = AgentState.WORKING
        
        result = await self.think(
            "Review this schema design for issues and improvements",
            {"design": design}
        )
        
        return result
    
    async def coordinate_team(self, task: str, context: Dict[str, Any]):
        """Coordinate team to complete a task"""
        
        # Analyze first
        analysis = await self.analyze_application(context.get("metadata", {}))
        
        # Delegate to Data Modeler
        await self.handoff_to(
            AgentRole.DATA_MODELER.value,
            "Design Schema",
            {
                "analysis": analysis,
                "context": context
            }
        )
        
        # Notify DBA Expert to prepare
        await self.send_message(
            AgentRole.DBA_EXPERT.value,
            "Prepare for Optimization",
            {
                "app_type": analysis.get("analysis", {}).get("app_type"),
                "scale": analysis.get("analysis", {}).get("scale_estimate")
            }
        )