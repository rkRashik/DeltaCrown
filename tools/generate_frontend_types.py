#!/usr/bin/env python3
"""
Frontend TypeScript Types Generator

Generates TypeScript type definitions from OpenAPI 3.0 schema for the DeltaCrown SDK.

Usage:
    python tools/generate_frontend_types.py

Output:
    frontend_sdk/src/types.generated.ts - Auto-generated types from OpenAPI schema

Requirements:
    - OpenAPI schema must be generated first: python manage.py spectacular --file schema.yml
    - PyYAML for reading schema.yml

Epic: Phase 9, Epic 9.2 - JSON Schemas & TypeScript Types
"""

import yaml
import json
from pathlib import Path
from typing import Dict, Any, List, Set
from datetime import datetime


class TypeScriptGenerator:
    """Convert OpenAPI 3.0 schema components to TypeScript interfaces."""
    
    def __init__(self, schema_path: Path, output_path: Path):
        self.schema_path = schema_path
        self.output_path = output_path
        self.schema = self._load_schema()
        self.components = self.schema.get("components", {}).get("schemas", {})
        self.generated_types: Set[str] = set()
        
    def _load_schema(self) -> Dict[str, Any]:
        """Load OpenAPI schema from YAML file."""
        with open(self.schema_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    
    def _openapi_type_to_ts(self, prop: Dict[str, Any], required: bool = False) -> str:
        """Convert OpenAPI property type to TypeScript type."""
        prop_type = prop.get("type", "any")
        prop_format = prop.get("format")
        nullable = prop.get("nullable", False) or prop.get("x-nullable", False)
        
        # Handle $ref
        if "$ref" in prop:
            ref_type = prop["$ref"].split("/")[-1]
            ts_type = ref_type
        # Handle arrays
        elif prop_type == "array":
            items = prop.get("items", {})
            item_type = self._openapi_type_to_ts(items, required=False)
            ts_type = f"Array<{item_type}>"
        # Handle enums
        elif "enum" in prop:
            enum_values = prop["enum"]
            ts_type = " | ".join([f'"{v}"' for v in enum_values])
        # Handle oneOf/anyOf
        elif "oneOf" in prop:
            types = [self._openapi_type_to_ts(t, required=False) for t in prop["oneOf"]]
            ts_type = " | ".join(types)
        elif "anyOf" in prop:
            types = [self._openapi_type_to_ts(t, required=False) for t in prop["anyOf"]]
            ts_type = " | ".join(types)
        # Basic types
        else:
            type_map = {
                "string": "string",
                "integer": "number",
                "number": "number",
                "boolean": "boolean",
                "object": "Record<string, any>",
                "null": "null",
            }
            
            # Handle date formats
            if prop_format in ["date", "date-time"]:
                ts_type = "string"  # ISO 8601 string
            else:
                ts_type = type_map.get(prop_type, "any")
        
        # Add null union if nullable
        if nullable and ts_type != "null":
            ts_type = f"{ts_type} | null"
        
        # Add undefined for optional fields
        if not required:
            ts_type = f"{ts_type} | undefined"
            
        return ts_type
    
    def _generate_interface(self, name: str, schema: Dict[str, Any]) -> str:
        """Generate TypeScript interface from OpenAPI schema object."""
        if name in self.generated_types:
            return ""
        
        self.generated_types.add(name)
        
        description = schema.get("description", "")
        properties = schema.get("properties", {})
        required_fields = set(schema.get("required", []))
        
        # Start interface
        lines = []
        if description:
            lines.append("/**")
            lines.append(f" * {description}")
            lines.append(" */")
        
        lines.append(f"export interface {name} {{")
        
        # Add properties
        for prop_name, prop_schema in properties.items():
            prop_desc = prop_schema.get("description", "")
            is_required = prop_name in required_fields
            prop_type = self._openapi_type_to_ts(prop_schema, required=is_required)
            
            if prop_desc:
                lines.append(f"  /** {prop_desc} */")
            
            optional_marker = "" if is_required else "?"
            lines.append(f"  {prop_name}{optional_marker}: {prop_type};")
        
        lines.append("}")
        lines.append("")
        
        return "\n".join(lines)
    
    def _generate_enum(self, name: str, schema: Dict[str, Any]) -> str:
        """Generate TypeScript enum or type alias from OpenAPI enum."""
        if name in self.generated_types:
            return ""
        
        self.generated_types.add(name)
        
        description = schema.get("description", "")
        enum_values = schema.get("enum", [])
        
        lines = []
        if description:
            lines.append("/**")
            lines.append(f" * {description}")
            lines.append(" */")
        
        # Use type alias instead of enum for string unions
        type_values = " | ".join([f'"{v}"' for v in enum_values])
        lines.append(f"export type {name} = {type_values};")
        lines.append("")
        
        return "\n".join(lines)
    
    def generate(self):
        """Generate complete TypeScript types file."""
        lines = [
            "/**",
            " * Auto-Generated TypeScript Types for DeltaCrown API",
            " *",
            f" * Generated: {datetime.now().isoformat()}",
            " * Source: schema.yml (OpenAPI 3.0)",
            " * Generator: tools/generate_frontend_types.py",
            " *",
            " * DO NOT EDIT MANUALLY - Regenerate with: pnpm run generate",
            " *",
            " * Epic: Phase 9, Epic 9.2 - JSON Schemas & TypeScript Types",
            " */",
            "",
            "/* eslint-disable */",
            "/* tslint:disable */",
            "",
        ]
        
        # Generate enums first
        for name, schema in self.components.items():
            if "enum" in schema:
                lines.append(self._generate_enum(name, schema))
        
        # Generate interfaces
        for name, schema in self.components.items():
            if schema.get("type") == "object" or "properties" in schema:
                lines.append(self._generate_interface(name, schema))
        
        # Write to file
        output = "\n".join(lines)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_path, "w", encoding="utf-8") as f:
            f.write(output)
        
        print(f"✅ Generated {len(self.generated_types)} types")
        print(f"📄 Output: {self.output_path}")


def main():
    """Main generator entry point."""
    # Paths
    repo_root = Path(__file__).parent.parent
    schema_path = repo_root / "schema.yml"
    output_path = repo_root / "frontend_sdk" / "src" / "types.generated.ts"
    
    # Check schema exists
    if not schema_path.exists():
        print("❌ schema.yml not found!")
        print("   Run: python manage.py spectacular --file schema.yml")
        return 1
    
    # Generate types
    print("🔄 Generating TypeScript types from OpenAPI schema...")
    generator = TypeScriptGenerator(schema_path, output_path)
    generator.generate()
    
    print("✅ Type generation complete!")
    return 0


if __name__ == "__main__":
    exit(main())
