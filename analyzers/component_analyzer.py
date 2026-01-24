"""Analyze React/Vue/Svelte components."""

import logging
import re
from collections import defaultdict
from pathlib import Path

from core.types import ComponentInfo, FieldInfo, SymbolKind
from core.utils import generate_id
from indexers.unified_indexer import UnifiedIndexer

logger = logging.getLogger(__name__)


class ComponentAnalyzer:
    """Analyze frontend components."""

    def __init__(self, project_root: Path):
        self.root = project_root

    async def analyze_all(
        self, indexer: UnifiedIndexer, api_calls: list, forms: list
    ) -> list[ComponentInfo]:
        """Analyze all components."""
        components = []

        # Build lookup maps
        api_by_file = defaultdict(list)
        for api in api_calls:
            api_by_file[api.file].append(api.id)

        form_by_file = defaultdict(list)
        for form in forms:
            form_by_file[form.file].append(form.id)

        # Analyze components
        for sym in indexer.symbol_table.get_by_kind(SymbolKind.COMPONENT):
            comp = self._analyze_component(
                sym, api_by_file.get(sym.file, []), form_by_file.get(sym.file, [])
            )
            components.append(comp)

        # Analyze hooks
        for sym in indexer.symbol_table.get_by_kind(SymbolKind.HOOK):
            components.append(
                ComponentInfo(
                    id=sym.id,
                    name=sym.name,
                    file=sym.file,
                    component_type="hook",
                    state=self._extract_state(sym.source),
                    api_calls=api_by_file.get(sym.file, []),
                    exported=sym.is_exported,
                )
            )

        logger.info(f"Analyzed {len(components)} components")
        return components

    def _analyze_component(
        self, symbol, api_ids: list, form_ids: list
    ) -> ComponentInfo:
        """Analyze a single component."""
        source = symbol.metadata.get("source", symbol.signature)
        file = symbol.file.lower()

        # Determine type
        if "/pages/" in file or "/app/" in file:
            comp_type = "page"
        elif "layout" in file or "layout" in symbol.name.lower():
            comp_type = "layout"
        else:
            comp_type = "component"

        # Extract props
        props = []
        for p in symbol.metadata.get("parameters", []):
            if p.name not in ("props", "children", "_"):
                props.append(
                    FieldInfo(
                        name=p.name, field_type=p.type or "any", required=not p.optional
                    )
                )

        # Also check for destructured props
        props_match = re.search(r"\(\s*\{\s*([^}]+)\s*\}", source)
        if props_match:
            for m in re.finditer(r"(\w+)(?:\s*=\s*[^,}]+)?", props_match.group(1)):
                name = m.group(1)
                if name not in [p.name for p in props] and name not in ("children",):
                    props.append(
                        FieldInfo(
                            name=name, field_type="any", required="=" not in m.group(0)
                        )
                    )

        # Extract state
        state = self._extract_state(source)

        # Extract child components
        children = self._extract_children(source)

        return ComponentInfo(
            id=symbol.id,
            name=symbol.name,
            file=symbol.file,
            component_type=comp_type,
            props=props,
            state=state,
            api_calls=api_ids,
            forms=form_ids,
            children=children,
            exported=symbol.is_exported,
        )

    def _extract_state(self, source: str) -> list[str]:
        """Extract state variables from component."""
        state = []

        # React useState
        for m in re.finditer(
            r"const\s+\[\s*(\w+)\s*,\s*\w+\s*\]\s*=\s*useState", source
        ):
            state.append(m.group(1))

        # React useReducer
        for m in re.finditer(
            r"const\s+\[\s*(\w+)\s*,\s*\w+\s*\]\s*=\s*useReducer", source
        ):
            state.append(m.group(1))

        # Zustand/Recoil selectors
        for m in re.finditer(
            r"const\s+(\w+)\s*=\s*use\w*(?:Store|State|Selector)", source
        ):
            state.append(m.group(1))

        return list(set(state))

    def _extract_children(self, source: str) -> list[str]:
        """Extract child component names from JSX."""
        children = []

        # Find capitalized JSX tags
        for m in re.finditer(r"<([A-Z][a-zA-Z0-9]*)", source):
            name = m.group(1)
            if name not in ("Fragment", "Suspense", "StrictMode", "Provider", "Router"):
                children.append(name)

        return list(set(children))
