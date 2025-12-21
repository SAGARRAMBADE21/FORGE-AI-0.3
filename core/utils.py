"""Utility functions."""

import uuid
import hashlib
import re
from typing import Iterator

_encoder = None


def get_encoder():
    global _encoder
    if _encoder is None:
        import tiktoken
        _encoder = tiktoken.get_encoding("cl100k_base")
    return _encoder


def generate_id() -> str:
    return str(uuid.uuid4())[:12]


def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def count_tokens(text: str) -> int:
    return len(get_encoder().encode(text))


def truncate_tokens(text: str, max_tokens: int) -> str:
    enc = get_encoder()
    tokens = enc.encode(text)
    if len(tokens) <= max_tokens:
        return text
    return enc.decode(tokens[:max_tokens])


def extract_keywords(text: str, max_count: int = 20) -> list[str]:
    text = re.sub(r'//.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    text = re.sub(r'#.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'["\'].*?["\']', '', text)

    identifiers = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', text)

    stop = {
        'if', 'else', 'for', 'while', 'return', 'const', 'let', 'var',
        'function', 'class', 'import', 'export', 'from', 'default',
        'true', 'false', 'null', 'undefined', 'new', 'this', 'self',
        'def', 'async', 'await', 'try', 'catch', 'finally', 'throw',
        'public', 'private', 'protected', 'static', 'readonly',
        'interface', 'type', 'enum', 'extends', 'implements', 'in',
        'and', 'or', 'not', 'is', 'as', 'with', 'pass', 'break',
        'fn', 'mut', 'pub', 'use', 'mod', 'struct', 'impl',
        'func', 'package', 'go', 'defer', 'chan', 'select', 'case',
    }

    keywords = []
    seen = set()
    for ident in identifiers:
        if ident.lower() not in stop and ident not in seen and len(ident) > 2:
            keywords.append(ident)
            seen.add(ident)
            if len(keywords) >= max_count:
                break
    return keywords