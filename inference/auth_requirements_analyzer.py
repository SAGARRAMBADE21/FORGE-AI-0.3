"""Analyze and infer authentication requirements."""

import logging
import re

from config.settings import Language
from core.types import (
    ApiResourceContract,
    AuthPattern,
    AuthRequirements,
    AuthStrategy,
    AuthType,
    OAuthProviderConfig,
    PermissionDefinition,
    PermissionModel,
    RoleDefinition,
)
from indexers.unified_indexer import UnifiedIndexer

logger = logging.getLogger(__name__)


class AuthRequirementsAnalyzer:
    """
    Analyze frontend to infer complete auth requirements.

    Detects:
    - Auth strategy (JWT, session, OAuth, hybrid)
    - OAuth providers
    - Permission model (RBAC, ABAC)
    - Roles and permissions
    """

    def __init__(self, indexer: UnifiedIndexer):
        self._indexer = indexer

    async def analyze(
        self, auth_pattern: AuthPattern | None, api_resources: list[ApiResourceContract]
    ) -> AuthRequirements:
        """Analyze and build complete auth requirements."""
        # Determine strategy
        strategy = self._determine_strategy(auth_pattern)

        # Detect OAuth providers
        oauth_providers = await self._detect_oauth_providers()

        # Infer permission model
        permission_model, roles, permissions = await self._infer_permissions(
            api_resources
        )

        # Build JWT/session config
        jwt_config = (
            self._build_jwt_config()
            if strategy in (AuthStrategy.JWT, AuthStrategy.HYBRID)
            else {}
        )
        session_config = (
            self._build_session_config()
            if strategy in (AuthStrategy.SESSION, AuthStrategy.HYBRID)
            else {}
        )

        # Detect MFA requirements
        mfa_required = await self._detect_mfa()

        return AuthRequirements(
            strategy=strategy,
            permission_model=permission_model,
            roles=roles,
            permissions=permissions,
            oauth_providers=oauth_providers,
            jwt_config=jwt_config,
            session_config=session_config,
            mfa_required=mfa_required,
            password_policy=self._infer_password_policy(),
        )

    def _determine_strategy(self, auth_pattern: AuthPattern | None) -> AuthStrategy:
        """Determine auth strategy from pattern."""
        if not auth_pattern:
            return AuthStrategy.JWT  # Default

        mapping = {
            AuthType.JWT: AuthStrategy.JWT,
            AuthType.SESSION: AuthStrategy.SESSION,
            AuthType.OAUTH: AuthStrategy.OAUTH,
            AuthType.API_KEY: AuthStrategy.API_KEY,
        }

        return mapping.get(auth_pattern.type, AuthStrategy.JWT)

    async def _detect_oauth_providers(self) -> list[OAuthProviderConfig]:
        """Detect OAuth providers from frontend code."""
        providers = []
        detected = set()

        for file_info in self._indexer.file_index.all_files():
            if file_info.language not in (
                Language.TYPESCRIPT,
                Language.TSX,
                Language.JAVASCRIPT,
                Language.JSX,
            ):
                continue

            content = self._indexer.get_file_content(file_info.path)
            if not content:
                continue

            # Google
            if "google" in content.lower() and "signin" in content.lower():
                if "google" not in detected:
                    detected.add("google")
                    providers.append(
                        OAuthProviderConfig(
                            name="google",
                            client_id_env="GOOGLE_CLIENT_ID",
                            client_secret_env="GOOGLE_CLIENT_SECRET",
                            scopes=["email", "profile"],
                        )
                    )

            # GitHub
            if "github" in content.lower() and (
                "oauth" in content.lower() or "signin" in content.lower()
            ):
                if "github" not in detected:
                    detected.add("github")
                    providers.append(
                        OAuthProviderConfig(
                            name="github",
                            client_id_env="GITHUB_CLIENT_ID",
                            client_secret_env="GITHUB_CLIENT_SECRET",
                            scopes=["user:email"],
                        )
                    )

            # Facebook
            if "facebook" in content.lower() and "login" in content.lower():
                if "facebook" not in detected:
                    detected.add("facebook")
                    providers.append(
                        OAuthProviderConfig(
                            name="facebook",
                            client_id_env="FACEBOOK_APP_ID",
                            client_secret_env="FACEBOOK_APP_SECRET",
                            scopes=["email", "public_profile"],
                        )
                    )

            # Discord
            if "discord" in content.lower() and "oauth" in content.lower():
                if "discord" not in detected:
                    detected.add("discord")
                    providers.append(
                        OAuthProviderConfig(
                            name="discord",
                            client_id_env="DISCORD_CLIENT_ID",
                            client_secret_env="DISCORD_CLIENT_SECRET",
                            scopes=["identify", "email"],
                        )
                    )

        return providers

    async def _infer_permissions(
        self, api_resources: list[ApiResourceContract]
    ) -> tuple[PermissionModel, list[RoleDefinition], list[PermissionDefinition]]:
        """Infer permission model, roles, and permissions."""
        permissions = []
        detected_roles = set()

        # Create permissions from API resources
        for resource in api_resources:
            resource_name = resource.name

            for endpoint in resource.endpoints:
                if endpoint.requires_auth:
                    # Map method to action
                    action = self._method_to_action(endpoint.method)
                    perm_name = f"{resource_name}:{action}"

                    permissions.append(
                        PermissionDefinition(
                            name=perm_name, resource=resource_name, actions=[action]
                        )
                    )

                # Collect role hints from endpoint permissions
                for perm in endpoint.permissions:
                    if perm.lower() in (
                        "admin",
                        "user",
                        "moderator",
                        "editor",
                        "viewer",
                    ):
                        detected_roles.add(perm.lower())

        # Detect roles from frontend code
        detected_roles.update(await self._detect_roles_from_code())

        # Build role definitions
        roles = self._build_roles(list(detected_roles), permissions)

        # Determine permission model
        if len(roles) > 1:
            permission_model = PermissionModel.RBAC
        else:
            permission_model = PermissionModel.SIMPLE

        return permission_model, roles, permissions

    async def _detect_roles_from_code(self) -> set[str]:
        """Detect role names from frontend code."""
        roles = set()

        for file_info in self._indexer.file_index.all_files():
            if file_info.language not in (
                Language.TYPESCRIPT,
                Language.TSX,
                Language.JAVASCRIPT,
                Language.JSX,
            ):
                continue

            content = self._indexer.get_file_content(file_info.path)
            if not content:
                continue

            # Look for role checks
            # role === 'admin', user.role === 'moderator', etc.
            for match in re.finditer(r'role\s*[=!]==?\s*[\'"](\w+)[\'"]', content):
                roles.add(match.group(1).lower())

            # Look for role enums/types
            for match in re.finditer(
                r'type\s+Role\s*=\s*[\'"](\w+)[\'"](?:\s*\|\s*[\'"](\w+)[\'"])*',
                content,
            ):
                for group in match.groups():
                    if group:
                        roles.add(group.lower())

        return roles

    def _build_roles(
        self, role_names: list[str], permissions: list[PermissionDefinition]
    ) -> list[RoleDefinition]:
        """Build role definitions with permissions."""
        roles = []

        # Always include admin with all permissions
        all_perms = [p.name for p in permissions]
        roles.append(RoleDefinition(name="admin", permissions=all_perms, inherits=[]))

        # Add detected roles
        for role_name in role_names:
            if role_name == "admin":
                continue

            # Determine permissions for role
            if role_name == "user":
                # Users can typically read and create their own
                role_perms = [
                    p.name
                    for p in permissions
                    if ":read" in p.name or ":create" in p.name
                ]
            elif role_name == "moderator":
                # Moderators can update/delete
                role_perms = [p.name for p in permissions if ":delete" not in p.name]
            elif role_name == "editor":
                # Editors can read/create/update
                role_perms = [p.name for p in permissions if ":delete" not in p.name]
            elif role_name == "viewer":
                # Viewers can only read
                role_perms = [p.name for p in permissions if ":read" in p.name]
            else:
                role_perms = []

            roles.append(
                RoleDefinition(name=role_name, permissions=role_perms, inherits=[])
            )

        return roles

    def _method_to_action(self, method: str) -> str:
        """Map HTTP method to permission action."""
        mapping = {
            "GET": "read",
            "POST": "create",
            "PUT": "update",
            "PATCH": "update",
            "DELETE": "delete",
        }
        return mapping.get(method, "read")

    def _build_jwt_config(self) -> dict:
        """Build JWT configuration."""
        return {
            "secret_env": "JWT_SECRET",
            "expires_in": "7d",
            "refresh_expires_in": "30d",
            "algorithm": "HS256",
        }

    def _build_session_config(self) -> dict:
        """Build session configuration."""
        return {
            "secret_env": "SESSION_SECRET",
            "cookie_name": "session",
            "max_age": 86400 * 7,  # 7 days
            "secure": True,
            "http_only": True,
            "same_site": "lax",
        }

    async def _detect_mfa(self) -> bool:
        """Detect if MFA is required."""
        for file_info in self._indexer.file_index.all_files():
            content = self._indexer.get_file_content(file_info.path)
            if content and (
                "2fa" in content.lower()
                or "mfa" in content.lower()
                or "totp" in content.lower()
            ):
                return True
        return False

    def _infer_password_policy(self) -> dict:
        """Infer password policy from frontend validation."""
        return {
            "min_length": 8,
            "require_uppercase": True,
            "require_lowercase": True,
            "require_number": True,
            "require_special": False,
        }
