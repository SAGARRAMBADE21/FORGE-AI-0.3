/**
 * TypeScript AST Analyzer using ts-morph
 * 
 * Parses TypeScript code and extracts type definitions with full semantic analysis.
 * 
 * Usage: node ts_analyzer.js <project_root>
 * Output: JSON array of type definitions
 * 
 * Example output:
 * [
 *   {
 *     "name": "User",
 *     "kind": "interface",
 *     "filePath": "/src/models/User.ts",
 *     "properties": [
 *       {"name": "id", "type": "string"},
 *       {"name": "email", "type": "string"}
 *     ],
 *     "isExported": true,
 *     "hasDecorators": false
 *   }
 * ]
 */

const { Project } = require("ts-morph");
const path = require("path");
const fs = require("fs");

// Get project root from command line
const projectRoot = process.argv[2];

if (!projectRoot) {
    console.error("Usage: node ts_analyzer.js <project_root>");
    process.exit(1);
}

// Check if project exists
if (!fs.existsSync(projectRoot)) {
    console.error(`Error: Project root does not exist: ${projectRoot}`);
    process.exit(1);
}

// Initialize ts-morph project
let project;
try {
    const tsConfigPath = path.join(projectRoot, "tsconfig.json");

    if (fs.existsSync(tsConfigPath)) {
        // Use existing tsconfig.json
        project = new Project({
            tsConfigFilePath: tsConfigPath,
            skipAddingFilesFromTsConfig: true,
        });
    } else {
        // No tsconfig - use default compiler options
        project = new Project({
            compilerOptions: {
                target: "ES2020",
                module: "ESNext",
                jsx: "react",
                strict: false,
            },
        });
    }
} catch (error) {
    console.error(`Error initializing project: ${error.message}`);
    process.exit(1);
}

// Add all TypeScript/React files
try {
    const sourcePattern = path.join(projectRoot, "src/**/*.{ts,tsx}");
    project.addSourceFilesAtPaths(sourcePattern);
} catch (error) {
    // Fallback: try to add files from common locations
    const commonPaths = [
        path.join(projectRoot, "**/*.ts"),
        path.join(projectRoot, "**/*.tsx"),
    ];

    for (const pattern of commonPaths) {
        try {
            project.addSourceFilesAtPaths(pattern);
        } catch (e) {
            // Continue if pattern fails
        }
    }
}

const types = [];

// Extract type information from all source files
for (const sourceFile of project.getSourceFiles()) {
    const filePath = sourceFile.getFilePath();

    // Skip node_modules and common build directories
    if (filePath.includes("node_modules") ||
        filePath.includes("dist") ||
        filePath.includes("build") ||
        filePath.includes(".next")) {
        continue;
    }

    const relativePath = filePath.replace(projectRoot, "");

    // Extract interfaces
    for (const iface of sourceFile.getInterfaces()) {
        const properties = [];

        for (const prop of iface.getProperties()) {
            try {
                properties.push({
                    name: prop.getName(),
                    type: prop.getType().getText(),
                    optional: prop.hasQuestionToken(),
                });
            } catch (error) {
                // Skip properties that can't be analyzed
                properties.push({
                    name: prop.getName(),
                    type: "unknown",
                    optional: false,
                });
            }
        }

        types.push({
            name: iface.getName(),
            kind: "interface",
            filePath: relativePath,
            properties: properties,
            isExported: iface.isExported(),
            hasDecorators: iface.getDecorators().length > 0,
            extends: iface.getExtends().map(e => e.getText()),
        });
    }

    // Extract classes
    for (const cls of sourceFile.getClasses()) {
        const className = cls.getName();
        if (!className) continue; // Skip anonymous classes

        const properties = [];

        for (const prop of cls.getProperties()) {
            try {
                properties.push({
                    name: prop.getName(),
                    type: prop.getType().getText(),
                    optional: prop.hasQuestionToken(),
                });
            } catch (error) {
                properties.push({
                    name: prop.getName(),
                    type: "unknown",
                    optional: false,
                });
            }
        }

        types.push({
            name: className,
            kind: "class",
            filePath: relativePath,
            properties: properties,
            isExported: cls.isExported(),
            hasDecorators: cls.getDecorators().length > 0,
            extends: cls.getExtends() ? [cls.getExtends().getText()] : [],
        });
    }

    // Extract type aliases (only object types)
    for (const typeAlias of sourceFile.getTypeAliases()) {
        const typeNode = typeAlias.getTypeNode();

        // Only include type aliases that are object types
        if (typeNode && typeNode.getKind() === 183) { // TypeLiteral kind
            const properties = [];

            // Try to extract properties from type literal
            try {
                const type = typeAlias.getType();
                const props = type.getProperties();

                for (const prop of props) {
                    properties.push({
                        name: prop.getName(),
                        type: prop.getTypeAtLocation(typeAlias).getText(),
                        optional: false,
                    });
                }
            } catch (error) {
                // Can't extract properties
            }

            types.push({
                name: typeAlias.getName(),
                kind: "type",
                filePath: relativePath,
                properties: properties,
                isExported: typeAlias.isExported(),
                hasDecorators: false,
                extends: [],
            });
        }
    }
}

// Output JSON
console.log(JSON.stringify(types, null, 2));
