#!/usr/bin/env python3
"""Comprehensively fix all docstrings in fastapi_prompt.py."""
import re

filepath = r'generation\prompts\frameworks\fastapi_prompt.py'

# Read the file
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the start and end of the FASTAPI_PROMPT string
start_idx = None
end_idx = None

for i, line in enumerate(lines):
    if 'FASTAPI_PROMPT = """' in line:
        start_idx = i
    elif start_idx is not None and line.strip() == '"""' and i > start_idx + 1:
        end_idx = i
        break

if start_idx is None or end_idx is None:
    print("Could not find FASTAPI_PROMPT boundaries")
    exit(1)

print(f"Found FASTAPI_PROMPT from line {start_idx} to {end_idx}")

# Process the content between start and end
new_lines = lines[:start_idx +1]  # Keep everything before

for i in range(start_idx + 1, end_idx):
    line = lines[i]
    # Replace any triple-quoted strings with single-line comments
    # This regex finds """text""" and replaces with # text
    line = re.sub(r'"""([^"]+)"""', r'# \1', line)
    new_lines.append(line)

# Add the rest
new_lines.extend(lines[end_idx:])

# Write back
with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"Fixed {filepath}")
