# Message handling
"""
Agent Messaging System - Communication between agents
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from pydantic import BaseModel, Field
import uuid
import asyncio
from collections import defaultdict


class MessageType(str, Enum):
    """Types of messages agents can send"""
    REQUEST = "request"           # Request another agent to do something
    RESPONSE = "response"         # Response to a request
    BROADCAST = "broadcast"       # Message to all agents
    NOTIFICATION = "notification" # Informational message
    ERROR = "error"              # Error message
    HANDOFF = "handoff"          # Hand off work to another agent
    APPROVAL = "approval"        # Request approval
    FEEDBACK = "feedback"        # Feedback on work


class Message(BaseModel):
    """Message passed between agents"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType
    
    # Routing
    sender: str                  # Sender agent ID
    recipient: Optional[str]     # Recipient agent ID (None for broadcast)
    
    # Content
    subject: str                 # What is this about
    content: Any                 # The actual content
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.now)
    correlation_id: Optional[str] = None  # For request/response matching
    priority: int = 5            # 1-10, higher is more important
    
    # State
    acknowledged: bool = False
    processed: bool = False


class MessageBus:
    """
    Central message bus for agent communication
    Implements pub/sub pattern for agent messaging
    """
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._messages: List[Message] = []
        self._pending: Dict[str, Message] = {}  # correlation_id -> Message
        self._lock = asyncio.Lock()
    
    def subscribe(self, agent_id: str, handler: Callable):
        """Subscribe an agent to receive messages"""
        self._subscribers[agent_id].append(handler)
    
    def unsubscribe(self, agent_id: str):
        """Unsubscribe an agent"""
        if agent_id in self._subscribers:
            del self._subscribers[agent_id]
    
    async def publish(self, message: Message) -> None:
        """Publish a message to the bus"""
        async with self._lock:
            self._messages.append(message)
            
            # Route message
            if message.recipient:
                # Direct message
                if message.recipient in self._subscribers:
                    for handler in self._subscribers[message.recipient]:
                        await self._call_handler(handler, message)
            else:
                # Broadcast
                for agent_id, handlers in self._subscribers.items():
                    if agent_id != message.sender:  # Don't send to self
                        for handler in handlers:
                            await self._call_handler(handler, message)
    
    async def _call_handler(self, handler: Callable, message: Message):
        """Call message handler"""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(message)
            else:
                handler(message)
        except Exception as e:
            print(f"Error in message handler: {e}")
    
    async def request(self, message: Message, timeout: float = 30.0) -> Optional[Message]:
        """
        Send a request and wait for response
        """
        message.correlation_id = message.id
        self._pending[message.correlation_id] = None
        
        await self.publish(message)
        
        # Wait for response
        start = datetime.now()
        while (datetime.now() - start).total_seconds() < timeout:
            if self._pending.get(message.correlation_id):
                response = self._pending.pop(message.correlation_id)
                return response
            await asyncio.sleep(0.1)
        
        # Timeout
        self._pending.pop(message.correlation_id, None)
        return None
    
    def respond(self, original: Message, response_content: Any) -> Message:
        """Create a response message"""
        response = Message(
            type=MessageType.RESPONSE,
            sender=original.recipient,
            recipient=original.sender,
            subject=f"RE: {original.subject}",
            content=response_content,
            correlation_id=original.correlation_id
        )
        
        # Store response for request() to pick up
        if original.correlation_id and original.correlation_id in self._pending:
            self._pending[original.correlation_id] = response
        
        return response
    
    def get_history(self, limit: int = 100) -> List[Message]:
        """Get message history"""
        return self._messages[-limit:]
    
    def clear(self):
        """Clear message history"""
        self._messages.clear()
        self._pending.clear()


# Global message bus instance
message_bus = MessageBus()