# generation/output_parser.py
"""
Output Parser - Parses LLM output into files
"""

import re
from typing import Dict, List, Tuple


class OutputParser:
    """
    Parses LLM output into file dictionary
    """
    
    # Patterns for file detection
    FILE_PATTERNS = [
        r"===FILE:\s*(.+?)===\n(.*?)(?====FILE:|$)",
        r"```(\w+)?\s*#\s*(.+?)\n(.*?)```",
        r"// filepath:\s*(.+?)\n(.*?)(?=// filepath:|$)",
        r"# filepath:\s*(.+?)\n(.*?)(?=# filepath:|$)",
    ]
    
    def parse(self, llm_output: str) -> Dict[str, str]:
        """
        Parse LLM output into files
        
        Args:
            llm_output: Raw LLM response
            
        Returns:
            Dict mapping file paths to contents
        """
        files = {}
        
        # Try each pattern
        for pattern in self.FILE_PATTERNS:
            matches = re.findall(pattern, llm_output, re.DOTALL)
            if matches:
                files.update(self._process_matches(matches, pattern))
                
        # If no patterns matched, try structured format
        if not files:
            files = self._parse_structured_format(llm_output)
            
        return files
    
    def _process_matches(
        self,
        matches: List[Tuple],
        pattern: str
    ) -> Dict[str, str]:
        """Process regex matches into files"""
        files = {}
        
        for match in matches:
            if len(match) == 2:
                filepath, content = match
            elif len(match) == 3:
                # For patterns with language specifier
                _, filepath, content = match
            else:
                continue
                
            filepath = filepath.strip()
            content = content.strip()
            
            if filepath and content:
                files[filepath] = content
                
        return files
    
    def _parse_structured_format(self, llm_output: str) -> Dict[str, str]:
        """
        Parse structured format like:
        
        <file path="src/main.ts">
        content
        </file>
        """
        files = {}
        
        pattern = r'<file\s+path="(.+?)">\n?(.*?)</file>'
        matches = re.findall(pattern, llm_output, re.DOTALL)
        
        for filepath, content in matches:
            files[filepath.strip()] = content.strip()
            
        return files
    
    def validate_files(self, files: Dict[str, str]) -> List[str]:
        """
        Validate generated files
        
        Returns:
            List of validation errors
        """
        errors = []
        
        for filepath, content in files.items():
            # Check for empty content
            if not content.strip():
                errors.append(f"Empty file: {filepath}")
                
            # Check for incomplete code blocks
            if content.count("```") % 2 != 0:
                errors.append(f"Unclosed code block in: {filepath}")
                
            # Check for common generation errors
            if "TODO: implement" in content.lower():
                errors.append(f"Incomplete implementation in: {filepath}")
                
        return errors