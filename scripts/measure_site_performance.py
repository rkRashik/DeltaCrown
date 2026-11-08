"""Bounded, anonymous, read-only page-performance probe (desktop + mobile, cold + warm) using Playwright.

  python scripts/measure_site_performance.py [--base https://ownlobby.com] [--out report.json] [--paths /,/teams/]

Per page and device: TTFB, LCP, request count, transferred bytes (CDP encodedDataLength), failed requests, broken
images and console errors. "cold" = fresh browser context (empty HTTP cache); "warm" = same context, reload.
Only GET navigations of public pages; no login, no forms, no concurrency. Run sparingly against production.
"""
import argparse
import json
import re
import sys
import time

from playwright.sync_api import sync_playwright

LCP_JS = """() => new Promise(resolve => {
  let v = 0; const po = new PerformanceObserver(l => { for (const e of l.getEntries()) v = e.startTime; });
  po.observe({type: 'largest-contentful-paint', buffered: true});
  setTimeout(() => resolve(Math.round(v)), 1500);
})"""
NAV_JS = "() => { const n = performance.getEntriesByType('navigation')[0]; return {ttfb: Math.round(n.responseStart), dcl: Math.round(n.domContentLoadedEventEnd), load: Math.round(n.loadEventEnd)}; }"
BROKEN_JS = "() => [...document.images].filter(i => i.complete && i.naturalWidth === 0 && i.currentSrc).map(i => i.currentSrc.slice(0, 120))"

DEVICES = {
    "desktop": dict(viewport={"width": 1366, "height": 800}),
    "mobile": dict(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True,
                   user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"),
}


def load(page, cdp, url, stats):
    stats.update(req=0, bytes=0, failed=[], big=[], statuses={})
    sizes = {}

    def on_response(r):
        stats["req"] += 1
        stats["statuses"][r.status] = stats["statuses"].get(r.status, 0) + 1
        if r.status >= 400:
            stats["failed"].append(f"{r.status} {r.url[:110]}")

    def on_finished(e):
        sizes[e["requestId"]] = e["encodedDataLength"]

    page.on("response", on_response)
    cdp.on("Network.loadingFinished", on_finished)
    t = time.time()
    try:
        page.goto(url, wait_until="load", timeout=60000)
    except Exception as exc:  # timeouts are results too
        stats["error"] = type(exc).__name__
    stats["wall_ms"] = round((time.time() - t) * 1000)
    out = {}
    try:
        out["lcp"] = page.evaluate(LCP_JS)
        out.update(page.evaluate(NAV_JS))
        out["broken_images"] = page.evaluate(BROKEN_JS)
    except Exception:
        pass
    page.remove_listener("response", on_response)
    stats["bytes"] = sum(sizes.values())
    return {**out, "requests": stats["req"], "kb": round(stats["bytes"] / 1024), "failed": stats["failed"][:6], "statuses": stats["statuses"], "wall_ms": stats["wall_ms"], **({"error": stats["error"]} if "error" in stats else {})}


def discover(base, p):
    """First tournament / team / user links from list pages (public, anonymous)."""
    found = {}
    ctx = p.chromium.launch().new_context()
    page = ctx.new_page()
    for key, path, pattern in (("tournament", "/tournaments/", r'href="(/tournaments/[a-z0-9][\w-]*/)"'),
                               ("team", "/teams/", r'href="(/teams/[a-z0-9][\w-]*/)"'),
                               ("profile", "/", r'href="(/u/[\w.-]+/)"')):
        try:
            page.goto(base + path, wait_until="domcontentloaded", timeout=60000)
            skip = {"/tournaments/", "/teams/", "/tournaments/create/", "/teams/create/"}
            for m in re.findall(pattern, page.content()):
                if m not in skip and not m.endswith(("/create/", "/mine/")):
                    found[key] = m
                    break
        except Exception:
            pass
    ctx.close()
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://ownlobby.com")
    ap.add_argument("--out", default="")
    ap.add_argument("--paths", default="")
    ap.add_argument("--devices", default="desktop,mobile")
    a = ap.parse_args()
    base = a.base.rstrip("/")
    results = {}
    with sync_playwright() as p:
        if a.paths:
            paths = a.paths.split(",")
        else:
            paths = ["/", "/tournaments/", "/teams/", "/community/", "/crownstore/", "/competition/rankings/", "/arena/"]
            paths += list(discover(base, p).values())
        browser = p.chromium.launch()
        for dev in a.devices.split(","):
            for path in paths:
                ctx = browser.new_context(**DEVICES[dev])
                page = ctx.new_page()
                cdp = ctx.new_cdp_session(page)
                cdp.send("Network.enable")
                errors = []
                page.on("console", lambda m: errors.append(m.text[:100]) if m.type == "error" else None)
                cold = load(page, cdp, base + path, {})
                page.wait_for_timeout(500)
                warm = load(page, cdp, base + path, {})  # same context: HTTP cache is warm
                ctx.close()
                results[f"{dev} {path}"] = {"cold": cold, "warm": warm, "console_errors": errors[:3]}
                c, w = cold, warm
                print(f"{dev:7} {path:34} cold ttfb={c.get('ttfb')} lcp={c.get('lcp')} req={c.get('requests')} kb={c.get('kb')} "
                      f"broken={len(c.get('broken_images', []))} fail={len(c.get('failed', []))} | warm ttfb={w.get('ttfb')} "
                      f"lcp={w.get('lcp')} req={w.get('requests')} kb={w.get('kb')}", flush=True)
        browser.close()
    if a.out:
        json.dump(results, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    sys.exit(main())
