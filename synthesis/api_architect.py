"""Design API architecture from inferred contracts."""

import logging
from dataclasses import dataclass

from core.types import (
    InferredModel, ApiResourceContract, ApiEndpointContract,
    AuthRequirements, PathParam, QueryParam, RequestBodySchema,
    ResponseSchema
)
from core.utils import generate_id

logger = logging.getLogger(__name__)


@dataclass
class ControllerDefinition:
    """Controller definition."""
    name: str
    resource: str
    base_path: str
    methods: list[dict]
    middleware: list[str]
    dependencies: list[str]


@dataclass
class RouteDefinition:
    """Route definition."""
    method: str
    path: str
    handler: str
    controller: str
    middleware: list[str]
    validation_schema: str | None


@dataclass
class ApiArchitecture:
    """Complete API architecture."""
    controllers: list[ControllerDefinition]
    routes: list[RouteDefinition]
    middleware: list[str]
    validation_schemas: dict[str, dict]


class ApiArchitect:
    """
    Design API architecture from contracts.
    
    Responsibilities:
    - Group endpoints into controllers
    - Design route structure
    - Plan middleware chain
    - Design validation schemas
    """

    def __init__(self):
        pass

    async def design_architecture(
        self,
        resources: list[ApiResourceContract],
        models: list[InferredModel],
        auth: AuthRequirements
    ) -> ApiArchitecture:
        """Design complete API architecture."""
        controllers = []
        routes = []
        validation_schemas = {}
        global_middleware = ['errorHandler', 'requestLogger']

        if auth.strategy.value != 'none':
            global_middleware.insert(0, 'cors')

        for resource in resources:
            # Create controller
            controller = self._design_controller(resource, models, auth)
            controllers.append(controller)

            # Create routes
            resource_routes = self._design_routes(resource, controller, auth)
            routes.extend(resource_routes)

            # Create validation schemas
            schemas = self._design_validation_schemas(resource, models)
            validation_schemas.update(schemas)

        # Add auth routes if needed
        if auth.strategy.value != 'none':
            auth_controller, auth_routes = self._design_auth_routes(auth)
            controllers.append(auth_controller)
            routes.extend(auth_routes)

        logger.info(f"Designed {len(controllers)} controllers with {len(routes)} routes")

        return ApiArchitecture(
            controllers=controllers,
            routes=routes,
            middleware=global_middleware,
            validation_schemas=validation_schemas
        )

    def _design_controller(
        self,
        resource: ApiResourceContract,
        models: list[InferredModel],
        auth: AuthRequirements
    ) -> ControllerDefinition:
        """Design a controller for a resource."""
        methods = []

        for endpoint in resource.endpoints:
            method_name = self._endpoint_to_method_name(endpoint)
            
            methods.append({
                'name': method_name,
                'http_method': endpoint.method,
                'path': self._relative_path(endpoint.path, resource.base_path),
                'description': endpoint.description,
                'params': [{'name': p.name, 'type': p.param_type} for p in endpoint.path_params],
                'query': [{'name': q.name, 'type': q.param_type, 'required': q.required} for q in endpoint.query_params],
                'body': endpoint.request_body is not None,
                'auth_required': endpoint.requires_auth,
                'permissions': endpoint.permissions,
            })

        # Determine dependencies
        dependencies = [f"{resource.name}Service"]
        if any(m['auth_required'] for m in methods):
            dependencies.append('AuthService')

        return ControllerDefinition(
            name=f"{resource.name.capitalize()}Controller",
            resource=resource.name,
            base_path=resource.base_path,
            methods=methods,
            middleware=resource.middleware,
            dependencies=dependencies
        )

    def _design_routes(
        self,
        resource: ApiResourceContract,
        controller: ControllerDefinition,
        auth: AuthRequirements
    ) -> list[RouteDefinition]:
        """Design routes for a resource."""
        routes = []

        for endpoint in resource.endpoints:
            method_name = self._endpoint_to_method_name(endpoint)
            
            # Build middleware chain
            middleware = []
            if endpoint.requires_auth:
                middleware.append('authenticate')
                if endpoint.permissions:
                    middleware.append(f"authorize({endpoint.permissions})")
            
            if endpoint.rate_limit:
                middleware.append(f"rateLimit({endpoint.rate_limit})")

            # Validation schema name
            validation = None
            if endpoint.request_body or endpoint.query_params:
                validation = f"{resource.name}{method_name.capitalize()}Schema"

            routes.append(RouteDefinition(
                method=endpoint.method,
                path=endpoint.path,
                handler=method_name,
                controller=controller.name,
                middleware=middleware,
                validation_schema=validation
            ))

        return routes

    def _design_validation_schemas(
        self,
        resource: ApiResourceContract,
        models: list[InferredModel]
    ) -> dict[str, dict]:
        """Design validation schemas for endpoints."""
        schemas = {}

        for endpoint in resource.endpoints:
            if not endpoint.request_body and not endpoint.query_params:
                continue

            method_name = self._endpoint_to_method_name(endpoint)
            schema_name = f"{resource.name}{method_name.capitalize()}Schema"

            schema = {'type': 'object', 'properties': {}, 'required': []}

            # Add body schema
            if endpoint.request_body and endpoint.request_body.schema:
                body_schema = endpoint.request_body.schema
                if 'properties' in body_schema:
                    schema['properties'].update(body_schema['properties'])
                if 'required' in body_schema:
                    schema['required'].extend(body_schema['required'])

            # Add query params
            for param in endpoint.query_params:
                schema['properties'][param.name] = {
                    'type': self._param_type_to_json(param.param_type)
                }
                if param.required:
                    schema['required'].append(param.name)

            schemas[schema_name] = schema

        return schemas

    def _design_auth_routes(
        self,
        auth: AuthRequirements
    ) -> tuple[ControllerDefinition, list[RouteDefinition]]:
        """Design authentication routes."""
        methods = [
            {
                'name': 'register',
                'http_method': 'POST',
                'path': '/register',
                'description': 'Register new user',
                'auth_required': False,
            },
            {
                'name': 'login',
                'http_method': 'POST',
                'path': '/login',
                'description': 'Login user',
                'auth_required': False,
            },
            {
                'name': 'logout',
                'http_method': 'POST',
                'path': '/logout',
                'description': 'Logout user',
                'auth_required': True,
            },
            {
                'name': 'me',
                'http_method': 'GET',
                'path': '/me',
                'description': 'Get current user',
                'auth_required': True,
            },
        ]

        # Add refresh token if JWT
        if auth.strategy.value in ('jwt', 'hybrid'):
            methods.append({
                'name': 'refresh',
                'http_method': 'POST',
                'path': '/refresh',
                'description': 'Refresh access token',
                'auth_required': False,
            })

        # Add OAuth routes
        for provider in auth.oauth_providers:
            methods.extend([
                {
                    'name': f'{provider.name}Auth',
                    'http_method': 'GET',
                    'path': f'/oauth/{provider.name}',
                    'description': f'Initiate {provider.name} OAuth',
                    'auth_required': False,
                },
                {
                    'name': f'{provider.name}Callback',
                    'http_method': 'GET',
                    'path': f'/oauth/{provider.name}/callback',
                    'description': f'{provider.name} OAuth callback',
                    'auth_required': False,
                },
            ])

        controller = ControllerDefinition(
            name='AuthController',
            resource='auth',
            base_path='/api/auth',
            methods=methods,
            middleware=[],
            dependencies=['AuthService', 'UserService']
        )

        routes = []
        for method in methods:
            middleware = ['authenticate'] if method['auth_required'] else []
            routes.append(RouteDefinition(
                method=method['http_method'],
                path=f"/api/auth{method['path']}",
                handler=method['name'],
                controller='AuthController',
                middleware=middleware,
                validation_schema=None
            ))

        return controller, routes

    def _endpoint_to_method_name(self, endpoint: ApiEndpointContract) -> str:
        """Convert endpoint to method name."""
        method = endpoint.method.lower()
        path_parts = endpoint.path.strip('/').split('/')
        
        # GET /users -> getAll, GET /users/:id -> getById
        # POST /users -> create, PUT /users/:id -> update
        # DELETE /users/:id -> delete
        
        has_id = any(p.startswith(':') for p in path_parts)
        
        if method == 'get':
            return 'getById' if has_id else 'getAll'
        elif method == 'post':
            return 'create'
        elif method == 'put' or method == 'patch':
            return 'update'
        elif method == 'delete':
            return 'delete'
        
        return f"{method}{'ById' if has_id else ''}"

    def _relative_path(self, full_path: str, base_path: str) -> str:
        """Get relative path from base."""
        if full_path.startswith(base_path):
            rel = full_path[len(base_path):]
            return rel if rel else '/'
        return full_path

    def _param_type_to_json(self, param_type: str) -> str:
        """Convert param type to JSON schema type."""
        mapping = {
            'string': 'string',
            'integer': 'integer',
            'number': 'number',
            'boolean': 'boolean',
        }
        return mapping.get(param_type, 'string')