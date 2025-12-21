"""Extract API calls from frontend code."""

import re
import logging
from pathlib import Path

from core.types import APICall, HTTPMethod
from core.utils import generate_id
from config.settings import Language
from indexers.unified_indexer import UnifiedIndexer

logger = logging.getLogger(__name__)


class APIExtractor:
    """Extract API calls from frontend code."""

    PATTERNS = [
        # Fetch API
        (r'fetch\s*\(\s*[\'"`]([^\'"`]+)[\'"`](?:\s*,\s*(\{[^}]*\}))?', "fetch"),
        (r'fetch\s*\(\s*`([^`]+)`(?:\s*,\s*(\{[^}]*\}))?', "fetch_template"),
        
        # Axios
        (r'axios\s*\.\s*(get|post|put|patch|delete)\s*[<(]\s*[\'"`]([^\'"`]+)[\'"]', "axios"),
        (r'axios\s*\(\s*\{[^}]*url\s*:\s*[\'"`]([^\'"`]+)[\'"][^}]*method\s*:\s*[\'"`](\w+)[\'"]', "axios_config"),
        
        # SWR
        (r'useSWR\s*[<(]\s*[\'"`]([^\'"`]+)[\'"]', "swr"),
        (r'useSWR\s*[<(]\s*`([^`]+)`', "swr_template"),
        
        # React Query
        (r'useQuery\s*[<(][^)]*[\'"`]([^\'"`]+)[\'"]', "react_query"),
        (r'useMutation\s*[<(]', "react_mutation"),
        
        # Other clients
        (r'ky\s*\.\s*(get|post|put|patch|delete)\s*\(\s*[\'"`]([^\'"`]+)[\'"]', "ky"),
        (r'\$http\s*\.\s*(get|post|put|patch|delete)\s*\(\s*[\'"`]([^\'"`]+)[\'"]', "angular_http"),
    ]

    def __init__(self, project_root: Path):
        self.root = project_root

    async def extract_all(self, indexer: UnifiedIndexer) -> list[APICall]:
        """Extract all API calls from indexed files."""
        calls = []
        seen = set()

        for file_info in indexer.file_index.all_files():
            if file_info.language not in (Language.TYPESCRIPT, Language.TSX, 
                                         Language.JAVASCRIPT, Language.JSX):
                continue

            content = indexer.get_file_content(file_info.path)
            if not content:
                continue

            file_calls = self._extract_from_file(content, file_info.path)
            
            for call in file_calls:
                key = (call.method.value, call.endpoint)
                if key not in seen:
                    seen.add(key)
                    calls.append(call)

        logger.info(f"Extracted {len(calls)} API calls")
        return calls

    def _extract_from_file(self, content: str, file: str) -> list[APICall]:
        """Extract API calls from a single file."""
        calls = []
        lines = content.split('\n')

        for pattern, ptype in self.PATTERNS:
            for match in re.finditer(pattern, content, re.DOTALL | re.IGNORECASE):
                call = self._parse_match(match, ptype, file, content, lines)
                if call:
                    calls.append(call)

        return calls

    def _parse_match(self, match, ptype: str, file: str, content: str, lines: list) -> APICall | None:
        """Parse a regex match into an APICall."""
        line_num = content[:match.start()].count('\n')
        method = HTTPMethod.GET
        endpoint = ""

        try:
            if ptype == "fetch":
                endpoint = match.group(1)
                opts = match.group(2) or ""
                method = self._extract_method(opts)
            elif ptype == "fetch_template":
                endpoint = re.sub(r'\$\{(\w+)\}', r':\1', match.group(1))
                opts = match.group(2) or ""
                method = self._extract_method(opts)
            elif ptype == "axios":
                method = HTTPMethod(match.group(1).upper())
                endpoint = match.group(2)
            elif ptype == "axios_config":
                endpoint = match.group(1)
                method = HTTPMethod(match.group(2).upper())
            elif ptype in ("swr", "swr_template", "react_query"):
                endpoint = match.group(1)
                if ptype == "swr_template":
                    endpoint = re.sub(r'\$\{(\w+)\}', r':\1', endpoint)
            elif ptype == "react_mutation":
                method = HTTPMethod.POST
                return None  # Need more context
            elif ptype in ("ky", "angular_http"):
                method = HTTPMethod(match.group(1).upper())
                endpoint = match.group(2)
        except (IndexError, ValueError):
            return None

        if not endpoint or not self._is_api_endpoint(endpoint):
            return None

        endpoint = self._normalize_endpoint(endpoint)
        path_params = re.findall(r':(\w+)|\{(\w+)\}|\[(\w+)\]', endpoint)
        path_params = [p[0] or p[1] or p[2] for p in path_params]

        # Check for auth
        ctx = content[max(0, match.start()-300):min(len(content), match.end()+300)]
        requires_auth = self._check_auth(ctx)

        # Extract types
        body_type, response_type = self._extract_types(ctx)

        return APICall(
            id=generate_id(),
            file=file,
            line=line_num,
            method=method,
            endpoint=endpoint,
            path_params=path_params,
            requires_auth=requires_auth,
            body_type=body_type,
            response_type=response_type,
            source='\n'.join(lines[max(0, line_num-1):min(len(lines), line_num+4)])
        )

    def _extract_method(self, opts: str) -> HTTPMethod:
        """Extract HTTP method from fetch options."""
        m = re.search(r'method\s*:\s*[\'"`](\w+)[\'"`]', opts, re.I)
        if m:
            method = m.group(1).upper()
            if method in HTTPMethod.__members__:
                return HTTPMethod(method)
        return HTTPMethod.GET

    def _is_api_endpoint(self, endpoint: str) -> bool:
        """Check if URL looks like an API endpoint."""
        if re.search(r'\.(js|css|png|jpg|svg|ico)(\?|$)', endpoint):
            return False
        if re.match(r'https?://', endpoint) and not re.search(r'/api/|/v\d+/', endpoint):
            return False
        return True

    def _normalize_endpoint(self, endpoint: str) -> str:
        """Normalize API endpoint."""
        endpoint = re.sub(r'^https?://[^/]+', '', endpoint)
        endpoint = endpoint.split('?')[0].rstrip('/')
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
        endpoint = re.sub(r'\$\{(\w+)\}', r':\1', endpoint)
        return endpoint

    def _check_auth(self, context: str) -> bool:
        """Check if API call requires authentication."""
        patterns = [r'Authorization', r'Bearer', r'token', r'auth', 
                   r'credentials\s*:\s*[\'"]include[\'"]', r'withCredentials']
        return any(re.search(p, context, re.I) for p in patterns)

    def _extract_types(self, context: str) -> tuple[str | None, str | None]:
        """Extract request/response types from context."""
        body_type = response_type = None
        
        # Generic types
        m = re.search(r'<\s*(\w+)\s*(?:,\s*(\w+)\s*)?>', context)
        if m:
            response_type = m.group(1)
            body_type = m.group(2)
        
        # Type assertion
        m = re.search(r'as\s+(\w+)', context)
        if m and not response_type:
            response_type = m.group(1)
        
        return body_type, response_type