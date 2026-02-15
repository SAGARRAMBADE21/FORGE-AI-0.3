"""
TypeScript AST Analyzer - Python wrapper for ts-morph based analysis.

Provides high-accuracy TypeScript type extraction using the TypeScript
Compiler API via ts-morph (Node.js).
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class TypeScriptASTAnalyzer:
    """
    Analyze TypeScript code using AST for accurate type extraction.
    
    Leverages Node.js + ts-morph for parsing TypeScript with full
    semantic analysis. Falls back to regex if Node.js unavailable.
    """
    
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.ts_analyzer_script = Path(__file__).parent / "ts_analyzer.js"
        self._node_available = self._check_node_availability()
    
    def _check_node_availability(self) -> bool:
        """Check if Node.js is available."""
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"Node.js available: {result.stdout.strip()}")
                return True
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        
        logger.warning("Node.js not available - AST analysis will be skipped")
        return False
    
    def _ensure_dependencies(self) -> bool:
        """Ensure ts-morph is installed."""
        if not self._node_available:
            return False
        
        package_json = self.ts_analyzer_script.parent / "package.json"
        node_modules = self.ts_analyzer_script.parent / "node_modules"
        
        # Check if dependencies are installed
        if node_modules.exists() and (node_modules / "ts-morph").exists():
            return True
        
        # Install dependencies
        logger.info("Installing TypeScript analyzer dependencies...")
        try:
            result = subprocess.run(
                ["npm", "install"],
                cwd=str(self.ts_analyzer_script.parent),
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                logger.info("Dependencies installed successfully")
                return True
            else:
                logger.debug(f"Failed to install dependencies: {result.stderr}")
                return False
        except Exception as e:
            logger.debug(f"Could not install dependencies: {e}")
            return False
    
    def extract_domain_models(self) -> List[Dict]:
        """
        Extract domain models from TypeScript files using AST.
        
        Returns list of type definitions:
        [
            {
                "name": "User",
                "kind": "interface" | "class" | "type",
                "filePath": "/src/models/User.ts",
                "properties": [{"name": "id", "type": "string"}, ...],
                "isExported": true,
                "hasDecorators": false
            }
        ]
        
        Returns empty list if Node.js/ts-morph unavailable.
        """
        if not self._node_available:
            logger.debug("AST analysis skipped - Node.js not available")
            return []
        
        if not self._ensure_dependencies():
            logger.debug("AST analysis skipped - dependencies unavailable")
            return []
        
        try:
            # Run TypeScript analyzer
            logger.info(f"Running TypeScript AST analysis on {self.project_root}")
            
            result = subprocess.run(
                ["node", str(self.ts_analyzer_script), str(self.project_root)],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.warning(f"TypeScript analysis failed: {result.stderr}")
                return []
            
            # Parse JSON output
            types = json.loads(result.stdout)
            logger.info(f"AST analysis found {len(types)} types")
            
            # Filter to domain models only
            domain_models = [t for t in types if self._is_domain_model(t)]
            logger.info(f"Filtered to {len(domain_models)} domain models")
            
            return domain_models
            
        except subprocess.TimeoutExpired:
            logger.warning("TypeScript analysis timed out")
            return []
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse TypeScript analysis output: {e}")
            return []
        except Exception as e:
            logger.warning(f"TypeScript analysis error: {e}")
            return []
    
    def _is_domain_model(self, type_info: Dict) -> bool:
        """
        Determine if extracted type is a domain model.
        
        Uses multiple heuristics:
        1. File location (models/, entities/, domain/)
        2. Naming conventions (no Dto, Props, State suffixes)
        3. Type kind (classes more likely domain entities)
        4. Export status (domain models usually exported)
        """
        # Use centralized filter
        from utils.domain_model_filter import is_domain_model
        
        # 1. Basic name filter
        if not is_domain_model(type_info["name"], type_info["filePath"]):
            return False
        
        # 2. Must be exported (domain models are shared)
        if not type_info.get("isExported", False):
            return False
        
        # 3. Prefer types in domain folders
        file_path_lower = type_info["filePath"].lower()
        
        # Strong indicators of domain models
        domain_indicators = ["/models/", "/entities/", "/domain/", "/types/models"]
        if any(indicator in file_path_lower for indicator in domain_indicators):
            return True
        
        # Exclude UI paths
        ui_indicators = ["/components/", "/pages/", "/views/", "/hooks/", "/ui/"]
        if any(indicator in file_path_lower for indicator in ui_indicators):
            return False
        
        # 4. Class types are more likely domain entities
        if type_info["kind"] == "class":
            # Classes with decorators likely domain entities (e.g., TypeORM)
            if type_info.get("hasDecorators", False):
                return True
            # Classes in /src/ but not in UI folders
            if "/src/" in file_path_lower and not any(ui in file_path_lower for ui in ui_indicators):
                return True
        
        # 5. Check properties
        properties = type_info.get("properties", [])
        if properties:
            # Has "id" field - strong indicator of domain entity
            if any(p.get("name") == "id" for p in properties):
                return True
            
            # Multiple properties suggest complex domain object
            if len(properties) > 3:
                return True
        
        # Default: exclude if unclear
        return False
