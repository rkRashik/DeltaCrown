"""
Shared screenshot OCR utilities — Supabase Storage + Gemini Vision.

Used by:
    apps/tournaments/services/br_screenshot_service.py     (BR lobby OCR)
    apps/tournaments/services/sports_screenshot_service.py (1v1 sports OCR)

We talk to Supabase Storage's REST API directly (no SDK) and configure
google-generativeai lazily, both to keep the Render container under its 512 MB
ceiling and to avoid double-importing transitive trees in two services.

Public surface
==============
    Errors:
        ScreenshotError                  base
        ScreenshotConfigError            missing env / package      (HTTP 503)
        ScreenshotUploadError            Supabase upload failed     (HTTP 502)
        ScreenshotExtractionError        Gemini call failed         (HTTP 422)

    Storage:
        get_screenshots_bucket()         -> str
        build_storage_path(*segments, original_filename='') -> str
        upload_screenshot(image_bytes, content_type, *, bucket='', storage_path) -> (public_url, path)
        delete_screenshot(storage_path, *, bucket='') -> bool

    Gemini:
        get_gemini_model()               -> genai.GenerativeModel
        strip_json_fences(text)          -> str
        call_gemini_vision_json(prompt, image_bytes, content_type) -> dict

Env vars
========
    GEMINI_API_KEY                  required
    GEMINI_MODEL                    optional, default 'gemini-1.5-flash'
    SUPABASE_URL                    required (e.g. https://xxx.supabase.co)
    SUPABASE_SERVICE_KEY            required (service role JWT)
    SUPABASE_SCREENSHOTS_BUCKET     optional, default 'screenshots'
"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from difflib import SequenceMatcher
from typing import Any, Dict, Tuple

logger = logging.getLogger(__name__)


# ── Errors ─────────────────────────────────────────────────────────────────

class ScreenshotError(Exception):
    """Base error for the screenshot OCR pipeline."""

    def __init__(self, message: str, code: str = "screenshot_error", details: Any = None):
        super().__init__(message)
        self.code = code
        self.details = details


class ScreenshotConfigError(ScreenshotError):
    """Required env var or package missing — surfaces as HTTP 503."""


class ScreenshotUploadError(ScreenshotError):
    """Supabase Storage upload failure — surfaces as HTTP 502."""


class ScreenshotExtractionError(ScreenshotError):
    """Gemini Vision call failed or returned a non-parseable response — HTTP 422."""


# ── Env helpers ────────────────────────────────────────────────────────────

_ALLOWED_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ScreenshotConfigError(
            f"Environment variable {name} is not set.",
            code="missing_env",
            details={"variable": name},
        )
    return value


def get_screenshots_bucket() -> str:
    return os.getenv("SUPABASE_SCREENSHOTS_BUCKET", "screenshots")


def _supabase_base_url() -> str:
    return require_env("SUPABASE_URL").rstrip("/")


def _supabase_headers() -> Dict[str, str]:
    key = require_env("SUPABASE_SERVICE_KEY")
    return {
        "Authorization": f"Bearer {key}",
        "apikey": key,
    }


# ── Storage path builder ───────────────────────────────────────────────────

def build_storage_path(*segments: str, original_filename: str = "") -> str:
    """
    Join ``segments`` with '/' and append ``<uuid4>.<ext>``.

    Extensions are whitelisted to a small set of image types; anything else
    falls back to ``.jpg`` so we never write executables or unknown blobs.

        build_storage_path('br', 'tournament_42', 'match_99', original_filename='shot.png')
        # → 'br/tournament_42/match_99/<uuid>.png'
    """
    ext = ".jpg"
    if original_filename and "." in original_filename:
        candidate = "." + original_filename.rsplit(".", 1)[-1].lower()
        if candidate in _ALLOWED_EXTS:
            ext = candidate
    cleaned = [str(s).strip("/").strip() for s in segments if s]
    cleaned = [s for s in cleaned if s]
    cleaned.append(f"{uuid.uuid4().hex}{ext}")
    return "/".join(cleaned)


# ── Supabase Storage REST: upload / delete ────────────────────────────────

def upload_screenshot(
    image_bytes: bytes,
    content_type: str,
    *,
    bucket: str = "",
    storage_path: str,
) -> Tuple[str, str]:
    """
    Upload raw image bytes to Supabase Storage via REST. Returns
    ``(public_url, storage_path)``.

    Raises ``ScreenshotUploadError`` on transport failure or non-2xx response.
    The caller is responsible for building the storage_path (see
    ``build_storage_path``).
    """
    import requests  # already in requirements.txt

    bucket = bucket or get_screenshots_bucket()
    base = _supabase_base_url()
    url = f"{base}/storage/v1/object/{bucket}/{storage_path}"

    headers = _supabase_headers()
    headers["Content-Type"] = content_type or "image/jpeg"
    # uuid in path → no collisions; explicit false makes overwrites loud.
    headers["x-upsert"] = "false"
    headers["cache-control"] = "no-store"

    try:
        resp = requests.post(url, data=image_bytes, headers=headers, timeout=20)
    except requests.RequestException as exc:
        raise ScreenshotUploadError(
            f"Failed to reach Supabase Storage: {exc}",
            code="supabase_upload_failed",
            details={"path": storage_path},
        ) from exc

    if resp.status_code >= 300:
        # Avoid leaking the service key — log only status + path + truncated body.
        logger.warning(
            "screenshot: supabase upload failed status=%s path=%s body=%s",
            resp.status_code, storage_path, resp.text[:200],
        )
        raise ScreenshotUploadError(
            f"Supabase upload returned HTTP {resp.status_code}.",
            code="supabase_upload_failed",
            details={"status": resp.status_code, "path": storage_path},
        )

    public_url = f"{base}/storage/v1/object/public/{bucket}/{storage_path}"
    return public_url, storage_path


def delete_screenshot(storage_path: str, *, bucket: str = "") -> bool:
    """
    Best-effort delete via REST. Logs but never raises — callers run this in
    a ``finally`` block where a raise would mask the real error.
    """
    if not storage_path:
        return False

    import requests

    try:
        bucket = bucket or get_screenshots_bucket()
        base = _supabase_base_url()
        headers = _supabase_headers()
    except ScreenshotConfigError as exc:
        logger.warning(
            "screenshot: skipping delete (config missing) path=%s err=%s",
            storage_path, exc,
        )
        return False

    url = f"{base}/storage/v1/object/{bucket}/{storage_path}"
    try:
        resp = requests.delete(url, headers=headers, timeout=10)
    except requests.RequestException as exc:
        logger.warning(
            "screenshot: failed to delete supabase object path=%s err=%s",
            storage_path, exc,
        )
        return False

    if resp.status_code >= 300:
        logger.warning(
            "screenshot: supabase delete returned status=%s path=%s body=%s",
            resp.status_code, storage_path, resp.text[:200],
        )
        return False
    return True


# ── Gemini Vision (lazy + JSON-strict helper) ──────────────────────────────

_GEMINI_MODEL_CACHE: Dict[str, Any] = {}


def get_gemini_model():
    """Lazily configure google-generativeai and return a singleton model."""
    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    if model_name in _GEMINI_MODEL_CACHE:
        return _GEMINI_MODEL_CACHE[model_name]

    api_key = require_env("GEMINI_API_KEY")
    try:
        import google.generativeai as genai  # type: ignore
    except ImportError as exc:
        raise ScreenshotConfigError(
            "google-generativeai is not installed on this server.",
            code="missing_package",
            details={"package": "google-generativeai"},
        ) from exc

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    _GEMINI_MODEL_CACHE[model_name] = model
    return model


_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


def strip_json_fences(text: str) -> str:
    """Remove ```json ... ``` fences Gemini sometimes wraps responses in."""
    if not text:
        return ""
    return _JSON_FENCE_RE.sub("", text.strip()).strip()


# ── Fuzzy name matching (shared across all OCR services) ──────────────────
#
# Used to map AI-extracted strings (team names, IGNs) to participant_ids /
# user_ids in the database. Stdlib only — no external NLP deps.

_NORMALIZE_RE = re.compile(r"[^\w\s]+", re.UNICODE)


def normalize_name(name: str) -> str:
    """Lowercase, strip non-word chars, collapse whitespace."""
    if not name:
        return ""
    return _NORMALIZE_RE.sub(" ", name.lower()).strip()


def name_similarity(a: str, b: str) -> float:
    """0.0..1.0 similarity using ``difflib.SequenceMatcher`` on normalized names."""
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def call_gemini_vision_json(
    prompt: str,
    image_bytes: bytes,
    content_type: str,
) -> Dict[str, Any]:
    """
    Call Gemini Vision with ``prompt`` + inline image and parse the response
    as JSON. Returns the parsed dict.

    Raises ``ScreenshotExtractionError`` on any failure path: SDK error, empty
    response, malformed JSON. Caller is responsible for further shape /
    domain validation on the returned dict.
    """
    model = get_gemini_model()

    try:
        response = model.generate_content(
            [
                prompt,
                {"mime_type": content_type or "image/jpeg", "data": image_bytes},
            ],
            generation_config={
                "temperature": 0.1,
                "response_mime_type": "application/json",
            },
        )
    except Exception as exc:
        raise ScreenshotExtractionError(
            f"Gemini Vision call failed: {exc}",
            code="gemini_call_failed",
        ) from exc

    text = ""
    try:
        text = (response.text or "").strip()
    except Exception:
        # Some SDK paths surface text via .candidates[0].content.parts[*].text
        try:
            parts = response.candidates[0].content.parts  # type: ignore[attr-defined]
            text = "".join(getattr(p, "text", "") for p in parts).strip()
        except Exception:
            text = ""

    if not text:
        raise ScreenshotExtractionError(
            "Gemini returned an empty response.",
            code="empty_response",
        )

    text = strip_json_fences(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ScreenshotExtractionError(
            "Gemini response was not valid JSON.",
            code="invalid_json",
            details={"raw": text[:500]},
        ) from exc
