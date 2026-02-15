"""
Utility for filtering TypeScript/frontend types to identify domain models.

This module provides functions to distinguish between:
- Domain models (User, Product, Order, Todo) - should be in database
- UI types (FormData, Props, State, Context) - should NOT be in database
"""

from typing import List, Set


# Common UI type patterns to exclude
UI_SUFFIXES: List[str] = [
    "FormData", "Form", "Schema", "Context", "ContextType",
    "Props", "State", "Filter", "Filters", "Config", "Configuration",
    "Toast", "Toaster", "Action", "Event", "Handler", "Callback",
    "Ref", "Hook", "Component", "Value", "Field", "Item",
    "Option", "Options", "Setting", "Settings",
    "UI", "View", "Dialog", "Modal", "Popup",
    "Styles", "Style", "Theme", "Colors",
    "Validator", "Validation", "Error", "Errors"
]

UI_PREFIXES: List[str] = [
    "Use", "With", "Handle", "Form", "Input", "Select",
    "On", "Handle", "Create", "Update", "Delete",  # Event handlers
    "Is", "Has", "Should", "Can"  # Boolean flags
]

# Keywords that indicate UI/temporary types
UI_KEYWORDS: Set[str] = {
    "temp", "temporary", "local", "current", "selected",
    "active", "hover", "focus", "disabled", "loading",
    "toaster", "toast", "notification", "alert", "message"
}


def is_domain_model(type_name: str, file_path: str = None) -> bool:
    """
    Determine if a TypeScript type represents a domain model.
    
    Domain models are business entities that should be stored in a database.
    UI types, form data, and component props should be excluded.
    
    Args:
        type_name: The name of the TypeScript type/interface
        file_path: Optional path to the source file (for location-based filtering)
        
    Returns:
        True if this is likely a domain model, False if it's a UI type
        
    Examples:
        >>> is_domain_model("User")
        True
        >>> is_domain_model("UserFormData")
        False
        >>> is_domain_model("TodoProps", "/components/TodoList.tsx")
        False
        >>> is_domain_model("User", "/models/User.ts")
        True
    """
    if not type_name or len(type_name) < 2:
        return False
    
    # File path heuristics (highest priority)
    if file_path:
        path_lower = file_path.lower()
        
        # Exclude UI component paths
        ui_paths = ["/components/", "/views/", "/pages/", "/ui/", "/forms/", "/hooks/", "/layouts/"]
        if any(ui_path in path_lower for ui_path in ui_paths):
            return False
        
        # Strongly prefer domain/model paths
        domain_paths = ["/models/", "/entities/", "/domain/", "/types/models", "/shared/models"]
        if any(domain_path in path_lower for domain_path in domain_paths):
            return True
    
    # Check for UI suffixes
    for suffix in UI_SUFFIXES:
        if type_name.endswith(suffix):
            return False
    
    # Check for UI prefixes
    for prefix in UI_PREFIXES:
        if type_name.startswith(prefix):
            return False
    
    # Check for UI keywords in the name
    name_lower = type_name.lower()
    for keyword in UI_KEYWORDS:
        if keyword in name_lower:
            return False
    
    # Likely a domain model
    return True


def filter_domain_models(type_names: List[str]) -> List[str]:
    """
    Filter a list of type names to only include domain models.
    
    Args:
        type_names: List of TypeScript type/interface names
        
    Returns:
        Filtered list containing only domain model names
        
    Example:
        >>> types = ["User", "Product", "LoginFormData", "TodoContext"]
        >>> filter_domain_models(types)
        ['User', 'Product']
    """
    return [name for name in type_names if is_domain_model(name)]


def get_excluded_reason(type_name: str) -> str:
    """
    Get the reason why a type was excluded (for debugging/logging).
    
    Args:
        type_name: The name of the TypeScript type
        
    Returns:
        Human-readable reason for exclusion, or empty string if it's a domain model
    """
    if is_domain_model(type_name):
        return ""
    
    # Check suffixes
    for suffix in UI_SUFFIXES:
        if type_name.endswith(suffix):
            return f"Ends with '{suffix}' (UI type suffix)"
    
    # Check prefixes
    for prefix in UI_PREFIXES:
        if type_name.startswith(prefix):
            return f"Starts with '{prefix}' (UI type prefix)"
    
    # Check keywords
    name_lower = type_name.lower()
    for keyword in UI_KEYWORDS:
        if keyword in name_lower:
            return f"Contains '{keyword}' (UI keyword)"
    
    return "Unknown reason"
