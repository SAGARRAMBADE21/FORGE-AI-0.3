"""Plan authentication implementation."""

import logging
from dataclasses import dataclass

from core.types import AuthRequirements, AuthStrategy

logger = logging.getLogger(__name__)


@dataclass
class AuthMiddlewareConfig:
    """Auth middleware configuration."""
    name: str
    type: str
    config: dict


@dataclass
class AuthServiceConfig:
    """Auth service configuration."""
    methods: list[dict]
    dependencies: list[str]
    config: dict


@dataclass
class AuthPlan:
    """Complete auth implementation plan."""
    middleware: list[AuthMiddlewareConfig]
    services: AuthServiceConfig
    models: list[dict]
    routes: list[dict]
    env_vars: list[str]


class AuthPlanner:
    """
    Plan authentication implementation.
    
    Creates:
    - Auth middleware configs
    - Auth service methods
    - User/Session models
    - Auth routes
    """

    def __init__(self):
        pass

    async def plan(self, requirements: AuthRequirements) -> AuthPlan:
        """Create auth implementation plan."""
        middleware = self._plan_middleware(requirements)
        services = self._plan_services(requirements)
        models = self._plan_models(requirements)
        routes = self._plan_routes(requirements)
        env_vars = self._plan_env_vars(requirements)

        return AuthPlan(
            middleware=middleware,
            services=services,
            models=models,
            routes=routes,
            env_vars=env_vars
        )

    def _plan_middleware(self, req: AuthRequirements) -> list[AuthMiddlewareConfig]:
        """Plan auth middleware."""
        middleware = []

        # Authentication middleware
        if req.strategy == AuthStrategy.JWT:
            middleware.append(AuthMiddlewareConfig(
                name='authenticate',
                type='jwt',
                config={
                    'secret_env': req.jwt_config.get('secret_env', 'JWT_SECRET'),
                    'algorithms': [req.jwt_config.get('algorithm', 'HS256')],
                    'token_location': 'header',
                    'header_name': 'Authorization',
                    'header_prefix': 'Bearer',
                }
            ))
        elif req.strategy == AuthStrategy.SESSION:
            middleware.append(AuthMiddlewareConfig(
                name='authenticate',
                type='session',
                config={
                    'secret_env': req.session_config.get('secret_env', 'SESSION_SECRET'),
                    'cookie_name': req.session_config.get('cookie_name', 'session'),
                    'max_age': req.session_config.get('max_age', 86400 * 7),
                }
            ))

        # Authorization middleware
        if req.permission_model.value != 'simple':
            middleware.append(AuthMiddlewareConfig(
                name='authorize',
                type='rbac' if req.permission_model.value == 'rbac' else 'abac',
                config={
                    'roles': [r.name for r in req.roles],
                    'default_role': 'user',
                }
            ))

        # Rate limiting
        middleware.append(AuthMiddlewareConfig(
            name='rateLimit',
            type='rate_limit',
            config={
                'window_ms': 60000,
                'max_requests': 100,
            }
        ))

        return middleware

    def _plan_services(self, req: AuthRequirements) -> AuthServiceConfig:
        """Plan auth service."""
        methods = [
            {
                'name': 'register',
                'params': [
                    {'name': 'email', 'type': 'string'},
                    {'name': 'password', 'type': 'string'},
                    {'name': 'name', 'type': 'string', 'optional': True},
                ],
                'returns': 'User',
                'logic': 'hash_password,create_user,generate_token',
            },
            {
                'name': 'login',
                'params': [
                    {'name': 'email', 'type': 'string'},
                    {'name': 'password', 'type': 'string'},
                ],
                'returns': 'AuthResult',
                'logic': 'find_user,verify_password,generate_token',
            },
            {
                'name': 'logout',
                'params': [{'name': 'userId', 'type': 'string'}],
                'returns': 'void',
                'logic': 'invalidate_token',
            },
            {
                'name': 'validateToken',
                'params': [{'name': 'token', 'type': 'string'}],
                'returns': 'TokenPayload | null',
                'logic': 'verify_jwt',
            },
            {
                'name': 'getCurrentUser',
                'params': [{'name': 'userId', 'type': 'string'}],
                'returns': 'User',
                'logic': 'find_user_by_id',
            },
        ]

        # Add refresh token method for JWT
        if req.strategy == AuthStrategy.JWT:
            methods.append({
                'name': 'refreshToken',
                'params': [{'name': 'refreshToken', 'type': 'string'}],
                'returns': 'AuthResult',
                'logic': 'verify_refresh,generate_new_tokens',
            })

        # Add OAuth methods
        for provider in req.oauth_providers:
            methods.extend([
                {
                    'name': f'get{provider.name.capitalize()}AuthUrl',
                    'params': [],
                    'returns': 'string',
                    'logic': f'build_oauth_url_{provider.name}',
                },
                {
                    'name': f'handle{provider.name.capitalize()}Callback',
                    'params': [{'name': 'code', 'type': 'string'}],
                    'returns': 'AuthResult',
                    'logic': f'exchange_code,get_user_info,upsert_user,generate_token',
                },
            ])

        # Add role/permission methods
        if req.permission_model.value == 'rbac':
            methods.extend([
                {
                    'name': 'assignRole',
                    'params': [
                        {'name': 'userId', 'type': 'string'},
                        {'name': 'role', 'type': 'string'},
                    ],
                    'returns': 'void',
                    'logic': 'update_user_role',
                },
                {
                    'name': 'hasPermission',
                    'params': [
                        {'name': 'userId', 'type': 'string'},
                        {'name': 'permission', 'type': 'string'},
                    ],
                    'returns': 'boolean',
                    'logic': 'get_user_role,check_role_permissions',
                },
            ])

        dependencies = ['UserRepository', 'bcrypt', 'jwt']
        if req.oauth_providers:
            dependencies.append('httpClient')

        return AuthServiceConfig(
            methods=methods,
            dependencies=dependencies,
            config={
                'jwt': req.jwt_config,
                'session': req.session_config,
                'password_policy': req.password_policy,
            }
        )

    def _plan_models(self, req: AuthRequirements) -> list[dict]:
        """Plan auth-related models."""
        models = []

        # User model additions
        user_fields = [
            {'name': 'email', 'type': 'string', 'unique': True},
            {'name': 'passwordHash', 'type': 'string', 'nullable': True},
            {'name': 'name', 'type': 'string', 'nullable': True},
            {'name': 'avatar', 'type': 'string', 'nullable': True},
            {'name': 'emailVerified', 'type': 'boolean', 'default': False},
            {'name': 'role', 'type': 'string', 'default': "'user'"},
        ]

        if req.mfa_required:
            user_fields.extend([
                {'name': 'mfaEnabled', 'type': 'boolean', 'default': False},
                {'name': 'mfaSecret', 'type': 'string', 'nullable': True},
            ])

        models.append({
            'name': 'User',
            'fields': user_fields,
        })

        # Refresh token model for JWT
        if req.strategy == AuthStrategy.JWT:
            models.append({
                'name': 'RefreshToken',
                'fields': [
                    {'name': 'token', 'type': 'string', 'unique': True},
                    {'name': 'userId', 'type': 'string'},
                    {'name': 'expiresAt', 'type': 'datetime'},
                    {'name': 'revoked', 'type': 'boolean', 'default': False},
                ],
            })

        # Session model for session-based auth
        if req.strategy == AuthStrategy.SESSION:
            models.append({
                'name': 'Session',
                'fields': [
                    {'name': 'sessionId', 'type': 'string', 'unique': True},
                    {'name': 'userId', 'type': 'string'},
                    {'name': 'data', 'type': 'json'},
                    {'name': 'expiresAt', 'type': 'datetime'},
                ],
            })

        # OAuth account model
        if req.oauth_providers:
            models.append({
                'name': 'OAuthAccount',
                'fields': [
                    {'name': 'provider', 'type': 'string'},
                    {'name': 'providerAccountId', 'type': 'string'},
                    {'name': 'userId', 'type': 'string'},
                    {'name': 'accessToken', 'type': 'string', 'nullable': True},
                    {'name': 'refreshToken', 'type': 'string', 'nullable': True},
                    {'name': 'expiresAt', 'type': 'datetime', 'nullable': True},
                ],
            })

        return models

    def _plan_routes(self, req: AuthRequirements) -> list[dict]:
        """Plan auth routes."""
        routes = [
            {'method': 'POST', 'path': '/api/auth/register', 'handler': 'register'},
            {'method': 'POST', 'path': '/api/auth/login', 'handler': 'login'},
            {'method': 'POST', 'path': '/api/auth/logout', 'handler': 'logout', 'auth': True},
            {'method': 'GET', 'path': '/api/auth/me', 'handler': 'me', 'auth': True},
        ]

        if req.strategy == AuthStrategy.JWT:
            routes.append({
                'method': 'POST',
                'path': '/api/auth/refresh',
                'handler': 'refresh'
            })

        for provider in req.oauth_providers:
            routes.extend([
                {
                    'method': 'GET',
                    'path': f'/api/auth/oauth/{provider.name}',
                    'handler': f'{provider.name}Auth'
                },
                {
                    'method': 'GET',
                    'path': f'/api/auth/oauth/{provider.name}/callback',
                    'handler': f'{provider.name}Callback'
                },
            ])

        return routes

    def _plan_env_vars(self, req: AuthRequirements) -> list[str]:
        """Plan required environment variables."""
        env_vars = []

        if req.strategy == AuthStrategy.JWT:
            env_vars.extend([
                req.jwt_config.get('secret_env', 'JWT_SECRET'),
                'JWT_EXPIRES_IN',
                'JWT_REFRESH_EXPIRES_IN',
            ])

        if req.strategy == AuthStrategy.SESSION:
            env_vars.append(req.session_config.get('secret_env', 'SESSION_SECRET'))

        for provider in req.oauth_providers:
            env_vars.extend([
                provider.client_id_env,
                provider.client_secret_env,
            ])

        return env_vars