# Reviewer agent
"""
Reviewer Agent - Reviews and validates schema designs
"""

from typing import Optional, List, Dict, Any
from database_generation.agents.base import BaseAgent, AgentRole, AgentState
from database_generation.agents.message import Message, MessageType


class ReviewerAgent(BaseAgent):
    """
    Reviewer Agent
    
    Responsibilities:
    - Validate schema designs
    - Check for best practices
    - Identify security issues
    - Ensure naming conventions
    - Final quality gate
    """
    
    def __init__(self):
        super().__init__(AgentRole.REVIEWER, "Reviewer")
    
    @property
    def system_prompt(self) -> str:
        return """
<role>
You are a Senior Technical Reviewer specializing in database schema quality assurance.
You ensure all designs meet best practices before deployment.
</role>

<responsibilities>
1. Validate schema structure
2. Check naming conventions
3. Verify referential integrity
4. Identify security concerns
5. Ensure performance best practices
6. Final approval gate
</responsibilities>

<review_checklist>
STRUCTURE:
- [ ] Every table has primary key
- [ ] Foreign keys reference existing tables
- [ ] No circular dependencies (unless intentional)
- [ ] Appropriate normalization level

NAMING:
- [ ] snake_case for all identifiers
- [ ] Plural table names
- [ ] Descriptive field names
- [ ] No reserved words

INTEGRITY:
- [ ] Required fields marked NOT NULL
- [ ] Unique constraints where needed
- [ ] Check constraints for validation
- [ ] Foreign key constraints defined

SECURITY:
- [ ] Sensitive data identified
- [ ] No plain text passwords
- [ ] Audit fields present
- [ ] Row-level security considered

PERFORMANCE:
- [ ] Foreign keys indexed
- [ ] Frequently queried fields indexed
- [ ] No over-indexing
- [ ] Appropriate field sizes
</review_checklist>

<output_format>
{
    "approved": true|false,
    "score": 0-100,
    "issues": [
        {
            "severity": "critical|major|minor|suggestion",
            "category": "structure|naming|integrity|security|performance",
            "entity": "table_name",
            "field": "field_name or null",
            "issue": "description",
            "recommendation": "how to fix"
        }
    ],
    "summary": {
        "critical_count": 0,
        "major_count": 0,
        "minor_count": 0,
        "suggestion_count": 0
    },
    "notes": ["additional observations"]
}
</output_format>
"""
    
    @property
    def expertise(self) -> List[str]:
        return [
            "quality assurance",
            "best practices",
            "security review",
            "code review",
            "validation"
        ]
    
    async def handle_request(self, message: Message) -> Optional[Message]:
        """Handle incoming request"""
        
        subject = message.subject.lower()
        
        if "review" in subject or "validate" in subject:
            result = await self.review_schema(message.content)
            return self.message_bus.respond(message, result)
        
        elif "approve" in subject:
            result = await self.approve_schema(message.content)
            return self.message_bus.respond(message, result)
        
        return None
    
    async def handle_handoff(self, message: Message):
        """Handle work handoff"""
        await super().handle_handoff(message)
        
        if "review" in message.subject.lower():
            content = message.content
            
            # Review the schema
            review_result = await self.review_schema(content)
            
            # If approved, notify Lead Architect
            if review_result.get("approved"):
                await self.send_message(
                    AgentRole.LEAD_ARCHITECT.value,
                    "Schema Approved",
                    {
                        "schema": content.get("schema"),
                        "review": review_result
                    },
                    MessageType.NOTIFICATION
                )
            else:
                # Send back for fixes
                await self.send_message(
                    AgentRole.DATA_MODELER.value,
                    "Schema Needs Fixes",
                    {
                        "schema": content.get("schema"),
                        "issues": review_result.get("issues", [])
                    },
                    MessageType.FEEDBACK
                )
    
    async def review_schema(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Review schema for issues"""
        
        self.state = AgentState.WORKING
        
        result = await self.think(
            "Review this schema thoroughly for issues",
            context
        )
        
        # Record findings
        issues = result.get("issues", [])
        critical = len([i for i in issues if i.get("severity") == "critical"])
        
        self.make_decision(
            f"Review complete: {'APPROVED' if result.get('approved') else 'NEEDS FIXES'}",
            f"Found {len(issues)} issues ({critical} critical)"
        )
        
        return result
    
    async def approve_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Final approval check"""
        
        # Quick review
        review = await self.review_schema({"schema": schema})
        
        # Only approve if no critical issues
        critical_issues = [
            i for i in review.get("issues", [])
            if i.get("severity") == "critical"
        ]
        
        return {
            "approved": len(critical_issues) == 0,
            "review": review
        }