"""
Agent Communication and Coordination Utilities

Provides helpers for agent collaboration and message routing.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from orchestration.agent_orchestrator import (
    AgentMessage,
    AgentOrchestrator,
    AgentRole,
    AgentTask,
    MessageType,
)
from orchestration.backend_agents import (
    ApiEngineerAgent,
    ArchitectAgent,
    AuthEngineerAgent,
    CodeReviewerAgent,
    DatabaseEngineerAgent,
    DevOpsEngineerAgent,
    ServiceEngineerAgent,
    TestingEngineerAgent,
)

logger = logging.getLogger(__name__)


class AgentTeamBuilder:
    """Builds and configures a complete backend engineering team"""

    @staticmethod
    def build_full_team(project_root: Path) -> AgentOrchestrator:
        """
        Build a complete team of backend agents

        Returns:
            Fully configured orchestrator with all specialized agents
        """
        orchestrator = AgentOrchestrator(project_root)

        # Register all specialized agents
        agents = [
            ArchitectAgent(orchestrator),
            DatabaseEngineerAgent(orchestrator),
            ApiEngineerAgent(orchestrator),
            ServiceEngineerAgent(orchestrator),
            AuthEngineerAgent(orchestrator),
            TestingEngineerAgent(orchestrator),
            DevOpsEngineerAgent(orchestrator),
            CodeReviewerAgent(orchestrator),
        ]

        for agent in agents:
            orchestrator.register_agent(agent)

        logger.info(f"Built backend engineering team with {len(agents)} agents")
        return orchestrator

    @staticmethod
    def build_minimal_team(project_root: Path) -> AgentOrchestrator:
        """
        Build a minimal team for quick prototyping

        Returns:
            Orchestrator with core agents only
        """
        orchestrator = AgentOrchestrator(project_root)

        # Core agents only
        core_agents = [
            ArchitectAgent(orchestrator),
            DatabaseEngineerAgent(orchestrator),
            ApiEngineerAgent(orchestrator),
            ServiceEngineerAgent(orchestrator),
        ]

        for agent in core_agents:
            orchestrator.register_agent(agent)

        logger.info(f"Built minimal team with {len(core_agents)} agents")
        return orchestrator

    @staticmethod
    def build_custom_team(
        project_root: Path, roles: List[AgentRole]
    ) -> AgentOrchestrator:
        """
        Build a custom team with specific roles

        Args:
            project_root: Project root directory
            roles: List of agent roles to include

        Returns:
            Orchestrator with specified agents
        """
        orchestrator = AgentOrchestrator(project_root)

        role_to_class = {
            AgentRole.ARCHITECT: ArchitectAgent,
            AgentRole.DATABASE_ENGINEER: DatabaseEngineerAgent,
            AgentRole.API_ENGINEER: ApiEngineerAgent,
            AgentRole.SERVICE_ENGINEER: ServiceEngineerAgent,
            AgentRole.AUTH_ENGINEER: AuthEngineerAgent,
            AgentRole.TESTING_ENGINEER: TestingEngineerAgent,
            AgentRole.DEVOPS_ENGINEER: DevOpsEngineerAgent,
            AgentRole.CODE_REVIEWER: CodeReviewerAgent,
        }

        for role in roles:
            agent_class = role_to_class.get(role)
            if agent_class:
                orchestrator.register_agent(agent_class(orchestrator))
            else:
                logger.warning(f"Unknown role: {role}")

        logger.info(f"Built custom team with {len(roles)} agents")
        return orchestrator


class AgentCollaborationLogger:
    """Logs and analyzes agent collaboration"""

    def __init__(self):
        self.interactions: List[Dict[str, Any]] = []

    def log_interaction(self, message: AgentMessage):
        """Log an agent interaction"""
        self.interactions.append(
            {
                "timestamp": message.timestamp,
                "from": message.from_agent,
                "to": message.to_agent,
                "type": message.message_type,
                "summary": self._summarize_content(message.content),
            }
        )

    def _summarize_content(self, content: Dict[str, Any]) -> str:
        """Create a brief summary of message content"""
        if "request" in content:
            return f"Request: {content['request'][:50]}..."
        elif "error" in content:
            return f"Error: {content['error']}"
        elif "status" in content:
            return f"Status: {content['status']}"
        else:
            return "Data exchange"

    def get_collaboration_metrics(self) -> Dict[str, Any]:
        """Get metrics about agent collaboration"""
        if not self.interactions:
            return {
                "total_interactions": 0,
                "agents_active": 0,
                "message_types": {},
                "most_active_pair": None,
                "collaboration_density": 0,
            }

        message_types = {}
        agent_pairs = {}

        for interaction in self.interactions:
            # Count message types
            msg_type = interaction["type"]
            message_types[msg_type] = message_types.get(msg_type, 0) + 1

            # Count agent pairs
            pair = f"{interaction['from']} -> {interaction['to']}"
            agent_pairs[pair] = agent_pairs.get(pair, 0) + 1

        most_active_pair = (
            max(agent_pairs.items(), key=lambda x: x[1]) if agent_pairs else None
        )

        return {
            "total_interactions": len(self.interactions),
            "agents_active": len(
                set(
                    [i["from"] for i in self.interactions]
                    + [i["to"] for i in self.interactions]
                )
            ),
            "message_types": message_types,
            "most_active_pair": most_active_pair,
            "collaboration_density": len(agent_pairs),
        }

    def generate_report(self) -> str:
        """Generate a human-readable collaboration report"""
        metrics = self.get_collaboration_metrics()

        report = f"""
=== Agent Collaboration Report ===

Total Interactions: {metrics['total_interactions']}
Active Agents: {metrics['agents_active']}

Message Type Breakdown:
"""
        for msg_type, count in metrics.get("message_types", {}).items():
            report += f"  - {msg_type}: {count}\n"

        if metrics["most_active_pair"]:
            pair, count = metrics["most_active_pair"]
            report += f"\nMost Active Collaboration: {pair} ({count} interactions)\n"

        report += f"\nCollaboration Density: {metrics['collaboration_density']} unique connections\n"

        return report


class WorkflowCoordinator:
    """Coordinates complex multi-agent workflows"""

    def __init__(self, orchestrator: AgentOrchestrator):
        self.orchestrator = orchestrator
        self.logger = AgentCollaborationLogger()

    async def execute_feature_workflow(
        self, feature_spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a complete feature development workflow

        Workflow:
        1. Architect designs feature architecture
        2. Database engineer adds schema changes
        3. API engineer creates endpoints
        4. Service engineer implements logic
        5. Auth engineer adds permissions
        6. Testing engineer creates tests
        7. DevOps engineer updates deployment
        8. Code reviewer approves changes
        """
        results = {}

        # Step 1: Architecture
        arch_task = await self.orchestrator._execute_agent_task(
            AgentRole.ARCHITECT,
            f"Design architecture for {feature_spec['name']}",
            {"requirements": feature_spec.get("requirements", [])},
        )
        results["architecture"] = arch_task

        # Step 2: Database changes (if needed)
        if feature_spec.get("requires_database"):
            db_task = await self.orchestrator._execute_agent_task(
                AgentRole.DATABASE_ENGINEER,
                f"Design schema for {feature_spec['name']}",
                {"feature": feature_spec, "architecture": arch_task},
            )
            results["database"] = db_task

        # Step 3: API endpoints
        if feature_spec.get("requires_api"):
            api_task = await self.orchestrator._execute_agent_task(
                AgentRole.API_ENGINEER,
                f"Design API for {feature_spec['name']}",
                {"feature": feature_spec, "architecture": arch_task},
            )
            results["api"] = api_task

        # Step 4: Business logic
        service_task = await self.orchestrator._execute_agent_task(
            AgentRole.SERVICE_ENGINEER,
            f"Implement business logic for {feature_spec['name']}",
            {
                "feature": feature_spec,
                "api": results.get("api"),
                "database": results.get("database"),
            },
        )
        results["services"] = service_task

        # Step 5: Tests
        test_task = await self.orchestrator._execute_agent_task(
            AgentRole.TESTING_ENGINEER,
            f"Generate tests for {feature_spec['name']}",
            {"implementation": results},
        )
        results["tests"] = test_task

        # Step 6: Code review
        review_task = await self.orchestrator._execute_agent_task(
            AgentRole.CODE_REVIEWER,
            f"Review {feature_spec['name']} implementation",
            {"implementation": results},
        )
        results["review"] = review_task

        return results

    async def execute_optimization_workflow(
        self, code_to_optimize: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a code optimization workflow

        Agents collaborate to identify and fix performance issues
        """
        # Code reviewer identifies issues
        issues = await self.orchestrator._execute_agent_task(
            AgentRole.CODE_REVIEWER,
            "Identify optimization opportunities",
            {"code": code_to_optimize},
        )

        # Relevant agents fix issues
        optimizations = {}

        if issues.get("database_issues"):
            db_opt = await self.orchestrator._execute_agent_task(
                AgentRole.DATABASE_ENGINEER,
                "Optimize database queries",
                {"issues": issues["database_issues"]},
            )
            optimizations["database"] = db_opt

        if issues.get("api_issues"):
            api_opt = await self.orchestrator._execute_agent_task(
                AgentRole.API_ENGINEER,
                "Optimize API endpoints",
                {"issues": issues["api_issues"]},
            )
            optimizations["api"] = api_opt

        return {"identified_issues": issues, "optimizations": optimizations}

    def get_collaboration_report(self) -> str:
        """Get a report of agent collaboration during workflow"""
        return self.logger.generate_report()


class ConflictResolver:
    """Resolves conflicts between agent proposals"""

    @staticmethod
    async def resolve_design_conflict(
        proposals: List[Dict[str, Any]], orchestrator: AgentOrchestrator
    ) -> Dict[str, Any]:
        """
        When multiple agents propose conflicting solutions,
        the architect makes the final decision
        """
        # Get architect's input
        architect = orchestrator.agents.get(AgentRole.ARCHITECT)
        if not architect:
            # Default: merge proposals
            return ConflictResolver._merge_proposals(proposals)

        # Architect reviews and decides
        decision_task = AgentTask(
            id="conflict_resolution",
            role=AgentRole.ARCHITECT,
            description="Resolve design conflict",
            input_data={"proposals": proposals},
        )

        decision = await architect.execute_task(decision_task)
        return decision

    @staticmethod
    def _merge_proposals(proposals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge multiple proposals into one (simple merge)"""
        merged = {}
        for proposal in proposals:
            merged.update(proposal)
        return merged


# Export main classes
__all__ = [
    "AgentTeamBuilder",
    "AgentCollaborationLogger",
    "WorkflowCoordinator",
    "ConflictResolver",
]
