"""Context enricher for adding semantic information to chunks."""

import logging
from typing import Dict, List, Set
from core.types import Chunk, Symbol, SymbolKind
from core.utils import extract_keywords, count_tokens
from config.settings import settings

logger = logging.getLogger(__name__)


class ContextEnricher:
    """
    Enriches chunks with additional semantic context.
    
    Adds documentation, parent context, related symbols, and semantic metadata
    to improve retrieval and understanding.
    """
    
    def __init__(self):
        self.max_context_tokens = 200
        self.max_related_symbols = 5
    
    def enrich_chunks(
        self,
        chunks: List[Chunk],
        symbols_by_file: Dict[str, List[Symbol]],
        contents: Dict[str, str]
    ) -> List[Chunk]:
        """
        Enrich all chunks with additional context.
        
        Args:
            chunks: List of chunks to enrich
            symbols_by_file: Symbols organized by file
            contents: File contents by file path
            
        Returns:
            Enriched chunks
        """
        logger.info(f"Enriching {len(chunks)} chunks with context")
        
        # Build symbol lookup
        symbol_lookup = self._build_symbol_lookup(symbols_by_file)
        
        enriched_count = 0
        for chunk in chunks:
            if self._enrich_chunk(chunk, symbol_lookup, contents):
                enriched_count += 1
        
        logger.info(f"Enriched {enriched_count}/{len(chunks)} chunks")
        return chunks
    
    def _enrich_chunk(
        self,
        chunk: Chunk,
        symbol_lookup: Dict[str, Symbol],
        contents: Dict[str, str]
    ) -> bool:
        """
        Enrich a single chunk with context.
        
        Args:
            chunk: Chunk to enrich
            symbol_lookup: Symbol name to Symbol mapping
            contents: File contents
            
        Returns:
            True if chunk was enriched
        """
        enriched = False
        
        # Initialize metadata if needed
        if not hasattr(chunk, 'metadata') or chunk.metadata is None:
            chunk.metadata = {}
        
        # Add parent context
        if self._add_parent_context(chunk, symbol_lookup):
            enriched = True
        
        # Add documentation context
        if self._add_documentation_context(chunk, symbol_lookup):
            enriched = True
        
        # Add related symbols
        if self._add_related_symbols(chunk, symbol_lookup):
            enriched = True
        
        # Add semantic tags
        if self._add_semantic_tags(chunk):
            enriched = True
        
        # Enhance keywords
        if self._enhance_keywords(chunk):
            enriched = True
        
        # Add usage patterns
        if self._add_usage_patterns(chunk):
            enriched = True
        
        return enriched
    
    def _add_parent_context(
        self,
        chunk: Chunk,
        symbol_lookup: Dict[str, Symbol]
    ) -> bool:
        """Add information about parent symbol/scope."""
        # Check if chunk has a symbol
        symbol_name = chunk.metadata.get('symbol_name')
        if not symbol_name:
            return False
        
        symbol = symbol_lookup.get(symbol_name)
        if not symbol or not hasattr(symbol, 'metadata'):
            return False
        
        parent_name = symbol.metadata.get('parent_name')
        if parent_name:
            chunk.metadata['parent_context'] = f"Part of {parent_name}"
            chunk.metadata['scope'] = 'nested'
            return True
        else:
            chunk.metadata['scope'] = 'top-level'
            return True
        
        return False
    
    def _add_documentation_context(
        self,
        chunk: Chunk,
        symbol_lookup: Dict[str, Symbol]
    ) -> bool:
        """Extract and add documentation from docstrings/comments."""
        content = chunk.content if hasattr(chunk, 'content') else ""
        
        # Extract docstrings
        docstring = self._extract_docstring(content)
        if docstring:
            chunk.metadata['docstring'] = docstring
            chunk.metadata['has_documentation'] = True
            
            # Extract summary (first line)
            lines = docstring.split('\n')
            chunk.metadata['doc_summary'] = lines[0].strip() if lines else ""
            
            return True
        
        # Check for inline comments
        comment_ratio = self._calculate_comment_ratio(content)
        if comment_ratio > 0.1:  # More than 10% comments
            chunk.metadata['well_commented'] = True
            chunk.metadata['comment_ratio'] = comment_ratio
            return True
        
        return False
    
    def _add_related_symbols(
        self,
        chunk: Chunk,
        symbol_lookup: Dict[str, Symbol]
    ) -> bool:
        """Find and add related symbols (called functions, used types, etc.)."""
        content = chunk.content if hasattr(chunk, 'content') else ""
        
        # Find function calls
        import re
        function_calls = set(
            re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', content)
        )
        
        # Find type references (capitalized identifiers)
        type_refs = set(
            re.findall(r'\b([A-Z][a-zA-Z0-9_]*)\b', content)
        )
        
        related = []
        
        # Check which symbols exist
        for name in function_calls:
            if name in symbol_lookup:
                related.append({
                    'name': name,
                    'type': 'function_call'
                })
        
        for name in type_refs:
            if name in symbol_lookup:
                related.append({
                    'name': name,
                    'type': 'type_reference'
                })
        
        if related:
            chunk.metadata['related_symbols'] = related[:self.max_related_symbols]
            return True
        
        return False
    
    def _add_semantic_tags(self, chunk: Chunk) -> bool:
        """Add semantic tags based on chunk content."""
        content = chunk.content if hasattr(chunk, 'content') else ""
        tags = []
        
        # Detect patterns
        if 'async' in content or 'await' in content:
            tags.append('async')
        
        if 'class' in content:
            tags.append('object-oriented')
        
        if 'def ' in content or 'function ' in content:
            tags.append('functional')
        
        if 'import ' in content or 'from ' in content or 'require(' in content:
            tags.append('imports')
        
        if 'export ' in content:
            tags.append('exports')
        
        if 'interface ' in content or 'type ' in content:
            tags.append('types')
        
        if 'test' in content.lower() or 'describe(' in content or 'it(' in content:
            tags.append('test')
        
        if '@' in content and ('decorator' in content or 'annotation' in content):
            tags.append('decorated')
        
        # Error handling
        if any(kw in content for kw in ['try', 'catch', 'except', 'finally']):
            tags.append('error-handling')
        
        # Data processing
        if any(kw in content for kw in ['map', 'filter', 'reduce', 'forEach']):
            tags.append('data-processing')
        
        # I/O operations
        if any(kw in content for kw in ['read', 'write', 'open', 'close', 'fetch', 'axios']):
            tags.append('io-operations')
        
        # State management
        if any(kw in content for kw in ['useState', 'useEffect', 'state', 'setState']):
            tags.append('stateful')
        
        if tags:
            chunk.metadata['semantic_tags'] = tags
            return True
        
        return False
    
    def _enhance_keywords(self, chunk: Chunk) -> bool:
        """Enhance keywords with weighted importance."""
        content = chunk.content if hasattr(chunk, 'content') else ""
        
        # Extract keywords with context
        keywords = extract_keywords(content, max_count=30)
        
        if not keywords:
            return False
        
        # Weight keywords based on importance
        weighted_keywords = []
        
        for keyword in keywords:
            weight = 1.0
            
            # Boost if it's a class name (capitalized)
            if keyword[0].isupper():
                weight *= 1.5
            
            # Boost if it appears multiple times
            count = content.count(keyword)
            if count > 1:
                weight *= (1 + min(count / 10, 2))
            
            # Boost if it's in a function/class definition
            if f'def {keyword}' in content or f'class {keyword}' in content:
                weight *= 2.0
            
            weighted_keywords.append({
                'keyword': keyword,
                'weight': round(weight, 2),
                'count': count
            })
        
        # Sort by weight
        weighted_keywords.sort(key=lambda x: x['weight'], reverse=True)
        
        chunk.metadata['weighted_keywords'] = weighted_keywords[:20]
        
        # Keep simple list for backward compatibility
        if not hasattr(chunk, 'metadata') or 'keywords' not in chunk.metadata:
            chunk.metadata['keywords'] = keywords[:20]
        
        return True
    
    def _add_usage_patterns(self, chunk: Chunk) -> bool:
        """Detect and add common usage patterns."""
        content = chunk.content if hasattr(chunk, 'content') else ""
        patterns = []
        
        # Design patterns
        if 'singleton' in content.lower():
            patterns.append('singleton-pattern')
        
        if 'factory' in content.lower():
            patterns.append('factory-pattern')
        
        if 'observer' in content.lower() or 'subscribe' in content.lower():
            patterns.append('observer-pattern')
        
        # Common frameworks
        if 'React' in content or 'useState' in content or 'useEffect' in content:
            patterns.append('react')
        
        if 'express' in content.lower() and ('app.' in content or 'router.' in content):
            patterns.append('express')
        
        if 'fastapi' in content.lower() or '@app.get' in content:
            patterns.append('fastapi')
        
        if 'django' in content.lower():
            patterns.append('django')
        
        # Database patterns
        if any(kw in content.lower() for kw in ['select', 'insert', 'update', 'delete', 'query']):
            patterns.append('database')
        
        if 'orm' in content.lower() or 'model' in content.lower():
            patterns.append('orm')
        
        # API patterns
        if any(kw in content for kw in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']):
            patterns.append('rest-api')
        
        if 'graphql' in content.lower() or 'mutation' in content.lower():
            patterns.append('graphql')
        
        if patterns:
            chunk.metadata['usage_patterns'] = patterns
            return True
        
        return False
    
    def _extract_docstring(self, content: str) -> str:
        """Extract docstring from content."""
        import re
        
        # Python docstrings
        python_match = re.search(r'^\s*["\']{{3}}(.*?)["\']{{3}}', content, re.MULTILINE | re.DOTALL)
        if python_match:
            return python_match.group(1).strip()
        
        # JSDoc comments
        jsdoc_match = re.search(r'/\*\*(.*?)\*/', content, re.DOTALL)
        if jsdoc_match:
            # Clean up JSDoc
            doc = jsdoc_match.group(1)
            lines = [
                line.strip().lstrip('*').strip() 
                for line in doc.split('\n')
            ]
            return '\n'.join(line for line in lines if line)
        
        return ""
    
    def _calculate_comment_ratio(self, content: str) -> float:
        """Calculate ratio of comments to code."""
        import re
        
        # Remove strings to avoid false positives
        content_no_strings = re.sub(r'["\'].*?["\']', '', content)
        
        # Count comment lines
        comment_lines = 0
        
        # Single-line comments
        comment_lines += len(re.findall(r'//.*$', content_no_strings, re.MULTILINE))
        comment_lines += len(re.findall(r'#.*$', content_no_strings, re.MULTILINE))
        
        # Multi-line comments
        for match in re.finditer(r'/\*.*?\*/', content_no_strings, re.DOTALL):
            comment_lines += match.group(0).count('\n') + 1
        
        # Total lines
        total_lines = content.count('\n') + 1
        
        if total_lines == 0:
            return 0.0
        
        return comment_lines / total_lines
    
    def _build_symbol_lookup(
        self,
        symbols_by_file: Dict[str, List[Symbol]]
    ) -> Dict[str, Symbol]:
        """Build a lookup table from symbol name to symbol."""
        lookup = {}
        
        for file, symbols in symbols_by_file.items():
            for symbol in symbols:
                # Use simple name as key
                lookup[symbol.name] = symbol
                
                # Also add qualified name if available
                if hasattr(symbol, 'metadata') and 'qualified_name' in symbol.metadata:
                    qualified = symbol.metadata['qualified_name']
                    lookup[qualified] = symbol
        
        return lookup
    
    def enrich_chunk_with_context_window(
        self,
        chunk: Chunk,
        file_content: str,
        window_lines: int = 5
    ) -> Chunk:
        """
        Add surrounding context to a chunk.
        
        Args:
            chunk: Chunk to enrich
            file_content: Full file content
            window_lines: Number of lines to add before/after
            
        Returns:
            Enriched chunk
        """
        lines = file_content.split('\n')
        
        # Get surrounding lines
        start = max(0, chunk.start_line - window_lines)
        end = min(len(lines), chunk.end_line + window_lines + 1)
        
        # Extract context
        before_context = '\n'.join(lines[start:chunk.start_line])
        after_context = '\n'.join(lines[chunk.end_line + 1:end])
        
        # Add to metadata
        if not hasattr(chunk, 'metadata'):
            chunk.metadata = {}
        
        chunk.metadata['context_before'] = before_context
        chunk.metadata['context_after'] = after_context
        chunk.metadata['context_window'] = window_lines
        
        return chunk


_context_enricher: ContextEnricher | None = None


def get_context_enricher() -> ContextEnricher:
    """Get singleton context enricher instance."""
    global _context_enricher
    if _context_enricher is None:
        _context_enricher = ContextEnricher()
    return _context_enricher
