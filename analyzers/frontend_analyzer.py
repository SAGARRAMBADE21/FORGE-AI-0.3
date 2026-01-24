"""Main frontend analyzer combining all extractors."""

import json
import logging
from pathlib import Path

from analyzers.api_extractor import APIExtractor
from analyzers.auth_analyzer import AuthAnalyzer
from analyzers.component_analyzer import ComponentAnalyzer
from analyzers.form_extractor import FormExtractor
from analyzers.type_extractor import TypeExtractor
from config.settings import Language
from core.types import (
    DataModel,
    FrameworkType,
    FrontendAnalysis,
    Relationship,
    RouteInfo,
)
from indexers.unified_indexer import UnifiedIndexer

logger = logging.getLogger(__name__)


class FrontendAnalyzer:
    """Complete frontend analyzer."""

    def __init__(self, project_root: Path):
        self.root = project_root
        self._api_extractor = APIExtractor(project_root)
        self._type_extractor = TypeExtractor(project_root)
        self._form_extractor = FormExtractor(project_root)
        self._component_analyzer = ComponentAnalyzer(project_root)
        self._auth_analyzer = AuthAnalyzer(project_root)

    async def analyze(self, indexer: UnifiedIndexer) -> FrontendAnalysis:
        """Perform comprehensive frontend analysis."""
        logger.info("Starting frontend analysis...")

        # Extract all
        api_calls = await self._api_extractor.extract_all(indexer)
        data_models = await self._type_extractor.extract_all(indexer)
        forms = await self._form_extractor.extract_all(indexer)
        components = await self._component_analyzer.analyze_all(
            indexer, api_calls, forms
        )
        auth = await self._auth_analyzer.detect(indexer, api_calls)
        routes = await self._extract_routes(indexer)

        # Infer relationships
        data_models = self._infer_relationships(data_models, api_calls)

        # Detect framework
        framework = self._detect_framework()

        logger.info(
            f"Analysis complete: {len(api_calls)} APIs, {len(data_models)} models, "
            f"{len(forms)} forms, {len(components)} components, {len(routes)} routes"
        )

        return FrontendAnalysis(
            project=str(self.root),
            framework=framework,
            language=indexer.detect_language(),
            api_calls=api_calls,
            data_models=data_models,
            forms=forms,
            components=components,
            auth=auth,
            routes=routes,
            stats=indexer.stats,
        )

    async def _extract_routes(self, indexer: UnifiedIndexer) -> list[RouteInfo]:
        """Extract routes from the project."""
        routes = []

        # Next.js pages directory
        pages_dir = self.root / "pages"
        if pages_dir.exists():
            routes.extend(self._extract_nextjs_pages(pages_dir))

        # Next.js app directory
        app_dir = self.root / "app"
        if app_dir.exists():
            routes.extend(self._extract_nextjs_app(app_dir))

        # React Router
        for file_info in indexer.file_index.all_files():
            if file_info.language not in (
                Language.TYPESCRIPT,
                Language.TSX,
                Language.JAVASCRIPT,
                Language.JSX,
            ):
                continue
            content = indexer.get_file_content(file_info.path)
            if content and "<Route" in content:
                routes.extend(self._extract_react_router(content, file_info.path))

        return routes

    def _extract_nextjs_pages(self, pages_dir: Path) -> list[RouteInfo]:
        """Extract routes from Next.js pages directory."""
        routes = []

        for path in pages_dir.rglob("*.tsx"):
            if path.name.startswith("_"):
                continue

            rel = path.relative_to(pages_dir)
            route = "/" + str(rel.with_suffix("")).replace("\\", "/")
            route = route.replace("/index", "")
            if not route:
                route = "/"

            # Convert [param] to :param
            is_dynamic = "[" in route
            route = re.sub(r"\[([^\]]+)\]", r":\1", route)
            params = re.findall(r":(\w+)", route)

            routes.append(
                RouteInfo(
                    path=route,
                    component=path.stem,
                    file=str(path.relative_to(self.root)),
                    is_dynamic=is_dynamic,
                    params=params,
                )
            )

        return routes

    def _extract_nextjs_app(self, app_dir: Path) -> list[RouteInfo]:
        """Extract routes from Next.js app directory."""
        routes = []

        for path in app_dir.rglob("page.tsx"):
            rel = path.parent.relative_to(app_dir)
            route = "/" + str(rel).replace("\\", "/")
            if route == "/.":
                route = "/"

            is_dynamic = "[" in route
            route = re.sub(r"\[([^\]]+)\]", r":\1", route)
            params = re.findall(r":(\w+)", route)

            routes.append(
                RouteInfo(
                    path=route,
                    component="page",
                    file=str(path.relative_to(self.root)),
                    is_dynamic=is_dynamic,
                    params=params,
                )
            )

        return routes

    def _extract_react_router(self, content: str, file: str) -> list[RouteInfo]:
        """Extract routes from React Router."""
        routes = []
        import re

        for m in re.finditer(
            r'<Route[^>]*path\s*=\s*[\'"]([^\'"]+)[\'"][^>]*(?:component|element)\s*=\s*\{?\s*<?(\w+)',
            content,
        ):
            path = m.group(1)
            component = m.group(2)

            is_dynamic = ":" in path
            params = re.findall(r":(\w+)", path)

            routes.append(
                RouteInfo(
                    path=path,
                    component=component,
                    file=file,
                    is_dynamic=is_dynamic,
                    params=params,
                )
            )

        return routes

    def _infer_relationships(
        self, models: list[DataModel], api_calls: list
    ) -> list[DataModel]:
        """Infer relationships between models."""
        model_names = {m.name.lower(): m.name for m in models}

        for model in models:
            relationships = []

            for field in model.fields:
                # Foreign key pattern
                if field.name.endswith("Id") or field.name.endswith("_id"):
                    ref = (
                        field.name[:-2]
                        if field.name.endswith("Id")
                        else field.name[:-3]
                    )
                    if ref.lower() in model_names:
                        relationships.append(
                            Relationship(
                                type="manyToOne",
                                target=model_names[ref.lower()],
                                field=field.name,
                                foreign_key=field.name,
                            )
                        )

                # Type reference
                if field.field_type.startswith("relation:"):
                    target = field.field_type.split(":")[1]
                    relationships.append(
                        Relationship(
                            type="oneToMany" if field.array else "manyToOne",
                            target=target,
                            field=field.name,
                        )
                    )

            # Infer from API endpoints
            import re

            for api in api_calls:
                parts = api.endpoint.split("/")
                for i, part in enumerate(parts):
                    if (
                        part.startswith(":")
                        and part.endswith("Id")
                        and i + 1 < len(parts)
                    ):
                        parent = part[1:-2].lower()
                        child = parts[i + 1].lower().rstrip("s")
                        if (
                            parent in model_names
                            and child in model_names
                            and model.name.lower() == child
                        ):
                            rel = Relationship(
                                type="manyToOne",
                                target=model_names[parent],
                                field=f"{parent}Id",
                                foreign_key=f"{parent}Id",
                            )
                            if rel not in relationships:
                                relationships.append(rel)

            model.relationships = relationships

        return models

    def _detect_framework(self) -> FrameworkType:
        """Detect project framework."""
        # Try package.json first
        pkg_path = self.root / "package.json"

        if pkg_path.exists():
            try:
                data = json.loads(pkg_path.read_text())
                deps = {
                    **data.get("dependencies", {}),
                    **data.get("devDependencies", {}),
                }

                framework = self._check_framework_deps(deps)
                if framework != FrameworkType.UNKNOWN:
                    return framework
            except Exception:
                pass

        # Fallback to package-lock.json
        lock_path = self.root / "package-lock.json"
        if lock_path.exists():
            try:
                data = json.loads(lock_path.read_text())
                # package-lock.json structure has dependencies in different places
                deps = {}
                if "dependencies" in data:
                    deps.update(data["dependencies"])
                if "packages" in data and "" in data["packages"]:
                    root_pkg = data["packages"][""]
                    if "dependencies" in root_pkg:
                        deps.update(root_pkg["dependencies"])
                    if "devDependencies" in root_pkg:
                        deps.update(root_pkg["devDependencies"])

                framework = self._check_framework_deps(deps)
                if framework != FrameworkType.UNKNOWN:
                    return framework
            except Exception:
                pass

        # Python frameworks
        for file in ["requirements.txt", "pyproject.toml"]:
            path = self.root / file
            if path.exists():
                try:
                    content = path.read_text().lower()
                    if "fastapi" in content:
                        return FrameworkType.FASTAPI
                    if "django" in content:
                        return FrameworkType.DJANGO
                    if "flask" in content:
                        return FrameworkType.FLASK
                except Exception:
                    pass

        return FrameworkType.UNKNOWN

    def _check_framework_deps(self, deps: dict) -> FrameworkType:
        """Check framework from dependencies dict."""
        if "next" in deps:
            return FrameworkType.NEXT
        if "nuxt" in deps:
            return FrameworkType.NUXT
        if "@angular/core" in deps:
            return FrameworkType.ANGULAR
        if "svelte" in deps:
            return FrameworkType.SVELTE
        if "vue" in deps:
            return FrameworkType.VUE
        if "react" in deps:
            return FrameworkType.REACT
        if "express" in deps:
            return FrameworkType.EXPRESS

        return FrameworkType.UNKNOWN


# Import re at module level
import re
