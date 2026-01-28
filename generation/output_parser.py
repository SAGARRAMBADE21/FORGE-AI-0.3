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

    # Patterns for file detection (order matters - more specific patterns first)
    FILE_PATTERNS = [
        # Primary format: ### FILE: path/to/file.ext (from OUTPUT_FORMAT_PROMPT)
        # Captures: filepath and code content (without language specifier)
        r"### FILE:\s*(.+?)\n```(?:\w+)?\n(.*?)```",
        # Alternative markdown heading formats
        r"## FILE:\s*(.+?)\n```(?:\w+)?\n(.*?)```",
        r"# FILE:\s*(.+?)\n```(?:\w+)?\n(.*?)```",
        # Simpler markdown heading without code block
        r"### FILE:\s*(.+?)\n(.*?)(?=### FILE:|## FILE:|# FILE:|$)",
        r"## FILE:\s*(.+?)\n(.*?)(?=### FILE:|## FILE:|# FILE:|$)",
        # Legacy formats
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

        # First, try the primary ### FILE: format with code blocks
        # Pattern matches: ### FILE: path\n```language\ncode\n```
        file_block_pattern = r'#{1,3}\s*FILE:\s*([^\n]+)\n```(?:\w+)?\n(.*?)```'
        matches = re.findall(file_block_pattern, llm_output, re.DOTALL)
        
        if matches:
            for filepath, content in matches:
                filepath = filepath.strip()
                content = content.strip()
                if filepath and content:
                    files[filepath] = content
            return files

        # Next, try ### FILE: without code blocks (content until next FILE:)
        simple_file_pattern = r'#{1,3}\s*FILE:\s*([^\n]+)\n(.*?)(?=#{1,3}\s*FILE:|$)'
        matches = re.findall(simple_file_pattern, llm_output, re.DOTALL)
        
        if matches:
            for filepath, content in matches:
                filepath = filepath.strip()
                # Remove any code block markers if present
                content = re.sub(r'^```\w*\n?', '', content.strip())
                content = re.sub(r'\n?```$', '', content.strip())
                content = content.strip()
                if filepath and content:
                    files[filepath] = content
            return files

        # Try legacy patterns
        legacy_patterns = [
            r"===FILE:\s*(.+?)===\n(.*?)(?====FILE:|$)",
            r"```(\w+)?\s*#\s*(.+?)\n(.*?)```",
            r"// filepath:\s*(.+?)\n(.*?)(?=// filepath:|$)",
            r"# filepath:\s*(.+?)\n(.*?)(?=# filepath:|$)",
        ]
        
        for pattern in legacy_patterns:
            matches = re.findall(pattern, llm_output, re.DOTALL)
            if matches:
                files.update(self._process_matches(matches, pattern))
                if files:
                    return files

        # If no patterns matched, try structured XML format
        files = self._parse_structured_format(llm_output)

        return files

    def _process_matches(self, matches: List[Tuple], pattern: str) -> Dict[str, str]:
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
