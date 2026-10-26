# OwnLobby repository audit

Audit date: 2026-10-26. Baseline feature/ownlobby-security-runtime at 8fc7c335f43709e91e64ea9dde8011c2a8ed26bd; all Phase 1-4 implementations verified as ancestors. Clean initial tree. Empty local checkpoint **97bd94d882e42edb9ab0dfab87b6d27a69231c2a**; cleanup branch feature/ownlobby-repository-cleanup. No push, merge, deployment, infrastructure or production-data action.

## Scope and inventory method

Git tracked, non-ignored untracked and ignored paths were enumerated separately. Initial counts: **3,223 tracked; zero untracked; 152,404 ignored files**. Counts include caches/environments and represent this workspace, not the size of a Git clone. Ignored content was inspected through metadata, not treated as disposable. Private media contents were not opened, decoded, hashed or exported. Final local fingerprint comparison confirms that all 26 protected Documents/DELTACROWN files retain their original paths, sizes and bytes.

The [sanitized machine inventory](reference/repository-inventory.json) includes category counts, all 52 nonempty tracked duplicate groups, exact candidate paths, tracked document classifications and legacy-reference counts. Raw ignored filenames and protected document fingerprints remain local in Artifacts/repository-cleanup. No private file list or credential value is committed.

| Tracked group | Files | Bytes at audit start |
|---|---:|---:|
| `.github` | 4 | 16192 |
| `Documents` | 1 | 39391 |
| `[root]` | 43 | 654604 |
| `apps` | 1688 | 18051926 |
| `bin` | 2 | 3987 |
| `branding` | 10 | 1503022 |
| `ci` | 1 | 3528 |
| `common` | 4 | 12574 |
| `config` | 1 | 7678 |
| `deltacrown` | 31 | 248097 |
| `frontend_sdk` | 10 | 108654 |
| `grafana` | 4 | 47877 |
| `migrations` | 2 | 2821 |
| `migrations_new` | 1 | 738 |
| `ops` | 3 | 5964 |
| `scripts` | 30 | 197687 |
| `static` | 629 | 125740197 |
| `synthetics` | 1 | 4010 |
| `templates` | 425 | 10529438 |
| `tests` | 327 | 4158165 |
| `tools` | 2 | 9863 |
| `vendor` | 4 | 3218031 |

## Classification of the actual workspace

| Category | Paths/evidence | Decision |
|---|---|---|
| Production code | apps/, deltacrown/, common/; configuration-driven services, app ready hooks, imports and routing | KEEP; common and apps/common are distinct compatibility/event utilities, not interchangeable copies. |
| Development tools | scripts/, tools/, bin/, root launcher/manual probe | KEEP/review by purpose. Manual Riot probe had import-time requests and is now guarded; explicit manual execution remains live-provider work and was not run. |
| Automated tests | tests/, app tests, synthetics/ | PROTECTED regression coverage; no test removed. New repository-safety tests added. |
| Required assets | static/, app static, 69 approved OwnLobby files | KEEP; approved copies intentionally duplicate bytes for different roles. Persisted/static paths prevent blind deduplication. |
| Uploaded/generated media | ignored media/: 28,745 files, 228,531,418 bytes; many PDFs/images | PROTECTED/NEEDS OWNER REVIEW. Generation versus genuine evidence cannot be inferred from extension/count. No file touched. |
| Deployment/config | Dockerfile, render.yaml/build/start scripts, requirements, package lock, config/, CI policy, Grafana | KEEP; runtime/production branch safety is not established by source alone. No settings/dependency/domain changes here. |
| Active docs | README and bounded existing OwnLobby release/security/domain/storage reports | KEEP/CONSOLIDATE navigation; stable paths remain. |
| Historical engineering | README_TECHNICAL.md, AuditReport.md, prior phase reports, .github/MODULE_3.1_PR.md | ARCHIVE CANDIDATE, retained in place with current-status pointers where useful. |
| Owner planning/designs | Documents/ (435 tracked+ignored files), docs/ (85 ignored Markdown), templates/My drafts/ | PROTECTED; no delete/move/rename. Drafts may contain unique future feature decisions despite duplicate HTML. |
| Temporary evidence | Artifacts/: 81,110 initial files/~2.24 GB, reports/, logs/, local synthetic sessions/TLS/test DB | KEEP until per-run recovery/evidence review; no wholesale disk cleanup. New cleanup evidence is separate. |
| Generated output | node_modules/, staticfiles/; tracked static/dist and static/community/build | Ignored caches are future review candidates only. Tracked CSS/JS outputs are deployment-required and retained. |
| Exact tracked duplicates | 52 nonempty groups; package markers, art aliases, drafts, templates, one standalone backup JS | Only 8,406-byte duplicate backup removed after real static-resolution/hash verification; 51 groups retained. |
| Obsolete-looking code | migrations_new/add_is_passport_supported.py; legacy app modules/routes/JS/templates | NEEDS OWNER REVIEW. Migration sketch has placeholder dependency; do not execute or delete as routine cleanup. Old app labels/migrations/feature contracts may remain necessary. |
| Sensitive/local-only | .env, populated ignored .env.example, local DB/media/evidence, tool configs | PROTECTED local files. New blank config/development.env.example is the supported setup source; no credential rotation or local-file rewrite. |

Tracked document-like extensions: 52 Markdown and 11 text files. These counts include runtime email/robots templates and dependency requirements, which are not prose to archive. No tracked PDF/Word document was found in that extension inventory. Ignored Documents primarily contains Markdown/TypeScript/design material plus an archive; uploaded media PDFs are not assumed to be documentation. Filename metadata alone cannot establish disposability.

## Reference and dependency analysis

Reviewed Django settings/app/static discovery, URL modules, app ready/signal/event registration, ASGI routing, Celery autodiscovery, build scripts, template/static includes, admin Media and relevant tests. Dynamic imports and feature flags mean no-import grep is not deletion proof. Current compiled community outputs are emitted by scripts/build-community.cjs and consumed by templates; schema.yml and frontend_sdk are contract tooling, not throwaway outputs. SQL/index scripts in migrations/ and tests/perf are schema references, not database dumps.

The removed file apps/user_profile/static_backup_20251231/admin/admin_game_passport.js was the sole tracked file in that backup directory, byte-identical to apps/user_profile/static/admin/admin_game_passport.js. The real Django finder resolves admin/admin_game_passport.js to the active path; ModelAdmin.Media references that canonical name. No tracked source referenced the backup directory. No ignored backup or containing directory was deleted. Full hash and recovery command are in the manifest/machine inventory.

Other duplicate groups cannot be safely collapsed yet: logo/game-art URLs may be stored in DB records; named static paths/aliases and template includes may differ; verification_sent/verify_email templates have distinct route roles; __init__.py duplicates establish separate namespaces; draft copies are owner planning. Approved brand variants are immutable even when identical.

## Legacy naming

The machine inventory records 702 tracked files with legacy-name matches by category. It stores counts/paths, not potentially sensitive matching lines. No blind replacement occurred. Technical project/app/table/migration/API/currency/infrastructure names, old-domain compatibility, histories, source artwork and audit provenance remain intentional.

Safe display edits are the engineering README, historical-reference titles and the launcher display title. The launcher still uses deltacrown commands; its process/network behavior was not redesigned. The GitHub repository name, Render hostname, Supabase ref, stored records and THE_CROWN are unchanged. Legacy public artwork is retained pending a complete licensed/persisted-path review rather than renamed to suggest it is approved OwnLobby artwork.

## Documentation findings

The old README is product direction with incomplete setup and historical contact/license claims. It is preserved verbatim in reference/README_PRODUCT_HISTORY.md with Git checkpoint provenance; the new README supplies verified setup, safety boundaries and navigation. Current report paths remain intact. Technical/ops/audit references now identify their historical status; old Makefile/test-compose commands in ops notes refer to absent files and are not current setup instructions.

Historical documentation has missing or workspace-only links (especially ignored docs/ and Documents paths). They are reported separately, not repaired by inventing specs or publishing owner collections. Active entry points must resolve to tracked targets and valid headings. An offline checker and explicit repository policy make that distinction reproducible.

The previous hygiene script applied a tiny whitelist to all local root files, suggested ignored docs/ destinations and recommended deleting DB-looking files. It is replaced by tracked/non-ignored placement review with no destructive actions; ignored owner material remains visible in this audit. Force-tracked environment/database files still fail. This is policy correction, not concealment of release blockers.

## Remaining risks and owner decisions

No root runtime package, application, migration, template, game asset, upload, security fixture, storage helper or approved brand file was reorganized. Keep the protected owner tree unchanged. Review only the explicitly deferred manifest items if further cleanup is desired; no broad deletion approval is inferred.

The ignored .env.example contains a provider-key-shaped value. It was inadvertently displayed while reading what appeared to be a setup template; no value is reproduced in these reports. Treat it as sensitive and assess privately whether it is real/active before any later coordinated sharing. It was neither tested nor rotated. A tracked placeholder-only replacement avoids repeating the problem. Repository licensing metadata also conflicts; owner clarification is required before redistribution, not an invented license change.

Cleanup does not resolve Linux/native Cairo, private media/persistence, backup restoration or successful provider/mail/worker staging gates. The complete storage implementation remains separately approved work. Production cutover remains No-Go.
