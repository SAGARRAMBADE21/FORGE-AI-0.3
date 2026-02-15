"""Field name normalization utilities for database schema generation."""

import re


def to_snake_case(name: str) -> str:
    """
    Convert camelCase or PascalCase to snake_case.
    
    Examples:
        userId -> user_id
        createdAt -> created_at
        HTTPSConnection -> https_connection
        userID -> user_id
        URLParser -> url_parser
    
    Args:
        name: Field name in camelCase or PascalCase
        
    Returns:
        Field name in snake_case
    """
    # Handle acronyms: HTTPSConnection -> HTTPS_Connection
    name = re.sub('([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
    
    # Handle normal camelCase: userId -> user_Id
    name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
    
    # Convert to lowercase
    return name.lower()


def normalize_field_name(name: str, convention: str = "snake_case") -> str:
    """
    Normalize field name to database naming convention.
    
    Args:
        name: Original field name
        convention: Target naming convention ('snake_case' or 'camelCase')
        
    Returns:
        Normalized field name
    """
    if convention == "snake_case":
        return to_snake_case(name)
    return name


def is_timestamp_field(field_name: str) -> bool:
    """
    Check if a field name represents a timestamp field.
    
    Args:
        field_name: Field name to check
        
    Returns:
        True if field appears to be a timestamp field
    """
    normalized = field_name.lower()
    timestamp_patterns = [
        'created_at', 'createdat',
        'updated_at', 'updatedat',
        'deleted_at', 'deletedat',
        'timestamp', 'time_stamp'
    ]
    
    # Check exact matches
    if normalized in timestamp_patterns:
        return True
    
    # Check for common "At" suffix pattern (e.g., createdAt, updatedAt)
    if normalized.endswith('at') and any(word in normalized for word in ['created', 'updated', 'deleted']):
        return True
    
    return False
