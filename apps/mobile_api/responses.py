"""Response envelope helpers for the mobile API.

Every mobile endpoint MUST return a response shaped as:

    {"success": bool, "data": Any | None, "error": Error | None}

Use ``success_response`` for successful results and ``error_response`` for
failures. Keeping a single shape lets the Flutter client parse every
endpoint identically.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from rest_framework import status as http_status
from rest_framework.response import Response


def success_response(data: Any = None, status: int = http_status.HTTP_200_OK) -> Response:
    return Response(
        {"success": True, "data": data, "error": None},
        status=status,
    )


def error_response(
    code: str,
    message: str,
    details: Optional[Mapping[str, Any]] = None,
    status: int = http_status.HTTP_400_BAD_REQUEST,
) -> Response:
    return Response(
        {
            "success": False,
            "data": None,
            "error": {
                "code": code,
                "message": message,
                "details": dict(details) if details else {},
            },
        },
        status=status,
    )
