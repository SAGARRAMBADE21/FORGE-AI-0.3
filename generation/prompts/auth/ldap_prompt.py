# generation/prompts/auth/ldap_prompt.py
"""
LDAP Authentication Prompt
"""

LDAP_PROMPT = """
# LDAP Authentication Requirements

## LDAP Integration
- Connect to LDAP/Active Directory servers
- Support secure LDAP (LDAPS) connections
- Implement connection pooling
- Handle failover and redundancy

## User Authentication
- Bind operations for user authentication
- Support for simple and SASL authentication
- Password policy enforcement
- Account lockout handling

## Directory Operations
- User search and retrieval
- Group membership queries
- Attribute mapping
- DN resolution

## Security
- Secure credential storage
- TLS/SSL certificate validation
- Timeout and connection management
- Audit logging

## Error Handling
- Connection failure handling
- Invalid credential responses
- Timeout management
- Graceful degradation
"""
