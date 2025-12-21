"""Design service layer architecture."""

import logging
from dataclasses import dataclass

from core.types import (
    InferredModel, InferredRelation, ApiResourceContract,
    RepositoryDefinition, RepositoryMethod, ServiceDefinition,
    ServiceMethod
)

logger = logging.getLogger(__name__)


@dataclass
class DomainEventDefinition:
    """Domain event definition."""
    name: str
    payload_fields: list[str]
    triggered_by: list[str]


@dataclass 
class ServiceArchitecture:
    """Complete service architecture."""
    repositories: list[RepositoryDefinition]
    services: list[ServiceDefinition]
    events: list[DomainEventDefinition]


class ServiceArchitect:
    """
    Design service layer architecture.
    
    Responsibilities:
    - Create repository layer
    - Design service methods
    - Identify transaction boundaries
    - Plan domain events
    """

    def __init__(self):
        pass

    async def design_architecture(
        self,
        models: list[InferredModel],
        relations: list[InferredRelation],
        resources: list[ApiResourceContract]
    ) -> ServiceArchitecture:
        """Design complete service architecture."""
        repositories = []
        services = []
        events = []

        # Create repositories for each model
        for model in models:
            repo = self._design_repository(model, relations)
            repositories.append(repo)

        # Create services for each resource
        for resource in resources:
            model = self._find_model(resource.model, models)
            service = self._design_service(resource, model, relations)
            services.append(service)

            # Design events
            resource_events = self._design_events(resource, model)
            events.extend(resource_events)

        # Add common services
        services.extend(self._create_common_services())

        logger.info(f"Designed {len(repositories)} repositories, {len(services)} services")

        return ServiceArchitecture(
            repositories=repositories,
            services=services,
            events=events
        )

    def _design_repository(
        self,
        model: InferredModel,
        relations: list[InferredRelation]
    ) -> RepositoryDefinition:
        """Design repository for a model."""
        methods = [
            # Standard CRUD
            RepositoryMethod(
                name='findById',
                return_type=f'{model.name} | null',
                parameters=[{'name': 'id', 'type': 'string'}],
                query_type='select'
            ),
            RepositoryMethod(
                name='findMany',
                return_type=f'{model.name}[]',
                parameters=[
                    {'name': 'where', 'type': f'Partial<{model.name}>', 'optional': True},
                    {'name': 'options', 'type': 'FindOptions', 'optional': True}
                ],
                query_type='select'
            ),
            RepositoryMethod(
                name='create',
                return_type=model.name,
                parameters=[{'name': 'data', 'type': f'Create{model.name}Input'}],
                query_type='insert'
            ),
            RepositoryMethod(
                name='update',
                return_type=model.name,
                parameters=[
                    {'name': 'id', 'type': 'string'},
                    {'name': 'data', 'type': f'Update{model.name}Input'}
                ],
                query_type='update'
            ),
            RepositoryMethod(
                name='delete',
                return_type='void',
                parameters=[{'name': 'id', 'type': 'string'}],
                query_type='delete'
            ),
            RepositoryMethod(
                name='count',
                return_type='number',
                parameters=[{'name': 'where', 'type': f'Partial<{model.name}>', 'optional': True}],
                query_type='select'
            ),
        ]

        # Add relation-specific methods
        for rel in relations:
            if rel.source_model == model.name:
                if rel.relation_type.value == 'one_to_many':
                    methods.append(RepositoryMethod(
                        name=f'findWith{rel.target_model}s',
                        return_type=f'{model.name} & {{ {rel.source_field}: {rel.target_model}[] }}',
                        parameters=[{'name': 'id', 'type': 'string'}],
                        query_type='select'
                    ))

        # Add unique field finders
        for field in model.fields:
            if field.unique and field.name != 'id':
                methods.append(RepositoryMethod(
                    name=f'findBy{field.name.capitalize()}',
                    return_type=f'{model.name} | null',
                    parameters=[{'name': field.name, 'type': self._field_to_ts_type(field)}],
                    query_type='select'
                ))

        return RepositoryDefinition(
            name=f'{model.name}Repository',
            model=model.name,
            methods=methods
        )

    def _design_service(
        self,
        resource: ApiResourceContract,
        model: InferredModel | None,
        relations: list[InferredRelation]
    ) -> ServiceDefinition:
        """Design service for a resource."""
        methods = []
        dependencies = []

        if model:
            dependencies.append(f'{model.name}Repository')

        for endpoint in resource.endpoints:
            method = self._endpoint_to_service_method(endpoint, model, relations)
            methods.append(method)

            # Add related repo dependencies
            for rel in relations:
                if model and rel.source_model == model.name:
                    dep = f'{rel.target_model}Repository'
                    if dep not in dependencies:
                        dependencies.append(dep)

        return ServiceDefinition(
            name=f'{resource.name.capitalize()}Service',
            dependencies=dependencies,
            methods=methods
        )

    def _endpoint_to_service_method(
        self,
        endpoint,
        model: InferredModel | None,
        relations: list[InferredRelation]
    ) -> ServiceMethod:
        """Convert endpoint to service method."""
        method_name = self._get_method_name(endpoint)
        
        # Determine parameters
        params = []
        for p in endpoint.path_params:
            params.append({'name': p.name, 'type': 'string'})
        
        if endpoint.request_body:
            params.append({'name': 'data', 'type': f'{method_name.capitalize()}Input'})

        # Determine return type
        if model:
            if endpoint.method == 'GET':
                if any(p.name == 'id' for p in endpoint.path_params):
                    return_type = model.name
                else:
                    return_type = f'{model.name}[]'
            elif endpoint.method == 'POST':
                return_type = model.name
            elif endpoint.method in ('PUT', 'PATCH'):
                return_type = model.name
            elif endpoint.method == 'DELETE':
                return_type = 'void'
            else:
                return_type = 'any'
        else:
            return_type = 'any'

        # Determine if transaction needed
        transaction = endpoint.method in ('POST', 'PUT', 'PATCH', 'DELETE')

        # Determine repository calls
        repo_calls = []
        if model:
            if endpoint.method == 'GET':
                repo_calls.append('findById' if 'id' in [p.name for p in endpoint.path_params] else 'findMany')
            elif endpoint.method == 'POST':
                repo_calls.append('create')
            elif endpoint.method in ('PUT', 'PATCH'):
                repo_calls.append('update')
            elif endpoint.method == 'DELETE':
                repo_calls.append('delete')

        return ServiceMethod(
            name=method_name,
            return_type=return_type,
            parameters=params,
            repository_calls=repo_calls,
            transaction_boundary=transaction
        )

    def _design_events(
        self,
        resource: ApiResourceContract,
        model: InferredModel | None
    ) -> list[DomainEventDefinition]:
        """Design domain events for resource."""
        events = []
        
        if not model:
            return events

        name = model.name

        # Create events for mutations
        for endpoint in resource.endpoints:
            if endpoint.method == 'POST':
                events.append(DomainEventDefinition(
                    name=f'{name}Created',
                    payload_fields=['id', *[f.name for f in model.fields[:5]]],
                    triggered_by=[f'{resource.name}Service.create']
                ))
            elif endpoint.method in ('PUT', 'PATCH'):
                events.append(DomainEventDefinition(
                    name=f'{name}Updated',
                    payload_fields=['id', 'changes'],
                    triggered_by=[f'{resource.name}Service.update']
                ))
            elif endpoint.method == 'DELETE':
                events.append(DomainEventDefinition(
                    name=f'{name}Deleted',
                    payload_fields=['id'],
                    triggered_by=[f'{resource.name}Service.delete']
                ))

        return events

    def _create_common_services(self) -> list[ServiceDefinition]:
        """Create common utility services."""
        return [
            ServiceDefinition(
                name='EmailService',
                dependencies=[],
                methods=[
                    ServiceMethod(
                        name='send',
                        return_type='void',
                        parameters=[
                            {'name': 'to', 'type': 'string'},
                            {'name': 'subject', 'type': 'string'},
                            {'name': 'body', 'type': 'string'}
                        ]
                    ),
                    ServiceMethod(
                        name='sendTemplate',
                        return_type='void',
                        parameters=[
                            {'name': 'to', 'type': 'string'},
                            {'name': 'template', 'type': 'string'},
                            {'name': 'data', 'type': 'Record<string, any>'}
                        ]
                    ),
                ]
            ),
            ServiceDefinition(
                name='CacheService',
                dependencies=[],
                methods=[
                    ServiceMethod(name='get', return_type='T | null', parameters=[{'name': 'key', 'type': 'string'}]),
                    ServiceMethod(name='set', return_type='void', parameters=[
                        {'name': 'key', 'type': 'string'},
                        {'name': 'value', 'type': 'T'},
                        {'name': 'ttl', 'type': 'number', 'optional': True}
                    ]),
                    ServiceMethod(name='delete', return_type='void', parameters=[{'name': 'key', 'type': 'string'}]),
                ]
            ),
        ]

    def _get_method_name(self, endpoint) -> str:
        """Get service method name from endpoint."""
        method = endpoint.method.lower()
        has_id = any(p.name == 'id' or p.name.endswith('Id') for p in endpoint.path_params)
        
        if method == 'get':
            return 'getById' if has_id else 'getAll'
        elif method == 'post':
            return 'create'
        elif method in ('put', 'patch'):
            return 'update'
        elif method == 'delete':
            return 'delete'
        return method

    def _find_model(self, name: str | None, models: list[InferredModel]) -> InferredModel | None:
        """Find model by name."""
        if not name:
            return None
        for model in models:
            if model.name.lower() == name.lower():
                return model
        return None

    def _field_to_ts_type(self, field) -> str:
        """Convert field to TypeScript type."""
        mapping = {
            'string': 'string',
            'text': 'string',
            'integer': 'number',
            'float': 'number',
            'boolean': 'boolean',
            'datetime': 'Date',
            'date': 'Date',
            'json': 'Record<string, any>',
            'uuid': 'string',
        }
        type_val = field.field_type.value if hasattr(field.field_type, 'value') else str(field.field_type)
        return mapping.get(type_val, 'any')