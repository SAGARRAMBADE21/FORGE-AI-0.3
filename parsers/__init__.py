"""Parsers module."""

from parsers.comment_extractor import CommentExtractor, get_comment_extractor
from parsers.error_recovery import ErrorRecovery, get_error_recovery
from parsers.incremental_parser import IncrementalParser, get_parser
from parsers.language_registry import LanguageRegistry, get_registry

__all__ = [
    "IncrementalParser",
    "get_parser",
    "LanguageRegistry",
    "get_registry",
    "CommentExtractor",
    "get_comment_extractor",
    "ErrorRecovery",
    "get_error_recovery",
]
