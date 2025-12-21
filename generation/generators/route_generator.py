"""Route generator."""

import logging
from synthesis.api_architect import RouteDefinition, ControllerDefinition

logger = logging.getLogger(__name__)


class RouteGenerator:
    """Generate Express routes."""

    def generate(
        self,
        routes: list[RouteDefinition],
        controllers: list[ControllerDefinition]
    ) -> str:
        """Generate routes file."""
        # Build imports
        imports = ["import { Router } from 'express';"]
        
        # Import middleware
        imports.append("import { authenticate, authorize } from '../middleware/auth';")
        imports.append("import { validate } from '../middleware/validate';")
        
        # Import controllers
        controller_names = set()
        for route in routes:
            controller_names.add(route.controller)
        
        for name in sorted(controller_names):
            class_name = name
            file_name = name.replace('Controller', '').lower()
            imports.append(f"import {{ {class_name} }} from '../controllers/{file_name}.controller';")

        # Build route registration
        route_registrations = []
        
        # Group routes by controller
        routes_by_controller: dict[str, list[RouteDefinition]] = {}
        for route in routes:
            if route.controller not in routes_by_controller:
                routes_by_controller[route.controller] = []
            routes_by_controller[route.controller].append(route)

        for controller_name, ctrl_routes in routes_by_controller.items():
            route_registrations.append(f"\n  // {controller_name} routes")
            
            for route in ctrl_routes:
                middleware_chain = self._build_middleware_chain(route)
                method = route.method.lower()
                
                route_registrations.append(
                    f"  router.{method}('{route.path}', {middleware_chain}{controller_name.lower()}.{route.handler});"
                )

        # Build full file
        content = '\n'.join(imports)
        content += '\n\n'
        content += '''export function createRouter(
  // Inject controller instances
'''
        
        # Add controller parameters
        for name in sorted(controller_names):
            param_name = name[0].lower() + name[1:]
            content += f"  {param_name}: {name},\n"
        
        content += '): Router {\n'
        content += '  const router = Router();\n'
        content += '\n'.join(route_registrations)
        content += '\n\n  return router;\n'
        content += '}\n'

        return content

    def _build_middleware_chain(self, route: RouteDefinition) -> str:
        """Build middleware chain for a route."""
        if not route.middleware:
            return ''
        
        parts = []
        for mw in route.middleware:
            if mw == 'authenticate':
                parts.append('authenticate')
            elif mw.startswith('authorize('):
                parts.append(mw)
            elif mw.startswith('rateLimit('):
                parts.append(mw)
            elif mw == 'validation' and route.validation_schema:
                parts.append(f"validate({route.validation_schema})")
            else:
                parts.append(mw)
        
        if parts:
            return ', '.join(parts) + ', '
        return ''

    def generate_index(self, controllers: list[ControllerDefinition]) -> str:
        """Generate routes index file."""
        imports = [
            "import { Router } from 'express';",
            "import { PrismaClient } from '@prisma/client';",
            "",
            "// Import repositories",
        ]
        
        # Track unique models
        models = set()
        for ctrl in controllers:
            if ctrl.resource and ctrl.resource != 'auth':
                models.add(ctrl.resource.capitalize())
        
        for model in sorted(models):
            imports.append(f"import {{ {model}Repository }} from '../repositories/{model.lower()}.repository';")
        
        imports.append("")
        imports.append("// Import services")
        
        for model in sorted(models):
            imports.append(f"import {{ {model}Service }} from '../services/{model.lower()}.service';")
        
        imports.append("import { AuthService } from '../services/auth.service';")
        imports.append("")
        imports.append("// Import controllers")
        
        for ctrl in controllers:
            name = ctrl.name
            file_name = ctrl.name.replace('Controller', '').lower()
            imports.append(f"import {{ {name} }} from '../controllers/{file_name}.controller';")
        
        imports.append("")
        imports.append("import { createRouter } from './routes';")
        
        # Build setup function
        setup = '''
export function setupRoutes(prisma: PrismaClient): Router {
  // Create repositories
'''
        for model in sorted(models):
            setup += f"  const {model.lower()}Repository = new {model}Repository(prisma);\n"
        
        setup += "\n  // Create services\n"
        for model in sorted(models):
            setup += f"  const {model.lower()}Service = new {model}Service({model.lower()}Repository);\n"
        
        setup += "  const authService = new AuthService(userRepository);\n"
        
        setup += "\n  // Create controllers\n"
        for ctrl in controllers:
            name = ctrl.name
            param_name = name[0].lower() + name[1:]
            if 'Auth' in name:
                setup += f"  const {param_name} = new {name}(authService);\n"
            else:
                resource = ctrl.resource.lower() if ctrl.resource else 'unknown'
                setup += f"  const {param_name} = new {name}({resource}Service);\n"
        
        setup += "\n  // Create router\n"
        setup += "  return createRouter(\n"
        for ctrl in controllers:
            param_name = ctrl.name[0].lower() + ctrl.name[1:]
            setup += f"    {param_name},\n"
        setup += "  );\n"
        setup += "}\n"
        
        return '\n'.join(imports) + '\n' + setup