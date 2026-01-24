"""Extract and synthesize API contracts from frontend evidence."""

import logging
import re
from collections import defaultdict

from core.types import (
    APICall,
    ApiEndpointContract,
    ApiResourceContract,
    Evidence,
    EvidenceSource,
    InferredModel,
    PathParam,
    QueryParam,
    RequestBodySchema,
    ResponseSchema,
)
from core.utils import generate_id

logger = logging.getLogger(__name__)


class ApiContractExtractor:
    """
    Extract and synthesize API contracts from frontend API calls.

    Process:
    1. Group API calls by endpoint pattern
    2. Synthesize contracts with params, bodies, responses
    3. Infer auth requirements per endpoint
    4. Group into resources
    """

    def __init__(self):
        pass

    async def extract_contracts(
        self, api_calls: list[APICall], models: list[InferredModel]
    ) -> list[ApiResourceContract]:
        """Extract API contracts from frontend API calls."""
        # Group by endpoint pattern
        endpoint_groups = self._group_by_pattern(api_calls)

        # Create resources
        resources = []
        resource_map: dict[str, ApiResourceContract] = {}

        for pattern, calls in endpoint_groups.items():
            # Determine resource name
            resource_name = self._extract_resource_name(pattern)
            base_path = self._extract_base_path(pattern)

            # Get or create resource
            if resource_name not in resource_map:
                resource_map[resource_name] = ApiResourceContract(
                    name=resource_name,
                    base_path=base_path,
                    model=self._find_matching_model(resource_name, models),
                )

            # Create endpoint contract
            endpoint = self._synthesize_endpoint(pattern, calls, models)
            resource_map[resource_name].endpoints.append(endpoint)

        resources = list(resource_map.values())

        # Infer middleware for resources
        for resource in resources:
            resource.middleware = self._infer_middleware(resource)

        logger.info(
            f"Extracted {len(resources)} API resources with {sum(len(r.endpoints) for r in resources)} endpoints"
        )
        return resources

    def _group_by_pattern(self, api_calls: list[APICall]) -> dict[str, list[APICall]]:
        """Group API calls by normalized endpoint pattern."""
        groups: dict[str, list[APICall]] = defaultdict(list)

        for call in api_calls:
            pattern = self._normalize_pattern(call.endpoint, call.method.value)
            groups[pattern].append(call)

        return groups

    def _normalize_pattern(self, endpoint: str, method: str) -> str:
        """Normalize endpoint to pattern."""
        # Replace :id, {id}, [id] with :param
        normalized = re.sub(r"[:\[{](\w+)[}\]]?", r":\1", endpoint)
        # Replace UUIDs with :id
        normalized = re.sub(r"/[a-f0-9-]{36}", "/:id", normalized)
        # Replace numeric IDs with :id
        normalized = re.sub(r"/\d+", "/:id", normalized)
        return f"{method}:{normalized}"

    def _extract_resource_name(self, pattern: str) -> str:
        """Extract resource name from pattern."""
        # GET:/api/users/:id -> users
        parts = pattern.split(":")[-1].strip("/").split("/")

        for part in parts:
            if part.startswith(":"):
                continue
            if part in ("api", "v1", "v2", "v3"):
                continue
            # Return pluralized name
            return part

        return "resource"

    def _extract_base_path(self, pattern: str) -> str:
        """Extract base path from pattern."""
        endpoint = pattern.split(":")[-1]
        parts = endpoint.strip("/").split("/")

        base_parts = []
        for part in parts:
            if part.startswith(":"):
                break
            base_parts.append(part)

        return "/" + "/".join(base_parts)

    def _find_matching_model(
        self, resource_name: str, models: list[InferredModel]
    ) -> str | None:
        """Find model matching resource name."""
        # users -> User
        singular = resource_name.rstrip("s")
        model_name = singular[0].upper() + singular[1:]

        for model in models:
            if model.name.lower() == model_name.lower():
                return model.name

        return None

    def _synthesize_endpoint(
        self, pattern: str, calls: list[APICall], models: list[InferredModel]
    ) -> ApiEndpointContract:
        """Synthesize endpoint contract from API calls."""
        method, path = pattern.split(":", 1)

        # Extract path params
        path_params = []
        for match in re.finditer(r":(\w+)", path):
            param_name = match.group(1)
            path_params.append(
                PathParam(
                    name=param_name,
                    param_type=self._infer_param_type(param_name),
                    required=True,
                )
            )

        # Collect query params from all calls
        query_params = []
        seen_params = set()
        for call in calls:
            for param in call.query_params:
                if param not in seen_params:
                    seen_params.add(param)
                    query_params.append(
                        QueryParam(name=param, param_type="string", required=False)
                    )

        # Determine if body is needed
        request_body = None
        if method in ("POST", "PUT", "PATCH"):
            request_body = self._infer_request_body(calls, models)

        # Infer responses
        responses = self._infer_responses(method, calls, models)

        # Determine auth requirement
        requires_auth = any(c.requires_auth for c in calls)

        # Build evidence
        evidence = [
            Evidence(
                source=EvidenceSource.API_RESPONSE,
                file=c.file,
                line=c.line,
                content=c.source,
                confidence=0.8,
            )
            for c in calls
        ]

        return ApiEndpointContract(
            id=generate_id(),
            method=method,
            path=path,
            path_params=path_params,
            query_params=query_params,
            request_body=request_body,
            responses=responses,
            requires_auth=requires_auth,
            tags=[self._extract_resource_name(pattern)],
            description=self._generate_description(method, path),
            evidence=evidence,
        )

    def _infer_param_type(self, param_name: str) -> str:
        """Infer parameter type from name."""
        if param_name == "id" or param_name.endswith("Id"):
            return "string"
        if "page" in param_name.lower() or "limit" in param_name.lower():
            return "integer"
        return "string"

    def _infer_request_body(
        self, calls: list[APICall], models: list[InferredModel]
    ) -> RequestBodySchema | None:
        """Infer request body schema."""
        # Try to find body type from calls
        for call in calls:
            if call.body_type:
                # Find matching model
                for model in models:
                    if model.name == call.body_type:
                        return RequestBodySchema(
                            schema=self._model_to_schema(
                                model, exclude=["id", "createdAt", "updatedAt"]
                            )
                        )

        # Default schema based on resource
        return RequestBodySchema(schema={"type": "object"})

    def _infer_responses(
        self, method: str, calls: list[APICall], models: list[InferredModel]
    ) -> list[ResponseSchema]:
        """Infer response schemas."""
        responses = []

        # Success response
        if method == "GET":
            # Could be single item or list
            if any(":id" in c.endpoint for c in calls):
                responses.append(ResponseSchema(status_code=200, description="Success"))
            else:
                responses.append(
                    ResponseSchema(status_code=200, description="List of items")
                )
        elif method == "POST":
            responses.append(ResponseSchema(status_code=201, description="Created"))
        elif method == "PUT" or method == "PATCH":
            responses.append(ResponseSchema(status_code=200, description="Updated"))
        elif method == "DELETE":
            responses.append(ResponseSchema(status_code=204, description="Deleted"))

        # Common error responses
        responses.append(ResponseSchema(status_code=400, description="Bad Request"))
        responses.append(ResponseSchema(status_code=404, description="Not Found"))

        return responses

    def _model_to_schema(self, model: InferredModel, exclude: list[str] = None) -> dict:
        """Convert model to JSON schema."""
        exclude = exclude or []

        properties = {}
        required = []

        for field in model.fields:
            if field.name in exclude:
                continue

            prop = {"type": self._field_type_to_json(field.field_type)}

            if field.constraints:
                if "min_length" in field.constraints:
                    prop["minLength"] = field.constraints["min_length"]
                if "max_length" in field.constraints:
                    prop["maxLength"] = field.constraints["max_length"]
                if "pattern" in field.constraints:
                    prop["pattern"] = field.constraints["pattern"]

            properties[field.name] = prop

            if not field.nullable:
                required.append(field.name)

        return {"type": "object", "properties": properties, "required": required}

    def _field_type_to_json(self, field_type) -> str:
        """Convert field type to JSON schema type."""
        mapping = {
            "string": "string",
            "text": "string",
            "integer": "integer",
            "float": "number",
            "decimal": "number",
            "boolean": "boolean",
            "datetime": "string",
            "date": "string",
            "json": "object",
            "uuid": "string",
        }
        return mapping.get(
            field_type.value if hasattr(field_type, "value") else str(field_type),
            "string",
        )

    def _generate_description(self, method: str, path: str) -> str:
        """Generate endpoint description."""
        resource = self._extract_resource_name(f"{method}:{path}")
        singular = resource.rstrip("s")

        descriptions = {
            "GET": f"Get {resource}" if ":id" not in path else f"Get {singular} by ID",
            "POST": f"Create {singular}",
            "PUT": f"Update {singular}",
            "PATCH": f"Partially update {singular}",
            "DELETE": f"Delete {singular}",
        }

        return descriptions.get(method, f"{method} {path}")

    def _infer_middleware(self, resource: ApiResourceContract) -> list[str]:
        """Infer middleware for resource."""
        middleware = []

        # Auth middleware if any endpoint requires auth
        if any(e.requires_auth for e in resource.endpoints):
            middleware.append("auth")

        # Validation middleware
        middleware.append("validation")

        return middleware
