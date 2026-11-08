"""Read-only public-journey regression check (Playwright). No login, no form submission, no state change.

  python scripts/regression_public_journeys.py [--base https://ownlobby.com]

Checks, desktop and mobile: public pages render (HTTP 200, a heading, no horizontal overflow on mobile, no
broken images, no 4xx/5xx sub-requests), key links navigate, auth entry points exist and protected routes
redirect anonymous visitors to the login page. Exit code 1 when any check fails.
"""
import argparse
import re
import sys

from playwright.sync_api import sync_playwright

PUBLIC = ["/", "/tournaments/", "/teams/", "/community/", "/shop/", "/arena/", "/accounts/login/"]
PROTECTED = ["/me/settings/", "/notifications/", "/teams/create/", "/tournaments/create/"]
DEVICES = {
    "desktop": dict(viewport={"width": 1366, "height": 800}),
    "mobile": dict(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True),
}
BROKEN = "() => [...document.images].filter(i => i.complete && i.naturalWidth === 0 && i.currentSrc && !i.currentSrc.startsWith('data:')).map(i => i.currentSrc.slice(0, 100))"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://ownlobby.com")
    base = ap.parse_args().base.rstrip("/")
    failures, rows = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for dev, opts in DEVICES.items():
            for path in PUBLIC:
                ctx = browser.new_context(**opts)
                page = ctx.new_page()
                bad, errors = [], []
                page.on("response", lambda r: bad.append(f"{r.status} {r.url[:90]}") if r.status >= 400 and "gtag" not in r.url and "google" not in r.url else None)
                page.on("pageerror", lambda e: errors.append(str(e)[:100]))
                try:
                    resp = page.goto(base + path, wait_until="load", timeout=60000)
                    page.wait_for_timeout(1200)
                    status = resp.status if resp else 0
                    heading = page.locator("h1, h2").count()
                    overflow = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
                    broken = page.evaluate(BROKEN)
                except Exception as exc:
                    status, heading, overflow, broken = 0, 0, 0, [f"load failed: {type(exc).__name__}"]
                problems = []
                if status != 200:
                    problems.append(f"status {status}")
                if not heading:
                    problems.append("no heading")
                if dev == "mobile" and overflow > 8:
                    problems.append(f"horizontal overflow {overflow}px")
                if broken:
                    problems.append(f"{len(broken)} broken image(s) e.g. {broken[0]}")
                if bad:
                    problems.append(f"{len(bad)} failed request(s) e.g. {bad[0]}")
                if errors:
                    problems.append(f"{len(errors)} JS error(s) e.g. {errors[0]}")
                rows.append((dev, path, "OK" if not problems else "; ".join(problems)))
                if problems:
                    failures.append((dev, path, problems))
                ctx.close()
        # anonymous access restrictions: protected pages must send visitors to login, never render
        ctx = browser.new_context(**DEVICES["desktop"])
        page = ctx.new_page()
        for path in PROTECTED:
            resp = page.goto(base + path, wait_until="domcontentloaded", timeout=60000)
            final = page.url
            ok = bool(re.search(r"login|signin|accounts", final)) or (resp and resp.status in (401, 403, 404))
            rows.append(("anon", path, "OK (redirected/denied)" if ok else f"NOT PROTECTED: {final}"))
            if not ok:
                failures.append(("anon", path, ["protected page rendered for an anonymous visitor"]))
        # navigation: follow the first tournament and team link from their list pages
        for listing, pattern in (("/tournaments/", r'href="(/tournaments/[a-z0-9][\w-]*/)"'), ("/teams/", r'href="(/teams/[a-z0-9][\w-]*/)"')):
            page.goto(base + listing, wait_until="domcontentloaded", timeout=60000)
            links = [m for m in re.findall(pattern, page.content()) if not m.endswith(("/create/", "/mine/")) and m != listing]
            if not links:
                rows.append(("nav", listing, "no detail links found"))
                failures.append(("nav", listing, ["no detail links"]))
                continue
            resp = page.goto(base + links[0], wait_until="load", timeout=60000)
            ok = resp and resp.status == 200 and page.locator("h1, h2").count() > 0
            rows.append(("nav", links[0], "OK" if ok else f"status {resp.status if resp else 0}"))
            if not ok:
                failures.append(("nav", links[0], ["detail page did not render"]))
        ctx.close()
        browser.close()
    for dev, path, result in rows:
        print(f"{dev:8} {path:36} {result}")
    print(f"\n{len(rows) - len(failures)}/{len(rows)} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
