"""Detect authentication patterns."""

import logging
import re
from pathlib import Path

from config.settings import Language
from core.types import APICall, AuthPattern, AuthType
from indexers.unified_indexer import UnifiedIndexer

logger = logging.getLogger(__name__)


class AuthAnalyzer:
    """Detect authentication patterns in frontend code."""

    # Modern auth provider detection patterns
    AUTH_PROVIDERS = {
        "firebase": [
            r"firebase.*/auth",
            r"signInWithEmailAndPassword",
            r"signInWithPopup",
            r"signInWithGoogle",
            r"createUserWithEmailAndPassword",
            r"onAuthStateChanged",
            r"getAuth\s*\(",
        ],
        "supabase": [
            r"supabase\.auth\.",
            r"@supabase/auth-helpers",
            r"createClient.*supabase",
            r"supabase\.auth\.signIn",
            r"supabase\.auth\.signUp",
        ],
        "nextauth": [
            r"next-auth",
            r"@auth/",
            r"NextAuth",
            r"useSession\s*\(",
            r"getServerSession",
            r"signIn\s*\(",
            r"getSession\s*\(",
            r"SessionProvider",
        ],
        "clerk": [
            r"@clerk/",
            r"useUser\s*\(",
            r"useAuth\s*\(",
            r"ClerkProvider",
            r"SignIn",
            r"SignUp",
            r"UserButton",
        ],
        "auth0": [
            r"@auth0/",
            r"useAuth0\s*\(",
            r"Auth0Provider",
            r"loginWithRedirect",
            r"getAccessTokenSilently",
        ],
        "kinde": [
            r"@kinde-oss/",
            r"useKindeAuth",
            r"KindeProvider",
        ],
        "lucia": [
            r"lucia-auth",
            r"lucia\s*\(",
            r"validateSession",
        ],
    }

    def __init__(self, project_root: Path):
        self.root = project_root

    async def detect(
        self, indexer: UnifiedIndexer, api_calls: list[APICall]
    ) -> AuthPattern | None:
        """Detect authentication pattern used in the project."""
        auth_type = AuthType.NONE
        storage = key = None
        login_ep = logout_ep = refresh_ep = None
        detected_provider = None
        protected_routes = []

        for file_info in indexer.file_index.all_files():
            if file_info.language not in (
                Language.TYPESCRIPT,
                Language.TSX,
                Language.JAVASCRIPT,
                Language.JSX,
            ):
                continue

            content = indexer.get_file_content(file_info.path)
            if not content:
                continue

            # Detect modern auth providers
            for provider, patterns in self.AUTH_PROVIDERS.items():
                for pattern in patterns:
                    if re.search(pattern, content, re.I):
                        detected_provider = provider
                        auth_type = AuthType.JWT if provider != "auth0" else AuthType.OAUTH
                        break
                if detected_provider:
                    break

            # Detect JWT/Bearer
            if re.search(r"Bearer\s+", content):
                auth_type = AuthType.JWT

            # Local storage token
            m = re.search(
                r'localStorage\.(setItem|getItem)\s*\(\s*[\'"](\w*token\w*)[\'"]',
                content,
                re.I,
            )
            if m:
                storage, key = "localStorage", m.group(2)
                auth_type = AuthType.JWT

            # Session storage token
            m = re.search(
                r'sessionStorage\.(setItem|getItem)\s*\(\s*[\'"](\w*token\w*)[\'"]',
                content,
                re.I,
            )
            if m:
                storage, key = "sessionStorage", m.group(2)
                auth_type = AuthType.JWT

            # Cookie-based session
            if re.search(r'credentials\s*:\s*[\'"]include[\'"]', content):
                if auth_type == AuthType.NONE:
                    auth_type = AuthType.SESSION
                storage = "cookie"

            # OAuth detection
            if re.search(r"oauth|OAuth|signInWith|signInWithPopup", content, re.I):
                auth_type = AuthType.OAUTH

            # API key detection
            if re.search(r"[xX][-_]?[aA][pP][iI][-_]?[kK]ey|apiKey|api_key", content):
                if auth_type == AuthType.NONE:
                    auth_type = AuthType.API_KEY

            # Detect protected routes (middleware patterns)
            if re.search(r"requireAuth|withAuth|ProtectedRoute|AuthGuard", content, re.I):
                # Try to extract route paths
                route_matches = re.findall(r'[\'"](/\w+(?:/\w+)*)[\'"]', content)
                protected_routes.extend(route_matches)

            # NextAuth middleware pattern
            if "middleware" in file_info.path.lower():
                if re.search(r"matcher\s*:\s*\[([^\]]+)\]", content):
                    matcher_match = re.search(r"matcher\s*:\s*\[([^\]]+)\]", content)
                    if matcher_match:
                        routes = re.findall(r'[\'"]([^\'"\s]+)[\'"]', matcher_match.group(1))
                        protected_routes.extend(routes)

        # Find auth endpoints from API calls
        for api in api_calls:
            ep = api.endpoint.lower()
            if "/login" in ep or "/signin" in ep or "/auth/login" in ep:
                login_ep = api.endpoint
            elif "/logout" in ep or "/signout" in ep:
                logout_ep = api.endpoint
            elif "/refresh" in ep or "/token/refresh" in ep:
                refresh_ep = api.endpoint
            elif "/register" in ep or "/signup" in ep:
                pass  # Could track this too

        if auth_type != AuthType.NONE or login_ep or detected_provider:
            provider_info = f" (provider: {detected_provider})" if detected_provider else ""
            logger.info(f"Detected auth: {auth_type.value}{provider_info}")
            return AuthPattern(
                type=auth_type if auth_type != AuthType.NONE else AuthType.JWT,
                storage=storage,
                key=key,
                login_endpoint=login_ep,
                logout_endpoint=logout_ep,
                refresh_endpoint=refresh_ep,
                protected_routes=list(set(protected_routes))[:20],  # Limit to 20
            )

        return None

