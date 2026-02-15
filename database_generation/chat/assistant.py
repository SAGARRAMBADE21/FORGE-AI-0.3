# Chat assistant
"""
Chat Assistant - Main conversational interface
"""

import json
import uuid
from typing import Optional, Dict, Any
from database_generation.chat.session import ChatSession
from database_generation.chat.intent_parser import IntentParser, Intent
from database_generation.chat.command_handler import CommandHandler
from database_generation.engine.ai_engine import ai_engine
from database_generation.prompts.agents import CHAT_AGENT_XML


class ChatAssistant:
    """Main chat assistant for natural language interaction"""
    
    def __init__(self, use_ai: bool = True):
        """
        Initialize chat assistant
        
        Args:
            use_ai: Whether to use AI for intent parsing (False = rule-based only)
        """
        self.use_ai = use_ai
        self.intent_parser = IntentParser()
        self.command_handler = CommandHandler()
        self.sessions: Dict[str, ChatSession] = {}
    
    def create_session(self, session_id: str = None) -> ChatSession:
        """Create a new chat session"""
        sid = session_id or str(uuid.uuid4())
        session = ChatSession(session_id=sid)
        self.sessions[sid] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get existing session"""
        return self.sessions.get(session_id)
    
    def chat(self, 
             message: str, 
             session: ChatSession,
             confirm: bool = False) -> Dict[str, Any]:
        """
        Process a chat message
        
        Args:
            message: User's message
            session: Chat session
            confirm: Whether this is a confirmation of pending action
        
        Returns:
            Response dictionary
        """
        # Add user message to history
        session.add_message("user", message)
        
        # Handle pending confirmation
        if session.pending_confirmation and not confirm:
            if message.lower() in ["yes", "y", "confirm", "ok", "sure"]:
                confirm = True
                message = session.pending_confirmation.get("original_message", message)
            elif message.lower() in ["no", "n", "cancel", "abort"]:
                session.pending_confirmation = None
                response = {
                    "success": True,
                    "message": "Action cancelled.",
                    "data": None
                }
                session.add_message("assistant", response["message"])
                return response
        
        # Parse intent
        if self.use_ai:
            result = self._ai_parse(message, session)
        else:
            result = self._rule_parse(message, session)
        
        intent = result.get("intent", Intent.UNKNOWN)
        params = result.get("params", {})
        confidence = result.get("confidence", 0.0)
        ai_response = result.get("ai_response")
        
        # Check if confirmation needed
        if result.get("requires_confirmation") and not confirm:
            session.pending_confirmation = {
                "intent": intent,
                "params": params,
                "original_message": message
            }
            response = {
                "success": True,
                "message": f"Are you sure you want to {self._describe_action(intent, params)}? (yes/no)",
                "requires_confirmation": True,
                "data": None
            }
            session.add_message("assistant", response["message"])
            return response
        
        # Clear pending confirmation
        session.pending_confirmation = None
        
        # Execute command
        if intent != Intent.UNKNOWN:
            success, message_text, data = self.command_handler.execute(
                intent, params, session
            )
        else:
            # Use AI response or default
            if ai_response:
                message_text = ai_response
                success = True
                data = None
            else:
                success = False
                message_text = "I didn't understand that. Type 'help' for available commands."
                data = None
        
        response = {
            "success": success,
            "message": message_text,
            "data": data,
            "intent": intent.value if intent else "unknown",
            "confidence": confidence
        }
        
        session.add_message("assistant", message_text, {"intent": intent.value if intent else None})
        
        return response
    
    def _rule_parse(self, message: str, session: ChatSession) -> Dict[str, Any]:
        """Parse using rule-based intent parser"""
        intent, params, confidence = self.intent_parser.parse(message)
        
        # Determine if confirmation needed
        requires_confirmation = intent in [
            Intent.REMOVE_ENTITY,
            Intent.REMOVE_FIELD
        ]
        
        return {
            "intent": intent,
            "params": params,
            "confidence": confidence,
            "requires_confirmation": requires_confirmation
        }
    
    def _ai_parse(self, message: str, session: ChatSession) -> Dict[str, Any]:
        """Parse using AI"""
        # First try rule-based for common patterns
        rule_result = self._rule_parse(message, session)
        
        # If high confidence from rules, use that
        if rule_result["confidence"] > 0.8:
            return rule_result
        
        # Otherwise, use AI
        input_data = {
            "user_message": message,
            "current_schema": session.schema.model_dump() if session.schema else None,
            "conversation_history": session.get_history(limit=5),
            "context": session.to_context()
        }
        
        try:
            ai_result = ai_engine.run_agent(CHAT_AGENT_XML, input_data)
            
            if "error" in ai_result:
                # Fall back to rule-based
                return rule_result
            
            # Parse AI response
            intent_str = ai_result.get("intent", "unknown")
            try:
                intent = Intent(intent_str)
            except ValueError:
                intent = Intent.UNKNOWN
            
            # Merge AI operations into params
            params = {}
            operations = ai_result.get("operations", [])
            if operations:
                op = operations[0]
                params = op.get("params", {})
                params["target"] = op.get("target")
            
            return {
                "intent": intent,
                "params": params,
                "confidence": ai_result.get("confidence", 0.5),
                "requires_confirmation": ai_result.get("requires_confirmation", False),
                "ai_response": ai_result.get("response_text")
            }
            
        except Exception as e:
            # Fall back to rule-based on error
            return rule_result
    
    def _describe_action(self, intent: Intent, params: Dict[str, Any]) -> str:
        """Describe an action for confirmation"""
        if intent == Intent.REMOVE_ENTITY:
            return f"remove entity '{params.get('entity_name')}'"
        if intent == Intent.REMOVE_FIELD:
            return f"remove field '{params.get('field_name')}' from '{params.get('entity_name')}'"
        return str(intent.value)


# Singleton instance
chat_assistant = ChatAssistant(use_ai=True)