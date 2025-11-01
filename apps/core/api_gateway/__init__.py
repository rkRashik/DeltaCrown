"""
Internal API Gateway - Inter-App Communication

Industry-standard API Gateway for loosely coupled inter-app communication.

Benefits:
- No direct imports between apps
- Versioned APIs for backward compatibility
- Can add authentication/authorization
- Request/response logging
- Easy to mock for testing
"""

import logging
from typing import Any, Callable, Dict, Optional
from dataclasses import dataclass
from datetime import datetime


logger = logging.getLogger(__name__)


@dataclass
class APIRequest:
    """API request data"""
    endpoint: str
    method: str  # 'get', 'create', 'update', 'delete'
    data: Dict[str, Any]
    requester: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class APIResponse:
    """API response data"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    status_code: int = 200


class APIGateway:
    """
    Internal API Gateway for app-to-app communication.
    
    Usage:
        # Register an API endpoint
        def get_tournament(request: APIRequest) -> APIResponse:
            tournament_id = request.data['tournament_id']
            tournament = Tournament.objects.get(id=tournament_id)
            return APIResponse(success=True, data={
                'id': tournament.id,
                'name': tournament.name
            })
        
        api_gateway.register_endpoint('tournaments.get', get_tournament, 'v1')
        
        # Call an API endpoint from another app
        response = api_gateway.call(APIRequest(
            endpoint='tournaments.get',
            method='get',
            data={'tournament_id': 123},
            requester='teams_app'
        ))
        
        if response.success:
            tournament_name = response.data['name']
    """
    
    def __init__(self):
        self._endpoints: Dict[str, Dict[str, Callable]] = {}  # {endpoint: {version: handler}}
        self._request_log: list = []
        self._enable_logging = True
        self._max_log_size = 1000
    
    def register_endpoint(
        self,
        endpoint: str,
        handler: Callable[[APIRequest], APIResponse],
        version: str = 'v1'
    ):
        """
        Register an API endpoint.
        
        Args:
            endpoint: Endpoint name (e.g., 'tournaments.get', 'teams.create')
            handler: Function that handles the request
            version: API version
        """
        if endpoint not in self._endpoints:
            self._endpoints[endpoint] = {}
        
        self._endpoints[endpoint][version] = handler
        logger.info(f"📝 Registered API endpoint: {endpoint} ({version})")
    
    def unregister_endpoint(self, endpoint: str, version: Optional[str] = None):
        """Unregister an API endpoint"""
        if endpoint in self._endpoints:
            if version:
                self._endpoints[endpoint].pop(version, None)
                if not self._endpoints[endpoint]:
                    del self._endpoints[endpoint]
            else:
                del self._endpoints[endpoint]
            logger.info(f"❌ Unregistered endpoint: {endpoint}")
    
    def call(
        self,
        request: APIRequest,
        version: str = 'v1'
    ) -> APIResponse:
        """
        Call an API endpoint.
        
        Args:
            request: API request
            version: API version to use
        
        Returns:
            API response
        """
        # Log request
        if self._enable_logging:
            self._request_log.append(request)
            if len(self._request_log) > self._max_log_size:
                self._request_log = self._request_log[-self._max_log_size:]
        
        logger.info(
            f"📞 API call: {request.endpoint} ({request.method}) "
            f"from {request.requester or 'unknown'}"
        )
        
        # Find handler
        if request.endpoint not in self._endpoints:
            logger.error(f"❌ Endpoint not found: {request.endpoint}")
            return APIResponse(
                success=False,
                error=f"Endpoint not found: {request.endpoint}",
                status_code=404
            )
        
        if version not in self._endpoints[request.endpoint]:
            logger.error(
                f"❌ Version not found: {request.endpoint} {version}"
            )
            return APIResponse(
                success=False,
                error=f"Version {version} not found for {request.endpoint}",
                status_code=404
            )
        
        # Call handler
        handler = self._endpoints[request.endpoint][version]
        
        try:
            response = handler(request)
            logger.debug(f"✅ API call successful: {request.endpoint}")
            return response
        
        except Exception as e:
            logger.error(
                f"❌ API call failed: {request.endpoint}",
                exc_info=True
            )
            return APIResponse(
                success=False,
                error=str(e),
                status_code=500
            )
    
    def list_endpoints(self) -> Dict[str, list]:
        """List all registered endpoints with their versions"""
        return {
            endpoint: list(versions.keys())
            for endpoint, versions in self._endpoints.items()
        }
    
    def get_request_log(self, limit: int = 100) -> list:
        """Get recent API request log"""
        return self._request_log[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get API gateway statistics"""
        total_versions = sum(
            len(versions) for versions in self._endpoints.values()
        )
        
        return {
            'total_endpoints': len(self._endpoints),
            'total_versions': total_versions,
            'request_log_size': len(self._request_log),
            'endpoints': list(self._endpoints.keys()),
        }
    
    def __repr__(self):
        stats = self.get_statistics()
        return (
            f"APIGateway(endpoints={stats['total_endpoints']}, "
            f"versions={stats['total_versions']})"
        )


# Global API gateway instance
api_gateway = APIGateway()
