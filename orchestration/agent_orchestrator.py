"""
Multi-Agent Orchestrator for Backend Generation

This module implements a team-based architecture where specialized agents
collaborate to generate production-level backend code.
"""

import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import asyncio

from generation.pipeline import GenerationContext
from config.settings import settings

logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    """Specialized agent roles in the backend team"""
    ARCHITECT = "architect"              # System architecture & design decisions
    DATABASE_ENGINEER = "database"       # Schema, migrations, queries
    API_ENGINEER = "api"                 # REST/GraphQL endpoints
    SERVICE_ENGINEER = "service"         # Business logic & services
    AUTH_ENGINEER = "auth"               # Authentication & authorization
    TESTING_ENGINEER = "testing"         # Test generation & quality
    DEVOPS_ENGINEER = "devops"           # Deployment, Docker, CI/CD
    CODE_REVIEWER = "reviewer"           # Code review & optimization


class MessageType(str, Enum):
    """Types of messages agents can exchange"""
    REQUEST = "request"           # Request for help/data
    RESPONSE = "response"         # Response to request
    PROPOSAL = "proposal"         # Propose a solution
    APPROVAL = "approval"         # Approve a proposal
    REJECTION = "rejection"       # Reject a proposal
    NOTIFICATION = "notification" # Inform about progress
    QUESTION = "question"         # Ask for clarification
    ANSWER = "answer"            # Answer a question


@dataclass
class AgentMessage:
    """Message exchanged between agents"""
    id: str
    from_agent: AgentRole
    to_agent: AgentRole
    message_type: MessageType
    content: Dict[str, Any]
    timestamp: str
    in_reply_to: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentTask:
    """Task assigned to an agent"""
    id: str
    role: AgentRole
    description: str
    input_data: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, in_progress, completed, failed
    output: Optional[Dict[str, Any]] = None
    messages: List[AgentMessage] = field(default_factory=list)


class BackendSubAgent:
    """
    Base class for specialized backend agents.
    
    Each agent has specific expertise and can:
    - Execute tasks in their domain
    - Request help from other agents
    - Respond to requests from other agents
    - Propose solutions for review
    """
    
    def __init__(self, role: AgentRole, orchestrator: 'AgentOrchestrator'):
        self.role = role
        self.orchestrator = orchestrator
        self.capabilities: List[str] = []
        self.current_task: Optional[AgentTask] = None
        
    async def execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """Execute a task - to be implemented by subclasses"""
        raise NotImplementedError
    
    async def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle incoming message from another agent"""
        if message.message_type == MessageType.REQUEST:
            return await self._handle_request(message)
        elif message.message_type == MessageType.QUESTION:
            return await self._handle_question(message)
        elif message.message_type == MessageType.PROPOSAL:
            return await self._handle_proposal(message)
        return None
    
    async def _handle_request(self, message: AgentMessage) -> AgentMessage:
        """Handle a request for help"""
        # Default implementation - subclasses can override
        return AgentMessage(
            id=f"msg_{message.id}_response",
            from_agent=self.role,
            to_agent=message.from_agent,
            message_type=MessageType.RESPONSE,
            content={"status": "processing"},
            timestamp=str(asyncio.get_event_loop().time()),
            in_reply_to=message.id
        )
    
    async def _handle_question(self, message: AgentMessage) -> AgentMessage:
        """Answer a question from another agent"""
        raise NotImplementedError
    
    async def _handle_proposal(self, message: AgentMessage) -> AgentMessage:
        """Review and approve/reject a proposal"""
        raise NotImplementedError
    
    async def send_message(self, to_agent: AgentRole, message_type: MessageType, 
                          content: Dict[str, Any]) -> AgentMessage:
        """Send a message to another agent"""
        message = AgentMessage(
            id=f"msg_{self.role}_{to_agent}_{asyncio.get_event_loop().time()}",
            from_agent=self.role,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            timestamp=str(asyncio.get_event_loop().time())
        )
        return await self.orchestrator.route_message(message)
    
    async def request_help(self, from_agent: AgentRole, request: str, 
                          context: Dict[str, Any]) -> Dict[str, Any]:
        """Request help from another specialized agent"""
        message = await self.send_message(
            from_agent,
            MessageType.REQUEST,
            {"request": request, "context": context}
        )
        return message.content
    
    async def propose_solution(self, to_agent: AgentRole, solution: Dict[str, Any]) -> bool:
        """Propose a solution for another agent to review"""
        response = await self.send_message(
            to_agent,
            MessageType.PROPOSAL,
            solution
        )
        return response.message_type == MessageType.APPROVAL


class AgentOrchestrator:
    """
    Orchestrates the team of specialized backend agents.
    
    Responsibilities:
    - Coordinate multiple agents
    - Route messages between agents
    - Manage task dependencies
    - Aggregate results
    - Ensure consistency
    """
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.agents: Dict[AgentRole, BackendSubAgent] = {}
        self.tasks: List[AgentTask] = []
        self.message_history: List[AgentMessage] = []
        self.shared_context: Dict[str, Any] = {}
        
    def register_agent(self, agent: BackendSubAgent):
        """Register a specialized agent"""
        self.agents[agent.role] = agent
        logger.info(f"Registered agent: {agent.role}")
        
    async def route_message(self, message: AgentMessage) -> AgentMessage:
        """Route a message from one agent to another"""
        self.message_history.append(message)
        
        target_agent = self.agents.get(message.to_agent)
        if not target_agent:
            logger.error(f"Agent {message.to_agent} not found")
            return AgentMessage(
                id=f"error_{message.id}",
                from_agent=AgentRole.ARCHITECT,
                to_agent=message.from_agent,
                message_type=MessageType.RESPONSE,
                content={"error": f"Agent {message.to_agent} not available"},
                timestamp=str(asyncio.get_event_loop().time()),
                in_reply_to=message.id
            )
        
        response = await target_agent.handle_message(message)
        if response:
            self.message_history.append(response)
        return response
    
    async def execute_workflow(self, 
                               context: GenerationContext,
                               progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Execute a complete backend generation workflow.
        
        The workflow involves coordination between multiple agents:
        1. Architect defines overall structure
        2. Database engineer designs schema
        3. API engineer designs endpoints
        4. Service engineer implements business logic
        5. Auth engineer adds security
        6. Testing engineer creates tests
        7. DevOps engineer adds deployment configs
        8. Code reviewer ensures quality
        """
        logger.info("Starting multi-agent backend generation workflow")
        
        # Phase 1: Architecture & Planning
        if progress_callback:
            progress_callback("architecture", "Architect planning system design...")
        
        architecture = await self._execute_agent_task(
            AgentRole.ARCHITECT,
            "Design system architecture",
            {"context": context, "requirements": context.features}
        )
        self.shared_context["architecture"] = architecture
        
        # Phase 2: Parallel Design Phase
        if progress_callback:
            progress_callback("design", "Engineers designing components...")
        
        design_tasks = await asyncio.gather(
            self._execute_agent_task(
                AgentRole.DATABASE_ENGINEER,
                "Design database schema",
                {"models": context.models, "relations": context.relations}
            ),
            self._execute_agent_task(
                AgentRole.API_ENGINEER,
                "Design API structure",
                {"resources": context.api_resources, "architecture": architecture}
            ),
            self._execute_agent_task(
                AgentRole.AUTH_ENGINEER,
                "Design authentication system",
                {"auth_requirements": context.auth_requirements}
            )
        )
        
        self.shared_context.update({
            "schema": design_tasks[0],
            "api_design": design_tasks[1],
            "auth_design": design_tasks[2]
        })
        
        # Phase 3: Implementation Phase
        if progress_callback:
            progress_callback("implementation", "Generating production code...")
        
        implementation = await asyncio.gather(
            self._execute_agent_task(
                AgentRole.DATABASE_ENGINEER,
                "Generate database code",
                {"schema": design_tasks[0]}
            ),
            self._execute_agent_task(
                AgentRole.API_ENGINEER,
                "Generate API endpoints",
                {"api_design": design_tasks[1], "schema": design_tasks[0]}
            ),
            self._execute_agent_task(
                AgentRole.SERVICE_ENGINEER,
                "Generate business services",
                {"service_architecture": context.service_architecture,
                 "schema": design_tasks[0]}
            ),
            self._execute_agent_task(
                AgentRole.AUTH_ENGINEER,
                "Generate auth implementation",
                {"auth_design": design_tasks[2]}
            )
        )
        
        # Phase 4: Testing & DevOps
        if progress_callback:
            progress_callback("quality", "Adding tests and deployment configs...")
        
        quality_tasks = await asyncio.gather(
            self._execute_agent_task(
                AgentRole.TESTING_ENGINEER,
                "Generate comprehensive tests",
                {"implementation": implementation, "context": context}
            ),
            self._execute_agent_task(
                AgentRole.DEVOPS_ENGINEER,
                "Generate deployment configs",
                {"architecture": architecture, "context": context}
            )
        )
        
        # Phase 5: Code Review & Optimization
        if progress_callback:
            progress_callback("review", "Code reviewer ensuring quality...")
        
        reviewed_code = await self._execute_agent_task(
            AgentRole.CODE_REVIEWER,
            "Review and optimize all generated code",
            {
                "implementation": implementation,
                "tests": quality_tasks[0],
                "devops": quality_tasks[1]
            }
        )
        
        # Aggregate results
        return {
            "architecture": architecture,
            "database": implementation[0],
            "api": implementation[1],
            "services": implementation[2],
            "auth": implementation[3],
            "tests": quality_tasks[0],
            "devops": quality_tasks[1],
            "review": reviewed_code,
            "messages": self.message_history,
            "shared_context": self.shared_context
        }
    
    async def _execute_agent_task(self, role: AgentRole, description: str, 
                                  input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task with a specific agent"""
        agent = self.agents.get(role)
        if not agent:
            logger.error(f"Agent {role} not available")
            return {"error": f"Agent {role} not available"}
        
        task = AgentTask(
            id=f"task_{role}_{len(self.tasks)}",
            role=role,
            description=description,
            input_data=input_data,
            status="in_progress"
        )
        
        self.tasks.append(task)
        agent.current_task = task
        
        try:
            result = await agent.execute_task(task)
            task.status = "completed"
            task.output = result
            logger.info(f"Task completed by {role}: {description}")
            return result
        except Exception as e:
            task.status = "failed"
            logger.error(f"Task failed for {role}: {e}")
            return {"error": str(e)}
    
    def get_agent_collaboration_summary(self) -> Dict[str, Any]:
        """Get a summary of how agents collaborated"""
        message_counts = {}
        for msg in self.message_history:
            key = f"{msg.from_agent} -> {msg.to_agent}"
            message_counts[key] = message_counts.get(key, 0) + 1
        
        return {
            "total_messages": len(self.message_history),
            "message_breakdown": message_counts,
            "tasks_completed": len([t for t in self.tasks if t.status == "completed"]),
            "tasks_failed": len([t for t in self.tasks if t.status == "failed"]),
            "agents_active": len(self.agents)
        }
