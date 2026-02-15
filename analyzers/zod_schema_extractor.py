"""
Zod Schema Extractor - Extract domain models from Zod schemas.

Modern React/TypeScript apps often use Zod for runtime validation.
This extractor identifies Zod schemas and infers domain models from them.
"""

import re
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class ZodSchemaExtractor:
    """
    Extract type information from Zod schemas in TypeScript files.
    
    Zod schemas provide both runtime validation and type inference,
    making them excellent sources for identifying domain models.
    """
    
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
    
    def extract_schemas(self) -> List[Dict]:
        """
        Find and parse Zod schemas in the project.
        
        Returns list of schema definitions:
        [
            {
                "name": "User",
                "source": "zod",
                "fields": [{"name": "id", "type": "string"}, ...],
                "file": "src/schemas/user.ts"
            }
        ]
        
        Example Zod schema:
        ```typescript
        const UserSchema = z.object({
          id: z.string(),
          email: z.string().email(),
          name: z.string()
        });
        
        type User = z.infer<typeof UserSchema>;
        ```
        """
        schemas = []
        
        try:
            # Search TypeScript files
            for file_path in self.project_root.rglob("*.ts"):
                if "node_modules" in str(file_path):
                    continue
                
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    
                    # Find Zod imports
                    if "from 'zod'" not in content and 'from "zod"' not in content:
                        continue
                    
                    # Extract schemas from this file
                    file_schemas = self._extract_from_file(content, file_path)
                    schemas.extend(file_schemas)
                    
                except Exception as e:
                    logger.debug(f"Error reading {file_path}: {e}")
                    continue
        
        except Exception as e:
            logger.warning(f"Zod schema extraction failed: {e}")
        
        logger.info(f"Found {len(schemas)} Zod schemas")
        return schemas
    
    def _extract_from_file(self, content: str, file_path: Path) -> List[Dict]:
        """Extract Zod schemas from a single file."""
        schemas = []
        
        # Pattern 1: const XxxSchema = z.object({...})
        schema_pattern = r'(?:export\s+)?const\s+(\w+Schema)\s*=\s*z\.object\s*\(\s*\{([^}]+)\}'
        
        for match in re.finditer(schema_pattern, content, re.DOTALL):
            schema_name = match.group(1).replace("Schema", "")
            schema_body = match.group(2)
            
            # Skip if it's a UI type
            from utils.domain_model_filter import is_domain_model
            if not is_domain_model(schema_name, str(file_path)):
                continue
            
            # Parse fields
            fields = self._parse_zod_fields(schema_body)
            
            if fields:  # Only add if we found fields
                schemas.append({
                    "name": schema_name,
                    "source": "zod",
                    "fields": fields,
                    "file": str(file_path.relative_to(self.project_root))
                })
        
        return schemas
    
    def _parse_zod_fields(self, schema_body: str) -> List[Dict]:
        """
        Parse Zod field definitions from schema body.
        
        Handles patterns like:
        - id: z.string()
        - email: z.string().email()
        - age: z.number().optional()
        - createdAt: z.date()
        """
        fields = []
        
        # Field pattern: fieldName: z.type()...
        field_pattern = r'(\w+)\s*:\s*z\.(\w+)\s*\('
        
        for match in re.finditer(field_pattern, schema_body):
            field_name = match.group(1)
            zod_type = match.group(2)
            
            # Map Zod types to database types
            type_mapping = {
                "string": "string",
                "number": "integer",
                "boolean": "boolean",
                "date": "datetime",
                "bigint": "bigint",
                "literal": "string",
                "enum": "string",
                "uuid": "string",
            }
            
            field_type = type_mapping.get(zod_type, "string")
            
            fields.append({
                "name": field_name,
                "type": field_type
            })
        
        return fields
