# OwnLobby rebranding implementation

## Safety and scope

Original branch: `master`. Clean-tree checkpoint: `8270018c536df41dcd869c3f4412c3c62a1d685b`. Implementation branch: `feature/ownlobby-rebrand`.

No deployment, DNS, provider, secrets, production database or payment changes are authorized by this implementation. Database names, Django project/app labels, model identifiers, URL names, API fields, wallet ledger/currency codes, stored tournament history and integration identifiers are retained.

## Architecture audit and implementation plan

The application uses Django with server-rendered templates, Tailwind (compiled CSS and existing CDN configuration), per-feature CSS/JavaScript, Channels WebSockets, Celery notifications and PostgreSQL models. Shared `templates/base.html`, `partials/primary_navigation.html`, `footer_modern.html`, `apps/common/seo.py` and context processors cover most pages. TOC, spectator and ecommerce also have independent shells. Accounts render multipart mail without request context. `apps/siteui/homepage_hero.py` already resolves real authenticated account activity; desktop/mobile homepage trees need identical progressive messaging.

1. Install the approved Arena Arch SVG/PNG masters, icons, social previews and Saffron Signal tokens unchanged. Read all supplied documentation including the four-page usage guide. Keep the full extracted kit under ignored local Artifacts for provenance.
2. Centralize identity in `deltacrown/branding.py`, backed by the official static JSON tokens; expose it with request context and request-independent email/template tags. Retain existing technical CSS names through compatibility tokens.
3. Migrate authored display copy in templates, SEO, mail and selected notification/presentation code. Do not rewrite stored content, app/model symbols, field names, form IDs, DOM contracts or routes.
4. Integrate dual-color SVG logo components and a quiet Deep/saffron visual layer across shared and standalone shells; preserve semantic status, publisher, team, payment and rank colors.
5. Present the universal homepage headline first; reveal one verified contextual headline without rotating links. Verify participant ownership, organizer ownership, fallback behavior and private response caching.
6. Prepare additive, environment-aware domain settings while keeping the old canonical origin and authenticated mail sender until a separately approved cutover.
7. Validate system checks, safe tests, templates, assets, settings contracts, JavaScript, responsive pages and logo colors. Record remaining references and production prerequisites.

## Initial findings

Baseline: 769 source files / 3,152 lines contain legacy references, including 244 templates. A file-by-file baseline is retained locally in `Artifacts/ownlobby/baseline-legacy.json`. Existing homepage pure tests: 94 passing. Baseline Django system checks: no errors, one existing `siteui.W001` persistent media-storage warning.

`The Crown` is the persisted `THE_CROWN` tier above Legend, with a 30,000-point threshold in the organizations and competition ranking services. Keep its label and code during this migration. Recommended future display name: **Apex**, retaining `THE_CROWN` as the compatibility code; this needs a separate approved terminology change, including filters, model choices, configurable thresholds, badges and historical labels. The dashboard currently claims 25,000 points for this tier; this pre-existing discrepancy needs a separate ranking review rather than a calculation change here.

The pre-existing homepage match probes select any active match in a registered tournament. Personalization must constrain both the tournament registration and the participant identity before surfacing a private action. The existing resolver also misses solo registrations when there is no team and has no organizer state. These are addressed within the specifically authorized homepage phase.

## Delivered implementation

`deltacrown/branding.py` centralizes identity, feature captions, typography, official asset paths and verified environment-specific destinations. The context processor, request-independent template tags and shared logo/head/email components reuse that identity. Official palette values are shared by Python, compiled Tailwind and the existing browser Tailwind configurations without changing their technical keys. Primary wordmarks remain supplied, dual-color artwork.

Sixty-nine approved SVG/PNG/icon/social files were integrated without altering their bytes. `branding/approved-assets.json` records source paths and hashes. The canonical token JSON preserves the kit's values; the local PWA manifest uses relative icon paths, scope and start URL. Shared and standalone application shells use the new favicons, metadata and visual layer. Auth, header/footer, teams/HQ, player profiles and settings, tournament creation/details/TOC, brackets/matches, community, competitive/ranking screens, wallet/store, administration and transactional emails received authored display changes. Future certificates and Discord formatting use the approved identity; existing generated documents/messages remain intact.

The visual integration uses Deep surfaces, restrained saffron, quieter navigation/cards and reduced-motion support. It retains team/game/status colors and existing DOM selectors. The settings page received branding and scoped surface changes only; its form, tab, AJAX and passport contracts remain intact. Existing newsletter behavior is retained and its limitation is documented.

The homepage renders the universal three-line message in the initial HTML for everyone. One progressive transition reveals context from real registration, match, team or organizer ownership. Actions remain available immediately. Participation-type checks prevent numeric team/user ID collisions and unrelated match disclosure; private homepage responses are not shared-cacheable. Static invented fallback statistics, timeline and countdown dates were removed. Public cached content and stored historical content were not globally rewritten.

Display terminology is OwnLobby, Coins, Ranking Points, Team Rank where appropriate, Competitive Hub and Store. Game Passport, Team HQ, Showdown, Missions, Bounty, Dropzone and Match Rooms are preserved. `The Crown` remains pending the separate highest-tier decision above.

The existing community JSX entry points lacked their compiled scripts. A pinned esbuild development dependency and explicit community build step now produce those same paths; the deployment build invokes the combined frontend build. Existing runtime global names and script ordering are retained.

## Preserved contracts

Django project/app labels, package names, database tables/models/fields, migration files, URLs and route names, authentication and provider identifiers, API field/currency values, wallet arithmetic and ledger history, tournament/player IDs and stored historical achievements remain compatible. Existing old-domain host support, verified mail sender and external social destinations remain defaults. The webhook User-Agent and calendar PRODID retain their established integration identities. No destructive migrations, new financial capabilities, DNS changes, provider operations, push or deployment were performed.

## Validation and rollout

See `OWNLOBBY_VALIDATION.md` for actual results, baseline reproductions and representative screenshots; `OWNLOBBY_DOMAIN_MIGRATION.md` for deployment order, provider callbacks, DNS/TLS, mail, sessions, redirects and rollback; and `branding/legacy-references.json` for the classified remaining source references. Automated local rebrand verification reports no new failures. Existing release issues and external migration tasks remain, so this work is not a production-readiness declaration.

## Git record

- Original branch: `master`.
- Mandatory checkpoint: `8270018c536df41dcd869c3f4412c3c62a1d685b` (empty commit from a clean tree).
- Implementation branch: `feature/ownlobby-rebrand`.
- Implementation commit: the commit introducing this completed report, titled `feat: implement OwnLobby brand identity across platform`; its SHA is supplied in the final handoff. A commit cannot contain its own SHA without changing that SHA.

## Owner actions

Review the local implementation and release limitations. Approve any production deployment separately. Arrange registrar/hosting/TLS changes, provider callback changes, verified sender/support and social destinations with their account owners when scheduling cutover. Confirm the proposed future Apex tier label separately if desired; this implementation does not depend on that decision.
