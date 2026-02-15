# Intent parser
"""
Intent Parser - NLP Understanding
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum


class Intent(str, Enum):
    """User intent types"""
    CREATE_ENTITY = "create_entity"
    ADD_FIELD = "add_field"
    REMOVE_FIELD = "remove_field"
    MODIFY_FIELD = "modify_field"
    ADD_RELATIONSHIP = "add_relationship"
    ADD_INDEX = "add_index"
    REMOVE_ENTITY = "remove_entity"
    GENERATE_SQL = "generate_sql"
    SHOW_SCHEMA = "show_schema"
    EXPLAIN = "explain"
    SUGGEST = "suggest"
    UNDO = "undo"
    REDO = "redo"
    HELP = "help"
    EXPORT = "export"
    UNKNOWN = "unknown"


class IntentParser:
    """Parse user intent from natural language"""
    
    def __init__(self):
        # Intent patterns (regex)
        self.patterns = {
            Intent.CREATE_ENTITY: [
                r"(?:create|add|make|new)\s+(?:a\s+)?(?:table|entity|collection)\s+(?:called\s+|named\s+)?(\w+)",
                r"(?:create|add|make)\s+(\w+)\s+(?:table|entity)",
                r"(?:i\s+)?(?:need|want)\s+(?:a\s+)?(\w+)\s+(?:table|entity)",
            ],
            Intent.ADD_FIELD: [
                r"add\s+(?:a\s+)?(?:field|column)\s+(\w+)\s+to\s+(\w+)",
                r"add\s+(\w+)\s+(?:field|column)?\s*to\s+(\w+)",
                r"(\w+)\s+should\s+have\s+(?:a\s+)?(\w+)",
                r"(?:include|put)\s+(\w+)\s+in\s+(\w+)",
            ],
            Intent.REMOVE_FIELD: [
                r"(?:remove|delete|drop)\s+(?:the\s+)?(?:field|column)?\s*(\w+)\s+from\s+(\w+)",
                r"(?:remove|delete|drop)\s+(\w+)\.(\w+)",
            ],
            Intent.MODIFY_FIELD: [
                r"make\s+(\w+)(?:\.(\w+))?\s+(unique|required|optional|nullable)",
                r"set\s+(\w+)(?:\.(\w+))?\s+(?:as\s+)?(unique|required|optional|nullable)",
                r"(\w+)(?:\.(\w+))?\s+should\s+be\s+(unique|required|optional|nullable)",
            ],
            Intent.ADD_RELATIONSHIP: [
                r"(\w+)\s+(?:has\s+many|have\s+many)\s+(\w+)",
                r"(\w+)\s+(?:belongs\s+to|has\s+one)\s+(\w+)",
                r"(?:link|connect|relate)\s+(\w+)\s+(?:to|with)\s+(\w+)",
                r"(\w+)\s+and\s+(\w+)\s+(?:are\s+)?(?:related|connected)",
            ],
            Intent.ADD_INDEX: [
                r"(?:add|create)\s+(?:an?\s+)?index\s+on\s+(\w+)\.(\w+)",
                r"index\s+(\w+)\.(\w+)",
            ],
            Intent.REMOVE_ENTITY: [
                r"(?:remove|delete|drop)\s+(?:the\s+)?(?:table|entity)\s+(\w+)",
                r"(?:remove|delete|drop)\s+(\w+)\s+(?:table|entity)",
            ],
            Intent.GENERATE_SQL: [
                r"(?:generate|create|show|give)\s+(?:me\s+)?(?:the\s+)?(?:sql|ddl|query|schema)",
                r"(?:export|convert)\s+(?:to\s+)?(postgresql|mysql|mongodb|postgres|mongo)",
                r"(?:show|get)\s+(?:me\s+)?(?:the\s+)?(postgresql|mysql|mongodb|postgres|mongo)\s+(?:sql|ddl|code)",
            ],
            Intent.SHOW_SCHEMA: [
                r"(?:show|display|list|what)\s+(?:me\s+)?(?:the\s+)?(?:schema|tables|entities|structure)",
                r"what\s+(?:tables|entities)\s+(?:do\s+)?(?:i|we)\s+have",
                r"(?:current|my)\s+schema",
            ],
            Intent.EXPLAIN: [
                r"(?:explain|why|what\s+is|tell\s+me\s+about)\s+(.+)",
                r"what\s+does\s+(\w+)\s+(?:mean|do)",
            ],
            Intent.SUGGEST: [
                r"(?:suggest|recommend|what\s+should|improve)",
                r"(?:any|give\s+me)\s+(?:suggestions|recommendations)",
            ],
            Intent.UNDO: [
                r"undo",
                r"go\s+back",
                r"revert",
            ],
            Intent.REDO: [
                r"redo",
                r"go\s+forward",
            ],
            Intent.HELP: [
                r"(?:help|commands|what\s+can\s+you\s+do)",
                r"how\s+(?:do\s+i|to)",
            ],
            Intent.EXPORT: [
                r"(?:export|save|download)\s+(?:the\s+)?schema",
                r"save\s+(?:to|as)\s+(\w+)",
            ],
        }
        
        # Field type keywords
        self.type_keywords = {
            "string": ["string", "text", "varchar", "char", "str"],
            "text": ["text", "longtext", "content", "description"],
            "integer": ["integer", "int", "number", "count"],
            "bigint": ["bigint", "biginteger", "long"],
            "decimal": ["decimal", "money", "price", "amount", "float", "double"],
            "boolean": ["boolean", "bool", "flag", "is", "has", "can"],
            "timestamp": ["timestamp", "datetime", "date", "time", "created", "updated"],
            "uuid": ["uuid", "id", "identifier", "guid"],
            "json": ["json", "jsonb", "object", "metadata", "settings", "config"],
            "array": ["array", "list", "tags"],
            "enum": ["enum", "status", "type", "category"],
        }
    
    def parse(self, text: str) -> Tuple[Intent, Dict[str, Any], float]:
        """
        Parse user input and extract intent
        
        Returns:
            Tuple of (intent, extracted_params, confidence)
        """
        text_lower = text.lower().strip()
        
        # Try each intent pattern
        for intent, patterns in self.patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    params = self._extract_params(intent, match, text)
                    confidence = self._calculate_confidence(text_lower, intent, match)
                    return intent, params, confidence
        
        return Intent.UNKNOWN, {}, 0.0
    
    def _extract_params(self, intent: Intent, match: re.Match, 
                        original_text: str) -> Dict[str, Any]:
        """Extract parameters based on intent"""
        params = {"groups": match.groups()}
        
        if intent == Intent.CREATE_ENTITY:
            params["entity_name"] = match.group(1)
            params["fields"] = self._extract_fields_from_text(original_text)
        
        elif intent == Intent.ADD_FIELD:
            groups = match.groups()
            if len(groups) >= 2:
                params["field_name"] = groups[0]
                params["entity_name"] = groups[1]
                params["field_type"] = self._infer_field_type(groups[0])
        
        elif intent == Intent.REMOVE_FIELD:
            groups = match.groups()
            if len(groups) >= 2:
                params["field_name"] = groups[0] if '.' not in str(groups[0]) else groups[1]
                params["entity_name"] = groups[1] if '.' not in str(groups[0]) else groups[0]
        
        elif intent == Intent.MODIFY_FIELD:
            groups = match.groups()
            params["entity_name"] = groups[0]
            params["field_name"] = groups[1] if len(groups) > 1 else None
            params["modification"] = groups[-1]
        
        elif intent == Intent.ADD_RELATIONSHIP:
            groups = match.groups()
            params["from_entity"] = groups[0]
            params["to_entity"] = groups[1]
            params["type"] = self._infer_relationship_type(original_text.lower())
        
        elif intent == Intent.ADD_INDEX:
            groups = match.groups()
            params["entity_name"] = groups[0]
            params["field_name"] = groups[1]
        
        elif intent == Intent.REMOVE_ENTITY:
            params["entity_name"] = match.group(1)
        
        elif intent == Intent.GENERATE_SQL:
            # Extract database type if mentioned
            db_match = re.search(r'(postgresql|postgres|mysql|mongodb|mongo)', 
                                original_text.lower())
            if db_match:
                db = db_match.group(1)
                params["database"] = "postgresql" if db in ["postgres", "postgresql"] else \
                                    "mongodb" if db == "mongo" else db
        
        return params
    
    def _extract_fields_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract field definitions from text"""
        fields = []
        
        # Pattern: "with field1, field2, and field3"
        with_match = re.search(r'with\s+(.+?)(?:\.|$)', text.lower())
        if with_match:
            field_text = with_match.group(1)
            # Split by comma or "and"
            field_names = re.split(r',\s*|\s+and\s+', field_text)
            
            for name in field_names:
                name = name.strip()
                if name:
                    # Check for type specification: "email:string" or "email (string)"
                    type_match = re.search(r'(\w+)\s*[:\(]\s*(\w+)', name)
                    if type_match:
                        fields.append({
                            "name": type_match.group(1),
                            "type": self._normalize_type(type_match.group(2))
                        })
                    else:
                        # Clean and infer type
                        clean_name = re.sub(r'[^\w]', '', name)
                        if clean_name:
                            fields.append({
                                "name": clean_name,
                                "type": self._infer_field_type(clean_name)
                            })
        
        return fields
    
    def _infer_field_type(self, field_name: str) -> str:
        """Infer field type from name"""
        name_lower = field_name.lower()
        
        # Direct matches
        if name_lower in ["id", "uuid"]:
            return "uuid"
        if name_lower in ["email", "username", "name", "title", "slug", "phone"]:
            return "string"
        if name_lower in ["description", "content", "body", "bio", "text"]:
            return "text"
        if name_lower in ["price", "amount", "total", "cost", "salary"]:
            return "decimal"
        if name_lower in ["count", "quantity", "age", "number", "order"]:
            return "integer"
        
        # Pattern matches
        if name_lower.startswith(("is_", "has_", "can_", "should_")):
            return "boolean"
        if name_lower.endswith(("_at", "_date", "_time")):
            return "timestamp"
        if name_lower.endswith("_id"):
            return "uuid"
        if name_lower in ["metadata", "settings", "config", "data", "options"]:
            return "json"
        if name_lower in ["status", "type", "role", "state"]:
            return "enum"
        if name_lower in ["tags", "categories", "items"]:
            return "array"
        
        # Default
        return "string"
    
    def _normalize_type(self, type_str: str) -> str:
        """Normalize type string"""
        type_lower = type_str.lower()
        
        for canonical, keywords in self.type_keywords.items():
            if type_lower in keywords:
                return canonical
        
        return "string"
    
    def _infer_relationship_type(self, text: str) -> str:
        """Infer relationship type from text"""
        if "has many" in text or "have many" in text:
            return "one_to_many"
        if "belongs to" in text or "has one" in text:
            return "many_to_one"
        if "many to many" in text:
            return "many_to_many"
        
        return "one_to_many"  # Default
    
    def _calculate_confidence(self, text: str, intent: Intent, 
                             match: re.Match) -> float:
        """Calculate confidence score"""
        # Base confidence from match
        confidence = 0.7
        
        # Boost for longer matches
        match_ratio = len(match.group(0)) / len(text)
        confidence += match_ratio * 0.2
        
        # Boost for exact keywords
        keywords = {
            Intent.CREATE_ENTITY: ["create", "table", "entity"],
            Intent.ADD_FIELD: ["add", "field", "column"],
            Intent.REMOVE_FIELD: ["remove", "delete", "drop"],
            Intent.GENERATE_SQL: ["sql", "generate", "ddl"],
        }
        
        if intent in keywords:
            for kw in keywords[intent]:
                if kw in text:
                    confidence += 0.05
        
        return min(confidence, 1.0)