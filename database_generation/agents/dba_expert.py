# DBA expert agent
"""
DBA Expert Agent - Database Administration and Optimization
"""

from typing import Optional, List, Dict, Any
from database_generation.agents.base import BaseAgent, AgentRole, AgentState
from database_generation.agents.message import Message, MessageType


class DBAExpertAgent(BaseAgent):
    """
    DBA Expert Agent
    
    Responsibilities:
    - Optimize schema for performance
    - Design indexing strategy
    - Add constraints for data integrity
    - Recommend partitioning strategies
    - Security considerations
    """
    
    def __init__(self):
        super().__init__(AgentRole.DBA_EXPERT, "DBAExpert")
    
    @property
    def system_prompt(self) -> str:
        return """
<role>
You are a Senior DBA Expert with deep knowledge of PostgreSQL, MySQL, and MongoDB internals.
You optimize database schemas for performance, reliability, and security.
</role>

<responsibilities>
1. Analyze query patterns and add appropriate indexes
2. Design composite indexes for common queries
3. Add check constraints for data validation
4. Recommend partitioning for large tables
5. Security: row-level security, encryption considerations
6. Identify potential performance bottlenecks
</responsibilities>

<optimization_strategies>
INDEX_STRATEGY:
- Foreign keys always need indexes
- Columns in WHERE clauses need indexes
- Composite indexes for multi-column filters
- Partial indexes for filtered queries (status = 'active')
- Covering indexes for read-heavy tables
- GIN indexes for JSONB and arrays

CONSTRAINT_STRATEGY:
- Check constraints for valid ranges (price > 0)
- Check constraints for enum-like values
- NOT NULL for required business fields
- UNIQUE for natural keys (email, username, slug)

PARTITIONING_STRATEGY:
- Time-based partitioning for logs, events
- List partitioning for multi-tenant
- Range partitioning for large sequential data
</optimization_strategies>

<output_format>
{
    "optimizations": [
        {
            "type": "index|constraint|partition|security",
            "entity": "table_name",
            "action": "add|modify|remove",
            "details": {
                "name": "idx_name",
                "fields": ["field1", "field2"],
                "type": "btree|hash|gin|gist",
                "unique": false,
                "partial": null|"WHERE clause",
                "include": null|["col1", "col2"]
            },
            "reason": "why this helps",
            "impact": "high|medium|low",
            "query_pattern": "SELECT * FROM x WHERE y"
        }
    ],
    "warnings": [
        {"issue": "description", "suggestion": "how to fix"}
    ],
    "security_recommendations": [
        {"type": "rls|encryption|audit", "description": "what to do"}
    ]
}
</output_format>

<common_patterns_by_app>
ECOMMERCE:
- idx_products_category_status ON products(category_id, status)
- idx_orders_user_created ON orders(user_id, created_at DESC)
- idx_products_price ON products(price) for range queries
- Partial: idx_orders_pending ON orders(user_id) WHERE status = 'pending'

SOCIAL:
- idx_posts_user_created ON posts(user_id, created_at DESC)
- idx_posts_visibility ON posts(visibility, created_at DESC)
- idx_comments_post ON comments(post_id, created_at)
- idx_follows_follower ON follows(follower_id)
- idx_follows_following ON follows(following_id)

SAAS:
- idx_org_members ON org_members(organization_id, user_id)
- idx_subscriptions_org ON subscriptions(organization_id, status)
- Row-level security based on organization_id
</common_patterns_by_app>
"""
    
    @property
    def expertise(self) -> List[str]:
        return [
            "performance optimization",
            "indexing strategy",
            "query analysis",
            "partitioning",
            "security"
        ]
    
    async def handle_request(self, message: Message) -> Optional[Message]:
        """Handle incoming request"""
        
        subject = message.subject.lower()
        
        if "optimize" in subject:
            result = await self.optimize_schema(message.content)
            return self.message_bus.respond(message, result)
        
        elif "index" in subject:
            result = await self.design_indexes(message.content)
            return self.message_bus.respond(message, result)
        
        elif "review" in subject:
            result = await self.review_performance(message.content)
            return self.message_bus.respond(message, result)
        
        return None
    
    async def handle_handoff(self, message: Message):
        """Handle work handoff from Data Modeler"""
        await super().handle_handoff(message)
        
        if "optimize" in message.subject.lower():
            content = message.content
            schema = content.get("schema", {})
            app_type = content.get("app_type")
            
            # Optimize the schema
            optimized = await self.optimize_schema({
                "schema": schema,
                "app_type": app_type
            })
            
            # Hand off to SQL Writer
            await self.handoff_to(
                AgentRole.SQL_WRITER.value,
                "Generate SQL",
                {
                    "schema": schema,
                    "optimizations": optimized,
                    "app_type": app_type
                }
            )
    
    async def optimize_schema(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize schema for performance"""
        
        self.state = AgentState.WORKING
        
        result = await self.think(
            "Analyze and optimize this schema for performance",
            context
        )
        
        # Record decisions
        for opt in result.get("optimizations", []):
            self.make_decision(
                f"Added {opt.get('type')}: {opt.get('details', {}).get('name', 'unknown')}",
                opt.get("reason", "performance improvement")
            )
        
        return result
    
    async def design_indexes(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Design indexing strategy"""
        
        self.state = AgentState.WORKING
        
        result = await self.think(
            "Design optimal indexes for this schema",
            context
        )
        
        return result
    
    async def review_performance(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Review schema for performance issues"""
        
        self.state = AgentState.WORKING
        
        result = await self.think(
            "Review this schema for potential performance issues",
            {"schema": schema}
        )
        
        return result