"""
FORGE Multi-Agent System
A team of AI agents that collaborate to design database schemas
"""

from database_generation.agents.base import BaseAgent, AgentRole, AgentState
from database_generation.agents.message import Message, MessageBus, MessageType
from database_generation.agents.team_manager import TeamManager
from database_generation.agents.lead_architect import LeadArchitectAgent
from database_generation.agents.data_modeler import DataModelerAgent
from database_generation.agents.dba_expert import DBAExpertAgent
from database_generation.agents.sql_writer import SQLWriterAgent
from database_generation.agents.reviewer import ReviewerAgent
from database_generation.agents.chat_agent import ChatAgent

__all__ = [
    # Base
    "BaseAgent",
    "AgentRole",
    "AgentState",
    # Messaging
    "Message",
    "MessageBus",
    "MessageType",
    # Manager
    "TeamManager",
    # Agents
    "LeadArchitectAgent",
    "DataModelerAgent",
    "DBAExpertAgent",
    "SQLWriterAgent",
    "ReviewerAgent",
    "ChatAgent",
]