# OwnLobby technical SEO and site migration

## Implemented architecture

`apps/common/seo.py` supplies identity defaults, absolute URLs, descriptions, JSON-LD and indexing rules. Existing public views supply actual tournament/team/profile/organization/ranking metadata. `partials/seo_meta.html` applies the request policy even for view-specific metadata. `SearchIndexingMiddleware` supplies noindex headers for sensitive routes, filtered requests and errors. All approved favicons, PWA icons and dual-color logo assets remain unchanged.

`SITE_URL` is the sole public canonical origin. It must be an absolute origin without credentials, path, query or fragment, and must use HTTPS in production. The production default is still `https://deltacrown.xyz`. Set `https://ownlobby.com` only at the approved canonical cutover. Request Host, forwarded Host and Django Sites cannot silently choose a different SEO origin.

## Canonicals and indexing policy

Public homepage, tournament details/listing, meaningful active public teams, authored public profiles, organization pages and populated ranking pages use their real routes. Organization-owned teams use their existing `/orgs/<org>/teams/<team>/` canonical path; independent teams use `/teams/<team>/`. Public profiles remain `/@<username>/`. Existing route names and IDs are unchanged.

Pagination retains a normalized positive `page` value greater than one in the self-canonical. Page one and tracking parameters canonicalize to the clean route. Repeated/malformed pagination and search/filter/sort/spectator views are noindexed. Query parameters are parsed, so URL encoding cannot bypass policy and tracking values containing `search=` are not mistaken for search keys. View-specific thin/private-content noindex decisions remain authoritative.

Account, admin, API, settings, dashboard, wallet, participant hub, match lobby, management, notification, private media and similar endpoints are excluded from indexing. Authentication/authorization enforce privacy; robots rules and metadata do not secure data. Draft/pending tournament access is restricted to existing organizer/staff permissions. Error responses carry noindex headers.

`PUBLIC_DOMAIN_REDIRECTS_ENABLED=0` remains the default. Prepared redirects require an explicit enabled flag, new apex canonical origin, an old-domain or new-www request, anonymous GET/HEAD, a successful public HTML response and no noindex indication. They preserve the path/query. POSTs, API/JSON, callbacks, private pages, authenticated sessions, WebSockets and errors do not participate. The Render service hostname is deliberately excluded for health monitoring and integration continuity. Redirect enablement is a separate production approval.

The narrow new-www exception is a successful anonymous login/signup/reset entry GET: it moves to apex before a form is submitted or OAuth state is initiated. Old-domain authentication entry points remain operational. Do not publish direct www provider-start links; callback and API routes are not blanket-redirected.

## Metadata and structured data

Titles/descriptions/OG/Twitter cards use existing actual view data and centralized OwnLobby fallbacks. The approved default OG image has declared 1200×630 dimensions; arbitrary user images are not assigned invented dimensions. Descriptions and values are escaped in HTML. JSON-LD escapes `<`, `>`, `&` and Unicode separators without changing parsed data, preventing authored text from terminating its script block.

Organization, WebSite and breadcrumbs use the configured origin. Existing SportsTeam/ProfilePage and SportsEvent data use actual public entities. Tournament attendance distinguishes online, LAN and hybrid; cancelled events are marked cancelled; completed/archived events are not claimed to be scheduled. Missing dates are omitted. No awards, reviews, ratings, prize amounts, user totals or event availability were invented. Rich-result eligibility is not guaranteed; validate representative public pages using Google's tools during staging/launch.

## Robots and sitemap

Active routes are `/robots.txt`, `/sitemap.xml` and `/sitemap-<section>.xml`; the old static template and `deltacrown/sitemaps.py` are not wired to these routes. Robots advertises the selected-origin sitemap and discourages crawling private endpoints. Do not block all old-domain crawling during migration: crawlers must observe redirects.

The sitemap index discovers paginated static/tournament/team/organization/profile/ranking sections. Dynamic content uses deterministic primary-key ordering, count queries and 1,000-record pages; it does not silently stop after 5,000 records. Exceptions are visible to monitoring instead of being returned as a successful empty sitemap. Unknown sections and invalid pages return 404. XML values are escaped.

Tournament entries exclude deleted, draft, pending, cancelled and archived records. Teams require ACTIVE/PUBLIC, non-temporary status and meaningful authored description/tagline. Organization entries conservatively require description. Profiles require active users, a PUBLIC preset, `is_private_account=False` and authored bio. This conservative subset can omit eligible pages without exposing private profiles. Ranking pages are included only with actual data. Lastmod comes from stored timestamps. No emails, contacts, evidence or private participant information are output. Sitemaps cache publicly for five minutes; new canonical deployment requires public cache refresh.

## URL mapping and launch checklist

| Existing public URL | New canonical URL |
| --- | --- |
| `https://deltacrown.xyz/` | `https://ownlobby.com/` |
| `/tournaments/` and `/tournaments/<slug>/` | Same paths on new apex |
| `/teams/<slug>/` | Same independent-team path on new apex |
| `/orgs/<org>/teams/<team>/` | Same organization-team path on new apex |
| `/@<username>/` | Same public-profile path on new apex |
| `/competition/leaderboards/` and actual game-ranking routes | Same paths on new apex |
| Public legal/community pages | Same existing paths; preserve meaningful pagination |
| API, auth callbacks, webhooks, POSTs, private pages, WebSockets | Separate integration migration; no blanket redirect |

1. Inventory current indexable URLs, aliases and top landing pages from Search Console/server logs without exporting private data. Confirm each target returns the intended public content and canonical, and broken/deleted content returns a real 404/410 rather than redirecting everything home.
2. Verify ownership of old and new Search Console properties with the account owner. A DNS domain-property verification TXT is distinct from app DNS and mail records. Keep existing ownership methods working; no verification token is stored here.
3. Validate new TLS/routing, anonymous metadata, JSON-LD, robots, sitemap sections, old/new exact URL samples and new-www behavior before canonical switching. Staging must be private and use a crawler noindex policy without weakening application authentication.
4. At approved cutover change `SITE_URL`, refresh public caches, submit the new sitemap and update genuinely hardcoded internal public links. Relative links already follow the current host. Keep old-domain providers/inbound callbacks working.
5. After approved redirects are verified, use Google's Change of Address tool if eligible for the old-to-new domain move. The submitting account must own the appropriate old/new properties; follow the tool's exact variant/property checks. Do not use it merely for an HTTP-to-HTTPS change.
6. Monitor Search Console indexing/canonical choices, sitemap fetches, crawl errors and query performance, plus app 404/5xx, redirects, latency, TLS and broken links. Inspect immediately after release, daily during the first week and weekly thereafter. Maintain old-domain ownership and working redirects for at least a year, preferably longer.

These procedures follow [Google's site-move guidance](https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes) and [Change of Address requirements](https://support.google.com/webmasters/answer/9370220). Ranking or migration timing is not promised.

## Performance and residual work

Locked Tailwind/community builds and fail-visible hashed static processing now work. Logos have intrinsic dimensions; the homepage retains zero-shift one-time personalization and reduced-motion support. CDN Tailwind, fonts/icons and feature scripts remain a performance risk requiring measured feature coverage before removal. No production Lighthouse/Core Web Vitals, load test or ranking guarantee is claimed. See the readiness report for dependency, optional-template and storage limitations.
