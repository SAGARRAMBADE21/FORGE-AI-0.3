#!/usr/bin/env python3
"""Fix docstrings in fastapi_prompt.py."""

filepath = r'generation\prompts\frameworks\fastapi_prompt.py'

# Read the file
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace triple-quoted docstrings with single-line comments
replacements = [
    ('"""Schema for creating products"""', '# Schema for creating products'),
    ('"""Schema for product responses"""', '# Schema for product responses'),
    ('"""Dependency for getting async database sessions"""', '# Dependency for getting async database sessions'),
]

for old, new in replacements:
    content = content.replace(old, new)

# Write back
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Fixed {filepath}")
