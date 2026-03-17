import urllib.parse, json, urllib.request, urllib.error
import logging

logger = logging.getLogger(__name__)

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"
SCOPE = "openid email profile"

def build_auth_url(client_id: str, redirect_uri: str, state: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
        "state": state,
    }
    return AUTH_ENDPOINT + "?" + urllib.parse.urlencode(params)

def _post_json(url: str, data: dict) -> dict:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        logger.error("Google OAuth POST %s returned %d", url, exc.code)
        raise ValueError(f"Google OAuth request failed (HTTP {exc.code})") from exc
    except (urllib.error.URLError, OSError) as exc:
        logger.error("Google OAuth POST %s network error: %s", url, exc)
        raise ValueError("Google OAuth request failed (network error)") from exc

def _get_json(url: str, bearer: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {bearer}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        logger.error("Google OAuth GET %s returned %d", url, exc.code)
        raise ValueError(f"Google OAuth request failed (HTTP {exc.code})") from exc
    except (urllib.error.URLError, OSError) as exc:
        logger.error("Google OAuth GET %s network error: %s", url, exc)
        raise ValueError("Google OAuth request failed (network error)") from exc

def exchange_code_for_userinfo(*, code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
    """
    Returns a dict like: {"sub": "...", "email": "...", "email_verified": true, "name": "..."}
    """
    token = _post_json(TOKEN_ENDPOINT, {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    })
    access_token = token.get("access_token")
    if not access_token:
        raise ValueError("No access_token from Google")
    return _get_json(USERINFO_ENDPOINT, access_token)
