import asyncio
import json
import os
import random
import re
import string
import sys
import threading
import time
from datetime import timedelta
from pathlib import Path
from wsgiref.simple_server import make_server

import requests


BASE_URL = "http://127.0.0.1:8011"
SETTINGS_URL = f"{BASE_URL}/me/settings/"
PROJECT_ROOT = Path(__file__).resolve().parents[1]

DIRECT_ROUTES = {
    "valorant": "/api/oauth/riot/login/",
    "cs2": "/profile/api/oauth/steam/login/?game=cs2",
    "dota2": "/profile/api/oauth/steam/login/?game=dota2",
    "rocketleague": "/api/oauth/epic/login/",
}

SLUG_ALIASES = {
    "valorant": "valorant",
    "cs2": "cs2",
    "counter-strike-2": "cs2",
    "counterstrike2": "cs2",
    "dota2": "dota2",
    "dota-2": "dota2",
    "rocketleague": "rocketleague",
    "rocket-league": "rocketleague",
    "efootball": "efootball",
    "pubgmobile": "pubgm",
    "pubg-mobile": "pubgm",
    "pubgm": "pubgm",
    "ea-fc": "ea-fc",
    "easportsfc26": "ea-fc",
    "fc26": "ea-fc",
    "eafc": "ea-fc",
    "codm": "codm",
    "mlbb": "mlbb",
    "freefire": "freefire",
    "r6siege": "r6siege",
    "r6-siege": "r6siege",
}


def canonical_slug(value: str) -> str:
    raw = str(value or "").strip().lower().replace("_", "-").replace(" ", "")
    clean = "".join(ch for ch in raw if ch.isalnum() or ch == "-")
    return SLUG_ALIASES.get(clean, clean)


def random_suffix(length: int = 6) -> str:
    return "".join(random.choice(string.digits) for _ in range(length))


def extract_games(payload):
    if not payload:
        return []
    data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data, dict) and isinstance(data.get("games"), list):
        return data["games"]
    if isinstance(payload, dict) and isinstance(payload.get("games"), list):
        return payload["games"]
    if isinstance(data, list):
        return data
    if isinstance(payload, list):
        return payload
    return []


def extract_passports(payload):
    if not payload:
        return []
    data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data, dict) and isinstance(data.get("passports"), list):
        return data["passports"]
    if isinstance(payload, dict) and isinstance(payload.get("passports"), list):
        return payload["passports"]
    if isinstance(data, list):
        return data
    if isinstance(payload, list):
        return payload
    return []


def option_value(option) -> str:
    if isinstance(option, dict):
        return str(option.get("value") or option.get("label") or "")
    return str(option)


def build_metadata(schema: list, marker: str) -> dict:
    metadata = {}
    for idx, field in enumerate(schema or []):
        key = str(field.get("key") or f"field_{idx}")
        field_type = str(field.get("type") or "text").lower()
        options = field.get("options") or []

        if field_type == "select" and options:
            metadata[key] = option_value(options[0])
            continue

        if "ign" in key or "name" in key:
            metadata[key] = f"qa_{marker}_{idx}"
        elif "id" in key or "uid" in key:
            metadata[key] = random_suffix(9)
        elif "tag" in key:
            metadata[key] = f"TAG{random_suffix(2)}"
        elif "region" in key:
            metadata[key] = "Asia"
        elif "role" in key:
            metadata[key] = "Support"
        else:
            metadata[key] = f"qa_{marker}_{idx}"

    return metadata


def value_for_field(field: dict, marker: str, idx: int) -> str:
    key = str(field.get("key") or f"field_{idx}")
    label = str(field.get("label") or key).lower()
    regex = str(field.get("validation_regex") or "").strip()
    min_length = field.get("min_length")
    max_length = field.get("max_length")

    if regex == r"^6\d{9}$":
        return "6" + random_suffix(9)
    if regex == r"^\d{9,12}$":
        return random_suffix(9)
    if regex == r"^\d{8,12}$":
        return random_suffix(8)
    if regex == r"^\d{4,6}$":
        return random_suffix(4)
    if regex == r"^[A-Z]{4}-\d{3}-\d{3}-\d{3}$":
        return "ABCD-123-456-789"

    if "uid" in key or "player_id" in key or ("id" in key and "ea_id" not in key):
        return random_suffix(10)
    if "ign" in key or "name" in key:
        return f"qa_{marker}_{idx}"
    if "ea_id" in key or "konami_id" in key or "user" in label:
        return f"qa_{marker}_{idx}_{random_suffix(3)}"

    candidate = f"qa_{marker}_{idx}"

    try:
        min_n = int(min_length) if min_length is not None else None
    except (TypeError, ValueError):
        min_n = None
    try:
        max_n = int(max_length) if max_length is not None else None
    except (TypeError, ValueError):
        max_n = None

    if min_n and len(candidate) < min_n:
        candidate = candidate + ("x" * (min_n - len(candidate)))
    if max_n and len(candidate) > max_n:
        candidate = candidate[:max_n]

    if regex:
        try:
            if not re.match(regex, candidate):
                if "\\d" in regex:
                    target_len = min_n or 8
                    if max_n:
                        target_len = min(target_len, max_n)
                    candidate = "1" * max(target_len, 1)
        except re.error:
            pass

    return candidate


def wait_for_server(url: str, timeout: float = 45.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code in (200, 302):
                return True
        except requests.RequestException:
            pass
        time.sleep(0.5)
    return False


def fail(results: dict, key: str, message: str):
    results["checks"][key] = {"status": "failed", "message": message}
    raise RuntimeError(message)


def decode_json_bytes(data: bytes):
    return json.loads(data.decode("utf-8", errors="ignore"))


def safe_response_json(response):
    try:
        return response.json()
    except Exception:
        return {"raw": response.text()}


def find_passport_by_slug(passports: list, slug: str):
    for item in passports:
        item_slug = canonical_slug(
            (item.get("game") or {}).get("slug")
            or item.get("game_slug")
            or item.get("game_display_name")
        )
        if item_slug == slug:
            return item
    return None


def find_latest_passport_by_slug(passports: list, slug: str):
    candidates = []
    for item in passports:
        item_slug = canonical_slug(
            (item.get("game") or {}).get("slug")
            or item.get("game_slug")
            or item.get("game_display_name")
        )
        if item_slug == slug:
            candidates.append(item)
    if not candidates:
        return None
    return max(candidates, key=lambda obj: int(obj.get("id") or 0))


def main() -> int:
    from playwright.sync_api import sync_playwright

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "deltacrown.settings")

    import django

    django.setup()

    from django.contrib.auth import get_user_model
    from django.contrib.staticfiles.handlers import StaticFilesHandler
    from django.core.wsgi import get_wsgi_application
    from django.test import Client
    from django.utils import timezone

    from apps.user_profile.models import GameProfile
    from apps.user_profile.models.delete_otp import GamePassportDeleteOTP

    results = {
        "started_at": timezone.now().isoformat(),
        "base_url": BASE_URL,
        "checks": {},
        "notes": [],
    }
    current_step = "bootstrap"

    httpd = None
    server_thread = None

    try:
        current_step = "start_server"
        application = StaticFilesHandler(get_wsgi_application())
        httpd = make_server("127.0.0.1", 8011, application)
        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()

        if not wait_for_server(SETTINGS_URL):
            fail(results, "server_start", "Django dev server did not start in time.")

        results["checks"]["server_start"] = {
            "status": "passed",
            "message": "Django dev server is reachable.",
        }

        current_step = "seed_test_user"
        User = get_user_model()
        suffix = random_suffix(8)
        username = f"phase9_qa_{suffix}"
        email = f"{username}@example.com"
        password = "DeltaCrown#QA2026"

        user = User.objects.create_user(username=username, email=email, password=password)
        client = Client()
        client.force_login(user)

        current_step = "baseline_settings_check"
        settings_response = client.get("/me/settings/")
        if settings_response.status_code not in (200, 302):
            fail(results, "settings_page", f"Unexpected settings response status: {settings_response.status_code}")

        if settings_response.status_code == 302:
            settings_response = client.get(settings_response["Location"])

        settings_html = settings_response.content.decode("utf-8", errors="ignore")
        required_ids = [
            "tab-passports",
            "gp-connected-grid",
            "gp-add-grid",
            "gp-id-modal",
            "gp-disconnect-modal",
        ]
        missing_ids = [name for name in required_ids if name not in settings_html]
        if missing_ids:
            fail(results, "settings_markup", f"Missing required passports markup IDs: {missing_ids}")

        results["checks"]["settings_markup"] = {
            "status": "passed",
            "message": "Player Hub template IDs are present in settings page.",
        }

        current_step = "baseline_api_check"
        games_response = client.get("/profile/api/games/")
        if games_response.status_code != 200:
            fail(results, "games_api", f"Games API failed with status {games_response.status_code}")

        games_payload = decode_json_bytes(games_response.content)
        games = extract_games(games_payload)
        if not games:
            fail(results, "games_api", "Games API returned no games.")

        passports_response = client.get("/profile/api/game-passports/")
        if passports_response.status_code != 200:
            fail(results, "passports_api", f"Passports API failed with status {passports_response.status_code}")

        results["checks"]["api_baseline"] = {
            "status": "passed",
            "message": f"Games API returned {len(games)} games and passports API responded successfully.",
        }

        canonical_games = []
        for game in games:
            slug = canonical_slug(game.get("slug") or game.get("name") or game.get("display_name"))
            canonical_games.append((slug, game))

        manual_candidates = []
        for slug, game in canonical_games:
            schema = game.get("passport_schema") or []
            if slug not in DIRECT_ROUTES and schema:
                manual_candidates.append((slug, game))

        if not manual_candidates:
            fail(results, "manual_candidates", "Need at least one manual-schema game for smoke flow.")

        manual_games_by_slug = {slug: game for slug, game in manual_candidates}

        session_cookie = client.cookies.get("sessionid")
        if not session_cookie:
            fail(results, "session_cookie", "Failed to obtain authenticated session cookie from Django client.")

        csrf_cookie = client.cookies.get("csrftoken")

        direct_route_requests = []
        otp_request_count = {"count": 0}

        if sys.platform.startswith("win"):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            results["notes"].append(
                f"Event loop policy before Playwright: {asyncio.get_event_loop_policy().__class__.__name__}"
            )

        with sync_playwright() as p:
            current_step = "launch_browser"
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(base_url=BASE_URL)

            cookie_list = [
                {
                    "name": "sessionid",
                    "value": session_cookie.value,
                    "url": BASE_URL,
                    "httpOnly": True,
                }
            ]
            if csrf_cookie:
                cookie_list.append(
                    {
                        "name": "csrftoken",
                        "value": csrf_cookie.value,
                        "url": BASE_URL,
                        "httpOnly": False,
                    }
                )
            context.add_cookies(cookie_list)

            page = context.new_page()
            page.on(
                "request",
                lambda request: otp_request_count.__setitem__("count", otp_request_count["count"] + 1)
                if "/profile/api/game-passports/request-delete-otp/" in request.url
                else None,
            )

            current_step = "open_settings_in_browser"
            page.goto("/me/settings/", wait_until="domcontentloaded", timeout=60000)
            page.locator('button[data-target="passports"]').first.click(timeout=10000)
            page.wait_for_selector("#tab-passports.active", timeout=15000)
            page.wait_for_selector("#gp-add-grid button[data-action='add-game']", timeout=20000)

            rendered_add_slugs = page.locator("#gp-add-grid button[data-action='add-game']").evaluate_all(
                "buttons => buttons.map(btn => btn.dataset.gameSlug).filter(Boolean)"
            )
            rendered_add_pairs = [(raw, canonical_slug(raw)) for raw in rendered_add_slugs]

            direct_button_slug = None
            direct_slug = None
            for raw_slug, canonical in rendered_add_pairs:
                if canonical in DIRECT_ROUTES:
                    direct_button_slug = raw_slug
                    direct_slug = canonical
                    break

            if not direct_button_slug or not direct_slug:
                fail(results, "direct_button_present", "No rendered direct-connect add card was found in the UI.")

            manual_button_slug = None
            manual_slug = None
            manual_game = None
            for raw_slug, canonical in rendered_add_pairs:
                if canonical in manual_games_by_slug:
                    manual_button_slug = raw_slug
                    manual_slug = canonical
                    manual_game = manual_games_by_slug[canonical]
                    break

            if not manual_button_slug or not manual_game:
                fail(results, "manual_button_present", "No rendered manual-schema add card was found in the UI.")

            lock_slug = None
            lock_game = None
            for candidate_slug, candidate_game in manual_candidates:
                if candidate_slug != manual_slug:
                    lock_slug = candidate_slug
                    lock_game = candidate_game
                    break
            if not lock_game:
                lock_slug = manual_slug
                lock_game = manual_game

            def oauth_abort(route, request):
                direct_route_requests.append(request.url)
                route.abort()

            context.route("**/api/oauth/**", oauth_abort)
            context.route("**/profile/api/oauth/**", oauth_abort)

            current_step = "direct_connect_click"
            direct_btn = page.locator(
                f"button[data-action='add-game'][data-game-slug='{direct_button_slug}']"
            )
            direct_btn.first.click(timeout=10000)
            page.wait_for_timeout(1000)

            context.unroute("**/api/oauth/**", oauth_abort)
            context.unroute("**/profile/api/oauth/**", oauth_abort)

            expected_route = DIRECT_ROUTES[direct_slug]
            if not any(expected_route in request_url for request_url in direct_route_requests):
                fail(
                    results,
                    "direct_connect_flow",
                    f"Direct connect click did not hit expected route: {expected_route}",
                )

            results["checks"]["direct_connect_flow"] = {
                "status": "passed",
                "message": f"Clicking {direct_slug} add card requested {expected_route} via window.location redirect path.",
            }

            # Restore clean page state after direct-connect redirect attempt.
            current_step = "reload_for_manual_flow"
            page.goto("/me/settings/", wait_until="domcontentloaded", timeout=60000)
            page.locator('button[data-target="passports"]').first.click(timeout=10000)
            page.wait_for_selector("#tab-passports.active", timeout=15000)
            page.wait_for_selector("#gp-add-grid button[data-action='add-game']", timeout=20000)

            rendered_add_slugs_after_direct = page.locator(
                "#gp-add-grid button[data-action='add-game']"
            ).evaluate_all("buttons => buttons.map(btn => btn.dataset.gameSlug).filter(Boolean)")

            refreshed_manual_button_slug = None
            for raw_slug in rendered_add_slugs_after_direct:
                canonical = canonical_slug(raw_slug)
                if canonical == manual_slug:
                    refreshed_manual_button_slug = raw_slug
                    break

            if not refreshed_manual_button_slug:
                for raw_slug in rendered_add_slugs_after_direct:
                    canonical = canonical_slug(raw_slug)
                    if canonical in manual_games_by_slug:
                        refreshed_manual_button_slug = raw_slug
                        manual_slug = canonical
                        manual_game = manual_games_by_slug[canonical]
                        break

            if not refreshed_manual_button_slug:
                fail(
                    results,
                    "manual_button_present",
                    "No rendered manual-schema add card was found after direct-connect validation.",
                )

            current_step = "manual_modal_open"
            manual_btn = page.locator(
                f"button[data-action='add-game'][data-game-slug='{refreshed_manual_button_slug}']"
            )
            manual_btn.first.click(timeout=10000, force=True)
            page.wait_for_selector("#gp-id-modal:not(.hidden)", timeout=10000)
            page.wait_for_selector("#gp-id-fields [data-id-field]", timeout=10000)

            field_count = page.locator("#gp-id-fields [data-id-field]").count()
            if field_count < 1:
                fail(results, "manual_modal_fields", "Schema modal opened but no backend fields were rendered.")

            schema_fields = manual_game.get("passport_schema") or []
            for idx, schema_field in enumerate(schema_fields):
                key = schema_field.get("key")
                if not key:
                    continue

                field = page.locator(f'#gp-id-fields [data-id-field="{key}"]')
                if field.count() == 0:
                    continue

                target = field.first
                tag_name = target.evaluate("el => el.tagName.toLowerCase()")
                if tag_name == "select":
                    options_count = target.locator("option").count()
                    if options_count > 1:
                        target.select_option(index=1)
                    else:
                        target.select_option(index=0)
                    continue

                if tag_name == "input":
                    input_type = (target.get_attribute("type") or "text").lower()
                    if input_type in ("checkbox", "radio"):
                        target.check()
                        continue

                target.fill(value_for_field(schema_field, manual_slug, idx))

            current_step = "manual_submit_create"
            with page.expect_response(
                lambda r: "/profile/api/game-passports/create/" in r.url,
                timeout=20000,
            ) as create_resp_info:
                page.locator("#gp-id-save").click(timeout=10000)

            create_resp = create_resp_info.value
            create_json = safe_response_json(create_resp)
            if create_resp.status >= 400 or (
                isinstance(create_json, dict) and create_json.get("success") is False
            ):
                fail(
                    results,
                    "manual_submit",
                    f"Manual modal submit failed: status={create_resp.status}, payload={create_json}",
                )

            page.wait_for_selector("#gp-id-modal", state="hidden", timeout=15000)

            passports_after_create = extract_passports(client.get("/profile/api/game-passports/").json())
            created_passport = find_passport_by_slug(passports_after_create, manual_slug)
            if not created_passport:
                fail(
                    results,
                    "manual_submit_verify",
                    f"Created passport for {manual_slug} not found after submit.",
                )

            created_passport_id = int(created_passport["id"])

            results["checks"]["manual_schema_flow"] = {
                "status": "passed",
                "message": f"Manual game {manual_slug} opened schema modal with {field_count} fields and submitted successfully.",
            }

            # Ensure the created profile is eligible for OTP delete flow.
            gp_obj = GameProfile.objects.get(id=created_passport_id)
            gp_obj.locked_until = timezone.now() - timedelta(days=1)
            gp_obj.verification_status = "PENDING"
            gp_obj.save(update_fields=["locked_until", "verification_status"])

            current_step = "otp_request_flow"
            page.reload(wait_until="domcontentloaded", timeout=60000)
            page.locator('button[data-target="passports"]').first.click(timeout=10000)
            page.wait_for_selector("#tab-passports.active", timeout=15000)
            page.wait_for_selector(
                f"button[data-action='disconnect'][data-passport-id='{created_passport_id}']",
                timeout=20000,
            )

            disconnect_btn = page.locator(
                f"button[data-action='disconnect'][data-passport-id='{created_passport_id}']"
            )
            if disconnect_btn.count() == 0:
                fail(results, "disconnect_button_present", "Disconnect button not found for created passport.")

            with page.expect_response(
                lambda r: "/profile/api/game-passports/request-delete-otp/" in r.url,
                timeout=20000,
            ) as otp_resp_info:
                disconnect_btn.first.click(timeout=10000)

            otp_resp = otp_resp_info.value
            otp_json = safe_response_json(otp_resp)
            if otp_resp.status >= 400 or (isinstance(otp_json, dict) and otp_json.get("success") is False):
                fail(
                    results,
                    "otp_request",
                    f"OTP request failed unexpectedly: status={otp_resp.status}, payload={otp_json}",
                )

            page.wait_for_selector("#gp-disconnect-modal:not(.hidden)", timeout=10000)
            resend_disabled = page.locator("#gp-disconnect-resend").is_disabled()
            timer_text = page.locator("#gp-disconnect-timer").inner_text(timeout=5000)
            if not resend_disabled or "Resend in" not in timer_text:
                fail(results, "otp_resend_timer_ui", "Resend timer UI did not start or resend button was not disabled.")

            resend_backend = client.post(
                "/profile/api/game-passports/request-delete-otp/",
                data=json.dumps({"passport_id": created_passport_id}),
                content_type="application/json",
            )
            if resend_backend.status_code != 429:
                fail(
                    results,
                    "otp_resend_cooldown_backend",
                    f"Expected cooldown 429 on immediate resend, got {resend_backend.status_code}.",
                )

            current_step = "otp_invalid_confirm"
            with page.expect_response(
                lambda r: "/profile/api/game-passports/confirm-delete/" in r.url,
                timeout=20000,
            ) as bad_confirm_resp_info:
                page.locator("#gp-disconnect-code").fill("000000")
                page.locator("#gp-disconnect-confirm").click(timeout=10000)

            bad_confirm_resp = bad_confirm_resp_info.value
            if bad_confirm_resp.status < 400:
                fail(results, "otp_invalid_code", "Invalid OTP code was unexpectedly accepted.")

            page.wait_for_selector("#gp-disconnect-error:not(.hidden)", timeout=10000)

            latest_otp = (
                GamePassportDeleteOTP.objects.filter(
                    user=user,
                    passport_id=created_passport_id,
                    used=False,
                )
                .order_by("-created_at")
                .first()
            )
            if not latest_otp:
                fail(results, "otp_code_lookup", "Could not find latest OTP code in database for confirmation test.")

            current_step = "otp_valid_confirm"
            with page.expect_response(
                lambda r: "/profile/api/game-passports/confirm-delete/" in r.url,
                timeout=20000,
            ) as ok_confirm_resp_info:
                page.locator("#gp-disconnect-code").fill(str(latest_otp.code))
                page.locator("#gp-disconnect-confirm").click(timeout=10000)

            ok_confirm_resp = ok_confirm_resp_info.value
            ok_confirm_json = safe_response_json(ok_confirm_resp)
            if ok_confirm_resp.status >= 400 or (
                isinstance(ok_confirm_json, dict) and ok_confirm_json.get("success") is False
            ):
                fail(
                    results,
                    "otp_confirm_success",
                    f"Valid OTP confirm failed: status={ok_confirm_resp.status}, payload={ok_confirm_json}",
                )

            page.wait_for_selector("#gp-disconnect-modal", state="hidden", timeout=15000)
            if GameProfile.objects.filter(id=created_passport_id).exists():
                fail(results, "otp_confirm_delete_effect", "Passport still exists after successful OTP confirmation.")

            results["checks"]["otp_disconnect_flow"] = {
                "status": "passed",
                "message": "Request, resend cooldown, invalid code handling, and valid OTP confirmation all behaved correctly.",
            }

            current_step = "lock_setup"
            lock_schema = lock_game.get("passport_schema") or []
            lock_metadata = build_metadata(lock_schema, "lock")
            lock_create_resp = client.post(
                "/profile/api/game-passports/create/",
                data=json.dumps(
                    {
                        "game_id": lock_game["id"],
                        "metadata": lock_metadata,
                        "pinned": False,
                    }
                ),
                content_type="application/json",
            )

            if lock_create_resp.status_code >= 400:
                fail(
                    results,
                    "lock_setup_create",
                    "Failed to create lock-test passport: "
                    f"{lock_create_resp.status_code} {lock_create_resp.content.decode('utf-8', errors='ignore')}",
                )

            passports_after_lock_create = extract_passports(client.get("/profile/api/game-passports/").json())
            lock_passport = find_latest_passport_by_slug(passports_after_lock_create, lock_slug)
            if not lock_passport:
                fail(results, "lock_setup_find", "Could not locate lock-test passport after create.")

            lock_passport_id = int(lock_passport["id"])
            lock_obj = GameProfile.objects.get(id=lock_passport_id)
            lock_obj.locked_until = timezone.now() + timedelta(days=7)
            lock_obj.verification_status = "PENDING"
            lock_obj.save(update_fields=["locked_until", "verification_status"])

            current_step = "lock_ui_verify"
            page.reload(wait_until="domcontentloaded", timeout=60000)
            page.locator('button[data-target="passports"]').first.click(timeout=10000)
            page.wait_for_selector("#tab-passports.active", timeout=15000)
            page.wait_for_selector(
                f"button[data-action='disconnect'][data-passport-id='{lock_passport_id}']",
                timeout=20000,
            )

            otp_count_before = otp_request_count["count"]
            lock_disconnect_btn = page.locator(
                f"button[data-action='disconnect'][data-passport-id='{lock_passport_id}']"
            )
            if lock_disconnect_btn.count() == 0:
                fail(results, "lock_disconnect_button", "Disconnect button not found for lock-test passport.")

            lock_disconnect_btn.first.click(timeout=10000)
            page.wait_for_timeout(1200)

            otp_count_after = otp_request_count["count"]
            if otp_count_after != otp_count_before:
                fail(results, "lock_prevents_otp", "Locked passport attempted OTP request; lock block did not hold.")

            modal_visible = page.locator("#gp-disconnect-modal").evaluate(
                "el => !el.classList.contains('hidden')"
            )
            if modal_visible:
                fail(results, "lock_modal_block", "Disconnect modal opened for locked passport, expected lock message only.")

            lock_badge_count = page.locator("text=Locked").count()
            if lock_badge_count < 1:
                fail(results, "lock_state_badge", "Lock state badge was not visible on connected card.")

            results["checks"]["lock_cooldown_flow"] = {
                "status": "passed",
                "message": "Locked passport blocked OTP request and modal opening, with lock state visible in UI.",
            }

            browser.close()

        all_passed = all(item.get("status") == "passed" for item in results["checks"].values())
        results["overall_status"] = "passed" if all_passed else "failed"
        results["finished_at"] = timezone.now().isoformat()

        print(json.dumps(results, indent=2))
        return 0 if all_passed else 2

    except Exception as exc:
        results["overall_status"] = "failed"
        results["error"] = f"[{current_step}] {str(exc) or repr(exc)}"
        results["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        print(json.dumps(results, indent=2))
        return 1

    finally:
        if httpd is not None:
            httpd.shutdown()
            httpd.server_close()
        if server_thread is not None and server_thread.is_alive():
            server_thread.join(timeout=5)


if __name__ == "__main__":
    sys.exit(main())
