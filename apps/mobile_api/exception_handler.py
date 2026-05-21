"""Custom DRF exception handler that wraps errors in the mobile envelope."""
from __future__ import annotations

from rest_framework import status as http_status
from rest_framework.exceptions import APIException, AuthenticationFailed, NotAuthenticated
from rest_framework.views import exception_handler as drf_exception_handler


_CODE_MAP = {
    http_status.HTTP_400_BAD_REQUEST: "bad_request",
    http_status.HTTP_401_UNAUTHORIZED: "not_authenticated",
    http_status.HTTP_403_FORBIDDEN: "forbidden",
    http_status.HTTP_404_NOT_FOUND: "not_found",
    http_status.HTTP_405_METHOD_NOT_ALLOWED: "method_not_allowed",
    http_status.HTTP_406_NOT_ACCEPTABLE: "not_acceptable",
    http_status.HTTP_409_CONFLICT: "conflict",
    http_status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: "unsupported_media_type",
    http_status.HTTP_429_TOO_MANY_REQUESTS: "throttled",
}


def mobile_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    status_code = response.status_code
    code = _resolve_code(exc, status_code)
    message = _resolve_message(exc, response.data)
    details = _resolve_details(response.data)

    response.data = {
        "success": False,
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
    }
    return response


def _resolve_code(exc, status_code: int) -> str:
    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        return "not_authenticated"
    if isinstance(exc, APIException) and getattr(exc, "default_code", None):
        return str(exc.default_code)
    return _CODE_MAP.get(status_code, "error")


def _resolve_message(exc, data) -> str:
    if isinstance(exc, APIException):
        detail = getattr(exc, "detail", None)
        if isinstance(detail, str):
            return detail
    if isinstance(data, dict) and "detail" in data and isinstance(data["detail"], str):
        return data["detail"]
    if isinstance(data, str):
        return data
    return "Request failed."


def _resolve_details(data) -> dict:
    if isinstance(data, dict):
        cleaned = {k: v for k, v in data.items() if k != "detail"}
        return cleaned
    if isinstance(data, list):
        return {"errors": data}
    return {}
