#!/usr/bin/env python3
"""Fix the fastapi_prompt.py file by replacing backticks inside the string."""

filepath = r'generation\prompts\frameworks\fastapi_prompt.py'

# Read the file
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Split by the FASTAPI_PROMPT assignment
parts = content.split('FASTAPI_PROMPT = """', 1)

if len(parts) == 2:
    # Split the prompt part from the rest
    prompt_parts = parts[1].split('"""', 1)
    
    if len(prompt_parts) == 2:
        # Replace ``` with ~~~ in the prompt string only
        fixed_prompt = prompt_parts[0].replace('```', '~~~')
        
        # Reconstruct the file
        new_content = parts[0] + 'FASTAPI_PROMPT = """' + fixed_prompt + '"""' + prompt_parts[1]
        
        # Write back
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"Fixed {filepath}")
    else:
        print("Could not find closing triple quotes")
else:
    print("Could not find FASTAPI_PROMPT assignment")
