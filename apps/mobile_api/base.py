"""Base view for mobile API endpoints.

Pins the custom mobile exception handler so every /api/mobile/v1/ response
(success or failure) shares the same envelope shape — independent of the
project-wide DRF exception handler used by web/admin APIs.
"""
from rest_framework.views import APIView

from .exception_handler import mobile_exception_handler


class MobileApiView(APIView):
    def get_exception_handler(self):
        return mobile_exception_handler
