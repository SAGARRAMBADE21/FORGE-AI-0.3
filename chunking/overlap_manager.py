"""Overlap manager for maintaining context between chunks."""

import logging
from typing import List
from core.types import Chunk
from core.utils import count_tokens
from config.settings import settings

logger = logging.getLogger(__name__)


class OverlapManager:
    """
    Manages overlap between adjacent chunks to maintain context continuity.
    
    Ensures that semantic boundaries are preserved and related code stays connected.
    """
    
    def __init__(self):
        self.overlap_tokens = settings.chunking.overlap_tokens
        self.min_overlap_lines = 2
        self.max_overlap_lines = 10
    
    def add_overlap_to_chunks(self, chunks: List[Chunk], lines: List[str]) -> List[Chunk]:
        """
        Add overlapping context between consecutive chunks.
        
        Args:
            chunks: List of chunks to process (must be sorted by start_line)
            lines: Source file lines
            
        Returns:
            Updated chunks with overlap information
        """
        if not chunks or len(chunks) < 2:
            return chunks
        
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            curr_chunk = chunks[i]
            
            self._add_overlap(prev_chunk, curr_chunk, lines)
        
        return chunks
    
    def _add_overlap(self, prev: Chunk, curr: Chunk, lines: List[str]) -> None:
        """
        Add overlap context from previous chunk to current chunk.
        
        Args:
            prev: Previous chunk
            curr: Current chunk to add overlap to
            lines: Source file lines
        """
        # Calculate gap between chunks
        gap = curr.start_line - prev.end_line - 1
        
        # If chunks are too far apart, don't add overlap
        if gap > 10:
            return
        
        # Calculate optimal overlap size
        overlap_lines = self._calculate_overlap_size(prev, curr, lines)
        
        if overlap_lines == 0:
            return
        
        # Determine overlap start position
        overlap_start = max(
            prev.end_line - overlap_lines + 1,
            prev.start_line
        )
        
        # Store overlap metadata
        if not hasattr(curr, 'metadata'):
            curr.metadata = {}
        
        curr.metadata['overlap_prev'] = {
            'lines': prev.end_line - overlap_start + 1,
            'start': overlap_start,
            'end': prev.end_line
        }
        
        # If current chunk doesn't already include this range, extend it
        if curr.start_line > overlap_start:
            # Reconstruct chunk content with overlap
            new_start = overlap_start
            new_content = '\n'.join(lines[new_start:curr.end_line + 1])
            
            # Update chunk
            curr.content = new_content
            curr.start_line = new_start
            curr.metadata['tokens'] = count_tokens(new_content)
    
    def _calculate_overlap_size(self, prev: Chunk, curr: Chunk, lines: List[str]) -> int:
        """
        Calculate optimal overlap size in lines.
        
        Args:
            prev: Previous chunk
            curr: Current chunk
            lines: Source file lines
            
        Returns:
            Number of lines to overlap
        """
        # Token-based calculation
        estimated_lines = max(
            self.min_overlap_lines,
            min(self.overlap_tokens // 15, self.max_overlap_lines)  # ~15 tokens per line estimate
        )
        
        # Don't exceed previous chunk size
        max_from_prev = prev.end_line - prev.start_line + 1
        overlap_lines = min(estimated_lines, max_from_prev)
        
        # Try to find a good boundary (end of function, class, etc.)
        overlap_lines = self._adjust_to_boundary(
            prev, 
            overlap_lines, 
            lines
        )
        
        return overlap_lines
    
    def _adjust_to_boundary(
        self, 
        chunk: Chunk, 
        target_lines: int, 
        lines: List[str]
    ) -> int:
        """
        Adjust overlap to end at a semantic boundary.
        
        Args:
            chunk: Chunk to analyze
            target_lines: Target number of overlap lines
            lines: Source file lines
            
        Returns:
            Adjusted line count
        """
        start_search = max(
            chunk.end_line - target_lines - 3,
            chunk.start_line
        )
        end_search = chunk.end_line
        
        # Look for good boundary markers
        boundary_markers = [
            '}',  # End of block
            ')',  # End of parameters
            '];', # End of array
            'return',  # Return statement
            '"""',  # End of docstring
            "'''",  # End of docstring
        ]
        
        best_boundary = target_lines
        
        for i in range(end_search, start_search - 1, -1):
            if i < 0 or i >= len(lines):
                continue
                
            line = lines[i].strip()
            
            # Check if this is a good boundary
            for marker in boundary_markers:
                if marker in line:
                    lines_from_end = chunk.end_line - i
                    # Prefer boundaries closer to target
                    if abs(lines_from_end - target_lines) < abs(best_boundary - target_lines):
                        best_boundary = lines_from_end
                        break
        
        return max(self.min_overlap_lines, min(best_boundary, self.max_overlap_lines))
    
    def merge_overlapping_chunks(
        self, 
        chunks: List[Chunk], 
        lines: List[str]
    ) -> List[Chunk]:
        """
        Merge chunks that have significant overlap.
        
        Args:
            chunks: List of chunks to potentially merge
            lines: Source file lines
            
        Returns:
            List of merged chunks
        """
        if not chunks:
            return chunks
        
        merged = []
        current = chunks[0]
        
        for next_chunk in chunks[1:]:
            # Check if chunks should be merged
            should_merge = self._should_merge(current, next_chunk)
            
            if should_merge:
                current = self._merge_chunks(current, next_chunk, lines)
            else:
                merged.append(current)
                current = next_chunk
        
        # Add the last chunk
        merged.append(current)
        
        return merged
    
    def _should_merge(self, chunk1: Chunk, chunk2: Chunk) -> bool:
        """
        Determine if two chunks should be merged.
        
        Args:
            chunk1: First chunk
            chunk2: Second chunk
            
        Returns:
            True if chunks should be merged
        """
        # Check if chunks overlap or are very close
        gap = chunk2.start_line - chunk1.end_line
        
        if gap < 0:  # Actual overlap
            return True
        
        if gap <= 2:  # Very close chunks
            # Check if combined size is reasonable
            combined_tokens = chunk1.metadata.get('tokens', 0) + chunk2.metadata.get('tokens', 0)
            if combined_tokens <= settings.chunking.max_tokens:
                return True
        
        return False
    
    def _merge_chunks(self, chunk1: Chunk, chunk2: Chunk, lines: List[str]) -> Chunk:
        """
        Merge two chunks into one.
        
        Args:
            chunk1: First chunk
            chunk2: Second chunk
            lines: Source file lines
            
        Returns:
            Merged chunk
        """
        from core.utils import generate_id, extract_keywords
        
        # Determine the full range
        new_start = min(chunk1.start_line, chunk2.start_line)
        new_end = max(chunk1.end_line, chunk2.end_line)
        
        # Create new content
        new_content = '\n'.join(lines[new_start:new_end + 1])
        
        # Merge metadata
        merged_metadata = chunk1.metadata.copy()
        merged_metadata.update(chunk2.metadata)
        merged_metadata['tokens'] = count_tokens(new_content)
        merged_metadata['merged_from'] = [
            chunk1.id,
            chunk2.id
        ]
        
        # Create merged chunk
        merged = Chunk(
            id=generate_id(),
            content=new_content,
            file=chunk1.file,
            start_line=new_start,
            end_line=new_end,
            language=chunk1.language,
            chunk_type=chunk1.chunk_type,
            symbols=list(set(chunk1.symbols + chunk2.symbols)),
            dependencies=list(set(chunk1.dependencies + chunk2.dependencies)),
            metadata=merged_metadata
        )
        
        # Merge keywords
        if hasattr(chunk1, 'keywords') and hasattr(chunk2, 'keywords'):
            merged.metadata['keywords'] = extract_keywords(new_content)
        
        return merged


_overlap_manager: OverlapManager | None = None


def get_overlap_manager() -> OverlapManager:
    """Get singleton overlap manager instance."""
    global _overlap_manager
    if _overlap_manager is None:
        _overlap_manager = OverlapManager()
    return _overlap_manager
