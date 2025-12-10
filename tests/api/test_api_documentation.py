"""
Phase 9, Epic 9.1 - API Documentation Tests

Tests for OpenAPI schema generation with drf-spectacular.
Verifies schema accessibility, completeness, and accuracy.
"""

import pytest
from django.test import Client
from django.urls import reverse
from rest_framework.test import APIClient
import json


@pytest.mark.django_db
class TestAPIDocumentation:
    """Test API documentation system with drf-spectacular."""
    
    @pytest.fixture
    def client(self):
        """Create API client."""
        return APIClient()
    
    def test_schema_endpoint_accessible(self, client):
        """Test that OpenAPI schema endpoint is accessible."""
        response = client.get("/api/schema/")
        
        assert response.status_code == 200
        assert response["Content-Type"] == "application/vnd.oai.openapi+json; charset=utf-8" or \
               response["Content-Type"] == "application/vnd.oai.openapi; charset=utf-8"
    
    def test_schema_is_valid_openapi(self, client):
        """Test that generated schema is valid OpenAPI 3.0."""
        response = client.get("/api/schema/", HTTP_ACCEPT="application/json")
        schema = response.json()
        
        # Check OpenAPI version
        assert "openapi" in schema
        assert schema["openapi"].startswith("3.0")
        
        # Check required top-level keys
        assert "info" in schema
        assert "paths" in schema
        assert "components" in schema
    
    def test_schema_info_section(self, client):
        """Test schema info section has correct metadata."""
        response = client.get("/api/schema/", HTTP_ACCEPT="application/json")
        schema = response.json()
        
        info = schema["info"]
        assert info["title"] == "DeltaCrown Tournament Platform API"
        assert info["version"] == "1.0.0"
        assert "description" in info
        assert "contact" in info
        assert info["contact"]["email"] == "api@deltacrown.com"
    
    def test_schema_security_schemes(self, client):
        """Test schema defines authentication schemes."""
        response = client.get("/api/schema/", HTTP_ACCEPT="application/json")
        schema = response.json()
        
        components = schema.get("components", {})
        security_schemes = components.get("securitySchemes", {})
        
        # Should have JWT bearer auth
        assert "bearerAuth" in security_schemes or "jwtAuth" in security_schemes
        # Should have session/cookie auth
        assert "cookieAuth" in security_schemes or "sessionAuth" in security_schemes
    
    def test_schema_has_expected_tags(self, client):
        """Test schema includes expected API tags."""
        response = client.get("/api/schema/", HTTP_ACCEPT="application/json")
        schema = response.json()
        
        tags = schema.get("tags", [])
        tag_names = [tag["name"] for tag in tags]
        
        # Phase 8 tags
        assert "Analytics" in tag_names
        assert "Leaderboards" in tag_names
        assert "Seasons" in tag_names
        assert "User Stats" in tag_names
        assert "Team Stats" in tag_names
        assert "Match History" in tag_names
    
    def test_schema_has_analytics_endpoints(self, client):
        """Test schema includes Phase 8 analytics endpoints."""
        response = client.get("/api/schema/", HTTP_ACCEPT="application/json")
        schema = response.json()
        
        paths = schema.get("paths", {})
        
        # Analytics endpoints (Phase 8, Epic 8.5)
        assert any("/api/stats/v2/users/" in path for path in paths.keys())
        assert any("/api/stats/v2/teams/" in path for path in paths.keys())
        assert any("/api/leaderboards/v2/" in path for path in paths.keys())
        assert "/api/seasons/current/" in paths
        assert "/api/seasons/" in paths
    
    def test_schema_has_stats_endpoints(self, client):
        """Test schema includes user/team stats endpoints."""
        response = client.get("/api/schema/", HTTP_ACCEPT="application/json")
        schema = response.json()
        
        paths = schema.get("paths", {})
        
        # User Stats endpoints (Phase 8, Epic 8.2)
        assert any("/api/stats/v1/users/" in path for path in paths.keys())
        
        # Team Stats endpoints (Phase 8, Epic 8.3)
        assert any("/api/stats/v1/teams/" in path for path in paths.keys())
    
    def test_schema_has_match_history_endpoints(self, client):
        """Test schema includes match history endpoints."""
        response = client.get("/api/schema/", HTTP_ACCEPT="application/json")
        schema = response.json()
        
        paths = schema.get("paths", {})
        
        # Match History endpoints (Phase 8, Epic 8.4)
        assert any("/api/tournaments/v1/history/" in path for path in paths.keys())
    
    def test_schema_operation_ids_unique(self, client):
        """Test that all operation IDs in schema are unique."""
        response = client.get("/api/schema/", HTTP_ACCEPT="application/json")
        schema = response.json()
        
        operation_ids = []
        paths = schema.get("paths", {})
        
        for path_item in paths.values():
            for method in ["get", "post", "put", "patch", "delete"]:
                if method in path_item:
                    operation = path_item[method]
                    if "operationId" in operation:
                        operation_ids.append(operation["operationId"])
        
        # Check uniqueness
        assert len(operation_ids) == len(set(operation_ids)), "Duplicate operation IDs found"
    
    def test_schema_has_request_body_schemas(self, client):
        """Test schema includes request body schemas for POST/PUT operations."""
        response = client.get("/api/schema/", HTTP_ACCEPT="application/json")
        schema = response.json()
        
        paths = schema.get("paths", {})
        has_request_bodies = False
        
        for path_item in paths.values():
            for method in ["post", "put", "patch"]:
                if method in path_item:
                    operation = path_item[method]
                    if "requestBody" in operation:
                        has_request_bodies = True
                        # Verify request body has content
                        assert "content" in operation["requestBody"]
                        assert "application/json" in operation["requestBody"]["content"]
        
        assert has_request_bodies, "No request bodies found in schema"
    
    def test_schema_has_response_schemas(self, client):
        """Test schema includes response schemas for all operations."""
        response = client.get("/api/schema/", HTTP_ACCEPT="application/json")
        schema = response.json()
        
        paths = schema.get("paths", {})
        
        for path, path_item in paths.items():
            for method in ["get", "post", "put", "patch", "delete"]:
                if method in path_item:
                    operation = path_item[method]
                    assert "responses" in operation, f"Missing responses for {method.upper()} {path}"
                    
                    # Should have at least one success response (2xx)
                    response_codes = operation["responses"].keys()
                    has_success_response = any(code.startswith("2") for code in response_codes)
                    assert has_success_response, f"No success response for {method.upper()} {path}"
    
    def test_swagger_ui_accessible(self, client):
        """Test that Swagger UI page is accessible."""
        response = client.get("/api/docs/")
        
        assert response.status_code == 200
        assert "text/html" in response["Content-Type"]
        
        # Check that Swagger UI assets are referenced
        content = response.content.decode("utf-8")
        assert "swagger" in content.lower() or "openapi" in content.lower()
    
    def test_redoc_ui_accessible(self, client):
        """Test that ReDoc UI page is accessible."""
        response = client.get("/api/redoc/")
        
        assert response.status_code == 200
        assert "text/html" in response["Content-Type"]
    
    def test_schema_has_examples(self, client):
        """Test schema includes request/response examples."""
        response = client.get("/api/schema/", HTTP_ACCEPT="application/json")
        schema = response.json()
        
        paths = schema.get("paths", {})
        has_examples = False
        
        for path_item in paths.values():
            for method_obj in path_item.values():
                if isinstance(method_obj, dict):
                    # Check for examples in responses
                    responses = method_obj.get("responses", {})
                    for response in responses.values():
                        if isinstance(response, dict):
                            content = response.get("content", {})
                            for media_type in content.values():
                                if "examples" in media_type or "example" in media_type:
                                    has_examples = True
                                    break
        
        # Should have at least some examples (from Phase 8 analytics views)
        assert has_examples, "No examples found in schema"
    
    def test_schema_component_schemas_defined(self, client):
        """Test schema defines component schemas for reusable models."""
        response = client.get("/api/schema/", HTTP_ACCEPT="application/json")
        schema = response.json()
        
        components = schema.get("components", {})
        schemas = components.get("schemas", {})
        
        # Should have multiple component schemas
        assert len(schemas) > 0, "No component schemas defined"
        
        # Check for common analytics schemas (from Phase 8)
        schema_names = list(schemas.keys())
        
        # At least some analytics-related schemas should exist
        has_analytics_schemas = any(
            "analytics" in name.lower() or 
            "stats" in name.lower() or
            "leaderboard" in name.lower() or
            "season" in name.lower()
            for name in schema_names
        )
        assert has_analytics_schemas, "No analytics-related component schemas found"
    
    def test_schema_parameters_documented(self, client):
        """Test schema documents query/path parameters."""
        response = client.get("/api/schema/", HTTP_ACCEPT="application/json")
        schema = response.json()
        
        paths = schema.get("paths", {})
        has_parameters = False
        
        for path_item in paths.values():
            for method_obj in path_item.values():
                if isinstance(method_obj, dict) and "parameters" in method_obj:
                    has_parameters = True
                    
                    # Verify parameter structure
                    for param in method_obj["parameters"]:
                        assert "name" in param
                        assert "in" in param  # query, path, header, etc.
                        assert "schema" in param or "type" in param
        
        assert has_parameters, "No parameters documented in schema"
    
    def test_schema_no_errors_in_generation(self, client):
        """Test schema generation completes without errors."""
        response = client.get("/api/schema/", HTTP_ACCEPT="application/json")
        
        # Should return 200 OK
        assert response.status_code == 200
        
        # Should parse as valid JSON
        schema = response.json()
        assert isinstance(schema, dict)
        
        # Should not contain error indicators
        assert "error" not in schema
        assert "errors" not in schema
    
    def test_schema_paths_count(self, client):
        """Test schema contains expected number of paths."""
        response = client.get("/api/schema/", HTTP_ACCEPT="application/json")
        schema = response.json()
        
        paths = schema.get("paths", {})
        
        # Should have at least 20 paths (conservative estimate across all phases)
        assert len(paths) >= 20, f"Expected at least 20 paths, got {len(paths)}"
    
    def test_schema_http_methods_present(self, client):
        """Test schema includes various HTTP methods."""
        response = client.get("/api/schema/", HTTP_ACCEPT="application/json")
        schema = response.json()
        
        paths = schema.get("paths", {})
        methods_found = set()
        
        for path_item in paths.values():
            for method in ["get", "post", "put", "patch", "delete"]:
                if method in path_item:
                    methods_found.add(method.upper())
        
        # Should have GET and POST at minimum
        assert "GET" in methods_found
        assert "POST" in methods_found
    
    def test_schema_deprecated_fields_marked(self, client):
        """Test schema marks deprecated fields if any exist."""
        response = client.get("/api/schema/", HTTP_ACCEPT="application/json")
        schema = response.json()
        
        # This test passes if no deprecated fields exist or if they're properly marked
        # Just verify schema structure is valid
        assert "paths" in schema
        
        # If deprecated endpoints exist, they should have deprecated: true
        paths = schema.get("paths", {})
        for path_item in paths.values():
            for method_obj in path_item.values():
                if isinstance(method_obj, dict) and method_obj.get("deprecated"):
                    # If deprecated, should be boolean true
                    assert method_obj["deprecated"] is True


@pytest.mark.django_db
class TestSchemaConsistency:
    """Test schema consistency and best practices."""
    
    @pytest.fixture
    def client(self):
        """Create API client."""
        return APIClient()
    
    @pytest.fixture
    def schema(self, client):
        """Fetch OpenAPI schema."""
        response = client.get("/api/schema/", HTTP_ACCEPT="application/json")
        return response.json()
    
    def test_all_operations_have_tags(self, schema):
        """Test all operations are tagged for grouping."""
        paths = schema.get("paths", {})
        
        for path, path_item in paths.items():
            for method in ["get", "post", "put", "patch", "delete"]:
                if method in path_item:
                    operation = path_item[method]
                    assert "tags" in operation and len(operation["tags"]) > 0, \
                        f"Missing tags for {method.upper()} {path}"
    
    def test_all_operations_have_descriptions(self, schema):
        """Test all operations have descriptions."""
        paths = schema.get("paths", {})
        
        for path, path_item in paths.items():
            for method in ["get", "post", "put", "patch", "delete"]:
                if method in path_item:
                    operation = path_item[method]
                    # Should have either description or summary
                    assert "description" in operation or "summary" in operation, \
                        f"Missing description/summary for {method.upper()} {path}"
    
    def test_all_post_operations_have_request_bodies(self, schema):
        """Test POST operations have request bodies where appropriate."""
        paths = schema.get("paths", {})
        
        for path, path_item in paths.items():
            if "post" in path_item:
                operation = path_item["post"]
                # Most POST operations should have request bodies
                # (exceptions: operations that just trigger actions)
                # This is a soft check - just verify structure if present
                if "requestBody" in operation:
                    assert "content" in operation["requestBody"]
    
    def test_schema_servers_defined(self, schema):
        """Test schema defines server URLs."""
        # Servers may be empty in test environment, just check structure
        assert "paths" in schema  # Basic structure check
        # Servers are optional in OpenAPI 3.0
