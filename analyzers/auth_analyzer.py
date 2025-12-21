"""Detect authentication patterns."""

import re
import logging
from pathlib import Path

from core.types import AuthPattern, AuthType, APICall
from config.settings import Language
from indexers.unified_indexer import UnifiedIndexer

logger = logging.getLogger(__name__)


class AuthAnalyzer:
    """Detect authentication patterns in frontend code."""

    def __init__(self, project_root: Path):
        self.root = project_root

    async def detect(self, indexer: UnifiedIndexer, api_calls: list[APICall]) -> AuthPattern | None:
        """Detect authentication pattern used in the project."""
        auth_type = AuthType.NONE
        storage = key = None
        login_ep = logout_ep = refresh_ep = None

        for file_info in indexer.file_index.all_files():
            if file_info.language not in (Language.TYPESCRIPT, Language.TSX,
                                         Language.JAVASCRIPT, Language.JSX):
                continue

            content = indexer.get_file_content(file_info.path)
            if not content:
                continue

            # Detect JWT/Bearer
            if re.search(r'Bearer\s+', content):
                auth_type = AuthType.JWT

            # Local storage token
            m = re.search(r'localStorage\.(setItem|getItem)\s*\(\s*[\'"](\w*token\w*)[\'"]', content, re.I)
            if m:
                storage, key = "localStorage", m.group(2)
                auth_type = AuthType.JWT

            # Session storage token
            m = re.search(r'sessionStorage\.(setItem|getItem)\s*\(\s*[\'"](\w*token\w*)[\'"]', content, re.I)
            if m:
                storage, key = "sessionStorage", m.group(2)
                auth_type = AuthType.JWT

            # Cookie-based session
            if re.search(r'credentials\s*:\s*[\'"]include[\'"]', content):
                if auth_type == AuthType.NONE:
                    auth_type = AuthType.SESSION
                storage = "cookie"

            # OAuth detection
            if re.search(r'oauth|OAuth|signInWith|signInWithPopup', content, re.I):
                auth_type = AuthType.OAUTH

            # API key detection
            if re.search(r'[xX][-_]?[aA][pP][iI][-_]?[kK]ey|apiKey|api_key', content):
                if auth_type == AuthType.NONE:
                    auth_type = AuthType.API_KEY

        # Find auth endpoints from API calls
        for api in api_calls:
            ep = api.endpoint.lower()
            if '/login' in ep or '/signin' in ep or '/auth/login' in ep:
                login_ep = api.endpoint
            elif '/logout' in ep or '/signout' in ep:
                logout_ep = api.endpoint
            elif '/refresh' in ep or '/token/refresh' in ep:
                refresh_ep = api.endpoint
            elif '/register' in ep or '/signup' in ep:
                pass  # Could track this too

        if auth_type != AuthType.NONE or login_ep:
            logger.info(f"Detected auth: {auth_type.value}")
            return AuthPattern(
                type=auth_type if auth_type != AuthType.NONE else AuthType.JWT,
                storage=storage,
                key=key,
                login_endpoint=login_ep,
                logout_endpoint=logout_ep,
                refresh_endpoint=refresh_ep
            )

        return None