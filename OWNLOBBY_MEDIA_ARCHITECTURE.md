# OwnLobby media architecture and Phase 5 implementation plan

> Implementation update: [final engineering handoff](OWNLOBBY_FINAL_ENGINEERING_HANDOFF.md). The inventory and proposed plan below are historical audit evidence. Current opt-in code integrates all 53 concrete fields, separate public/private aliases and record-authorized streaming; both origins remain private. No provider has been selected or verified, and no production file/reference was migrated. Follow the new handoff for actual settings, backfill and rollback commands.


Audit: 2026-10-26, local source/schema only. **No provider selected/configured, bucket purchased, production object read, media copied or database record changed.** The storage/privacy/recovery release gate remains open. Proposed classifications require product/privacy approval where conditional; they are not assertions that current raw URLs are protected.

## Complete model inventory

There are **55 registered file/image fields, representing 53 concrete fields**. The two aliases are organizations.TeamAdminProxy.logo/banner; they share organizations.Team columns and objects. Every registered field currently uses **default storage**; none declares a private per-field backend. Registry and source searches agree; serializers/forms and documentation examples are not extra persisted fields. URLField/JSON references to externally hosted videos/proof links are additional uncontrolled external content, not durable FileField uploads.

[Machine inventory](branding/media-storage-inventory.json) records each source, upload callable/prefix, validator, concrete model, proxy alias, storage and proposed authorization. It was produced without enumerating user records/files by:

```powershell
$env:DJANGO_SETTINGS_MODULE='deltacrown.settings_brand_qa'
# Supply only loopback DATABASE_URL and DATABASE_URL_TEST=.../ownlobby_test.
python scripts/inventory_media.py --output branding/media-storage-inventory.json
```

All rows below use settings.STORAGES['default']. In production source this selects MediaCloudinaryStorage when CLOUDINARY_URL exists, otherwise FileSystemStorage under MEDIA_ROOT. Actual dashboard configuration, Cloudinary delivery type, object ACLs and retained objects were not inspected. Local QA intentionally uses filesystem storage.

| Model.field | Proposed policy | Upload prefix/callable | Declared validators |
|---|---|---|---|
| `games.Game.icon` | public-intended | `games/icons/` | validate_image_upload |
| `games.Game.logo` | public-intended | `games/logos/` | validate_image_upload |
| `games.Game.banner` | public-intended | `games/banners/` | validate_image_upload |
| `games.Game.card_image` | public-intended | `games/cards/` | validate_image_upload |
| `games.GameMapPool.image` | public-intended | `games/maps/` | none declared |
| `organizations.Organization.logo` | public-intended | `organizations/logos/` | validate_image_upload |
| `organizations.Organization.badge` | public-intended | `organizations/badges/` | validate_image_upload |
| `organizations.Organization.banner` | public-intended | `organizations/banners/` | validate_image_upload |
| `organizations.Team.logo` | public-intended | `teams/logos/` | validate_image_upload |
| `organizations.Team.banner` | public-intended | `teams/banners/` | validate_image_upload |
| `organizations.TeamMembership.roster_image` | conditional-private | `roster_photos/` | validate_image_upload |
| `organizations.TeamMedia.file` | conditional-private | `teams/gallery/` | validate_document_upload |
| `tournaments.Tournament.banner_image` | public-intended | `tournaments/banners/` | validate_image_upload |
| `tournaments.Tournament.thumbnail_image` | public-intended | `tournaments/thumbnails/` | validate_image_upload |
| `tournaments.Tournament.rules_pdf` | conditional-public | `tournaments/rules/` | validate_document_upload |
| `tournaments.Tournament.terms_pdf` | conditional-public | `tournaments/terms/` | validate_document_upload |
| `tournaments.Payment.payment_proof` | private | `payment_proofs/%Y/%m/` | none declared |
| `tournaments.Payment.proof_image` | private | `payments/proofs/` | none declared |
| `tournaments.PaymentVerification.proof_image` | private | `payments/proofs/` | validate_payment_proof_upload |
| `tournaments.DisputeEvidence.evidence_file` | private | `apps.tournaments.models.dispute._dispute_evidence_upload_to` | FileExtensionValidator |
| `tournaments.Certificate.file_pdf` | conditional-private | `certificates/pdf/%Y/%m/` | validate_document_upload |
| `tournaments.Certificate.file_image` | conditional-private | `certificates/images/%Y/%m/` | validate_image_upload |
| `tournaments.MatchResultSubmission.proof_screenshot` | private | `apps.tournaments.models.result_submission._proof_screenshot_upload_to` | FileExtensionValidator |
| `tournaments.RegistrationFormTemplate.thumbnail` | public-intended | `form_templates/thumbnails/` | validate_image_upload |
| `tournaments.FormResponse.payment_proof` | private | `registration_payments/` | validate_payment_proof_upload |
| `tournaments.TournamentSponsor.logo` | public-intended | `tournaments/sponsors/` | none declared |
| `tournaments.TournamentSponsor.banner_image` | public-intended | `tournaments/sponsors/banners/` | none declared |
| `tournaments.KYCSubmission.document_front` | private | `kyc/documents/` | none declared |
| `tournaments.KYCSubmission.document_back` | private | `kyc/documents/` | none declared |
| `tournaments.KYCSubmission.selfie_image` | private | `kyc/selfies/` | none declared |
| `tournaments.MatchMedia.file` | conditional-private | `match_media/` | none declared |
| `tournaments.CertificateRecord.generated_pdf` | conditional-private | `certificates/` | none declared |
| `user_profile.UserProfile.avatar` | public-intended | `apps.user_profile.models_main.user_avatar_path` | validate_image_upload |
| `user_profile.UserProfile.banner` | public-intended | `apps.user_profile.models_main.user_banner_path` | validate_image_upload |
| `user_profile.VerificationRecord.id_document_front` | private | `apps.user_profile.models_main.verification_kyc_document_path` | validate_image_upload |
| `user_profile.VerificationRecord.id_document_back` | private | `apps.user_profile.models_main.verification_kyc_document_path` | validate_image_upload |
| `user_profile.VerificationRecord.selfie_with_id` | private | `apps.user_profile.models_main.verification_kyc_document_path` | validate_image_upload |
| `user_profile.GameProfile.rank_image` | public-intended | `rank_images/` | validate_image_upload |
| `user_profile.Certificate.image` | conditional-private | `certificates/` | validate_image_upload |
| `user_profile.KYCSubmission.document_front` | private | `apps.user_profile.models_main.kyc_document_path` | validate_image_upload |
| `user_profile.KYCSubmission.document_back` | private | `apps.user_profile.models_main.kyc_document_path` | validate_image_upload |
| `user_profile.KYCSubmission.selfie_with_document` | private | `apps.user_profile.models_main.kyc_document_path` | validate_image_upload |
| `ecommerce.Category.image` | public-intended | `categories/` | validate_image_upload |
| `ecommerce.Brand.logo` | public-intended | `brands/` | validate_image_upload |
| `ecommerce.Product.featured_image` | public-intended | `products/` | validate_image_upload |
| `ecommerce.Product.hover_image` | public-intended | `products/` | validate_image_upload |
| `ecommerce.ProductImage.image` | public-intended | `products/` | validate_image_upload |
| `economy.InventoryItem.icon` | public-intended | `inventory/items/` | validate_image_upload |
| `siteui.ArenaHighlight.custom_thumbnail` | public-intended | `arena/highlights/%Y/%m/%d/` | validate_image_upload |
| `siteui.ArenaStream.custom_thumbnail` | public-intended | `arena/streams/%Y/%m/%d/` | validate_image_upload |
| `siteui.CommunityPostMedia.file` | conditional-private | `community/posts/%Y/%m/%d/` | none declared |
| `siteui.CommunityPostMedia.thumbnail` | conditional-private | `community/thumbnails/%Y/%m/%d/` | validate_image_upload |
| `contracts.ContractProofSubmission.proof_file` | private | `apps.contracts.models._mission_proof_upload_to` | validate_payment_proof_upload |

Public-intended does not bypass draft/team/profile visibility. Conditional content should remain private until a deliberately reviewed publication path allows it. MatchMedia.is_evidence distinguishes evidence from other match media; it is not an object-storage ACL. Team gallery/roster content and community attachments inherit parent permissions. Certificates can carry personal data and should not become universally public simply because their prefix says certificates.

## Non-FileField uploads and external references

The active /ckeditor5/ image-upload route saves via django_ckeditor_5.storage_utils.handle_uploaded_file and returns a raw URL embedded in rich-text HTML. Its storage selection honors CKEDITOR_5_FILE_STORAGE, legacy DEFAULT_FILE_STORAGE, then the default STORAGES backend; instantiated backend options need explicit review. Upload permission is configured staff-only and the package invokes PIL verification. These bytes have no dedicated OwnLobby FileField row, so object/HTML reference discovery must supplement the 53-field backfill. Draft rich text can still reference a public object. Include editor uploads, metadata/JSON URL references, generated temporary files and orphaned objects in the migration manifest; do not assume a FileField-only iterator finds every blob.

## Real read/write/delete paths and gaps

| Area | Creation/read path and existing controls | Phase 5 obligation |
|---|---|---|
| Profile avatar/banner | user_profile/views/settings_api.py upload_media/remove_media_api: authenticated own profile, size checks, PIL image inspection, default_storage deletion, FieldFile URL response | Use the field's actual storage for deletion. Preserve old object until new save/DB commit succeeds; current delete-first replacement can lose the old asset on failure. Keep upload response keys and settings DOM/contracts. |
| Team/org artwork/gallery | organizations/api/views/team_manage.py profile_upload_media/community_upload_media, _check_manage_permissions; admin/forms/service paths also write fields | Existing direct team saves trust content_type and do not invoke model full_clean. Central validation must be invoked explicitly on every write; preserve supported gallery video workflows rather than applying a PDF-only validator blindly. |
| Tournaments/art/rules/terms | Tournament serializers, organizer/admin forms and services; public detail has draft/staff guards | Raw storage URL must not make a draft document public. Rules importer/preview now use FieldFile.open and no longer require local .path. |
| Payments/KYC | registration/form/TOC serializers/services, user_profile/views/kyc_views.py, admin previews; serializer/admin code emits field.url | Page/API authorization does not protect an already public object URL. Add protected file delivery for ALL KYC/payment fields, including the three distinct KYC/verification models. Do not expose these through global public Cloudinary delivery. |
| Mission/match/dispute evidence | dashboard/views.py competitive_*_file_view checks authenticated owner/participants/reviewer scope and uses FieldFile.open/FileResponse. contracts/views.py restricts reads to enrollment owner/staff | These guards are a useful starting point, but default-storage/raw URL access can bypass them. TOC, mobile serializers and templates still emit evidence .url. Inventory and replace alternate delivery paths with the same policy. |
| Community/ecommerce/game assets | siteui forms/models/upload handlers, ecommerce and game admin fields; community media has parent content relationships | Staff/editor or post-owner writes; enforce publication visibility, actual content checks and safe derivative delivery. Distinguish original user uploads from trusted approved brand SVGs. |
| Certificates | ReportLab/CairoSVG/svglib services save default-storage certificate fields. CertificateS3Storage and s3_protocol provide optional testable helpers, consistency tasks and a backfill command | No FileField declares CertificateS3Storage and get_certificate_storage has no active caller. CERT_S3_* switches are not a platform migration. Review actual wiring and proof of end-to-end use before enabling anything. |
| Deletion/retention | Explicit default_storage.delete exists for profile replacements; other fields use generic FieldFile/service/admin behavior | Django model deletion does not automatically clean every file. Add an authorized, transaction-aware deletion queue, reference checks, idempotency, retention/hold rules and failed-delete monitoring. Never recursively purge a prefix as a migration shortcut. |

Direct sensitive URLs were found in tournaments/api/toc/payments_service.py (_serialize_kyc), participants_service.py, tournaments/admin_registration.py, user_profile/admin/users.py and mobile_api/matches/serializers.py. competitive match-report templates also use evidence_file.url. These require a complete delivery-policy sweep in Phase 5, not merely replacing one template.

Filesystem risks also include user_profile/templatetags/user_avatar_tags.py checking MEDIA_ROOT with os.path.isfile and the certificate S3 helper's local shadow writes/fallback. Audit all os.path/MEDIA_ROOT/open references by purpose before conversion: request.path and URL path parsing are not storage calls. Generic FieldFile.open/save/delete are portable only if the configured backend supports the file type and permissions. Remote streaming may still buffer an object; bound sizes and close handles. User-supplied URLField evidence is not backed up merely because its URL is stored.

## Validation findings and safe prerequisites implemented

- Unknown bytes previously inherited the browser Content-Type; generic RIFF could be treated as WebP. Shared image/proof/document validators now fail closed for unknown data and recognize WebP only with its WEBP marker. Three regressions cover spoofed content, existing allowlists and pointer preservation. Valid format policy stays unchanged (configured documents PDF/JPEG/PNG; image policy also supports GIF/WebP).
- This is magic-signature/type validation, not antivirus, complete image decoding or proof of harmless PDF contents. Model save does not invoke validators automatically. Team gallery/KYC and other direct saves need explicit validation service integration. Sensitive KYC FileFields have no declared validators in several models. **P1 before public delivery.**
- Actual limits differ: profile avatar 5 MiB/banner 10 MiB, team artwork 5 MiB/gallery 10 MiB, KYC view 5 MiB, common proof validator 10 MiB, common document default 20 MiB. Common image validator reads MAX_IMAGE_UPLOAD_SIZE (absent, default 10 MiB), while settings MAX_UPLOAD_SIZE is 5 MiB. DATA_UPLOAD_MAX_MEMORY_SIZE=2.5 MiB is not a global uploaded-file cap. Agree consistent per-category limits; do not silently change product capacity in this audit.
- Phase 5 needs bounded decoded pixel/frame limits, decompression-bomb rejection, image re-encoding/metadata stripping, PDF validation/scanning/quarantine and explicit video policy. Do not host arbitrary active SVG/HTML uploads as public images. The 69 trusted brand assets are separate and unchanged.
- PDF rules import/preview now work with storage.open even when no .path exists; a real PDF regression uses an object that has no path attribute. No storage backend selection or schema migration was made.
- .dockerignore now excludes .env variants and local credential directories. Previously a COPY of the full Docker context could include local secrets; no image was built or deployed here. Ignored QA/media artifacts remain excluded.
- Development MediaProxyMiddleware can redirect missing files, including unknown prefixes, to a production origin/Cloudinary in DEBUG. It is disabled in guarded QA. Phase 5 should remove the implicit production fallback and allowlist public development fixtures; never use it to test private production media.

## Recommended architecture (pending owner selection)

Use **separate public and private object stores/buckets**, with explicit Django storage aliases and category-aware delivery. Prefer an S3-compatible implementation using the existing django-storages/boto3 stack. R2 Standard is a practical first choice for small public image delivery and private objects because it avoids Internet egress charges and fits current dependencies. If the existing Supabase plan already includes enough storage, evaluate that option before adding a second provider/account. Existing Cloudinary can remain for approved public image transformations if its actual account and quotas are verified; it should not become the default sink for all confidential documents.

Public bucket: only approved published artwork/derived images; controlled MIME and names, immutable cache keys and optional CDN. Private bucket: KYC/payment/dispute/mission originals, drafts and conditionally shared originals; never public access or public CDN fallback. Use opaque UUID keys without usernames/emails/IDs in new sensitive object names. Separate least-privilege read/write/backup credentials; no browser service-role key. All choices must work with Render web and workers without local-disk dependence.

Keep current protected Django download URLs for confidential content. Authorize the actual record and role on every issuance/read; unrelated organizer/team membership does not grant KYC access. Stream through FieldFile.open for strongest per-request checks, or explicitly approve short-lived presigned redirects (for example 60-300 seconds) for larger files. Presigned URLs are bearer capabilities reusable until expiry, not continuous Django authorization or one-time tokens. For highly sensitive KYC prefer the application proxy when immediate revocation matters. Add private/no-store, noindex, nosniff, appropriate Content-Disposition and no-referrer policies. Never persist/log signed URLs or put them in public sitemaps/OG data.

Do not reuse one public storage alias and attempt to infer privacy solely from a folder name. Publishing a private original must be an explicit checked copy/derivative operation; withdrawing publication must remove public derivatives and caches. Old public URLs need separate containment if confidential files were already publicly delivered. Live exposure remains **unverified/P0 conditional**, not assumed safe or assumed breached.

## Provider/cost comparison (verified public documentation, 2026-10-26)

| Option | Current published information | Fit/tradeoffs |
|---|---|---|
| Cloudflare R2 Standard | Free monthly allowance: 10 GB-month storage, 1M Class A and 10M Class B operations. Beyond allowance: storage $0.015/GB-month, Class A $4.50/M, Class B $0.36/M; Internet egress free. Allowances/rounding apply at account level, not per bucket. | Existing boto3/S3-compatible stack; separate public/private buckets; budget for requests, backups and extra services. Verify billing prerequisites and region/jurisdiction before purchase. [Pricing](https://developers.cloudflare.com/r2/pricing/), [presigned delivery](https://developers.cloudflare.com/r2/api/s3/presigned-urls/). |
| Existing Supabase Storage | Free lists 1 GB file storage and 5 GB each regular/cached egress; free projects pause after inactivity. Pro starts at $25/month and lists 100 GB file storage. Actual existing plan/remaining allowance unknown. | May avoid another provider; Django identities are not automatically Supabase Auth identities. Design signed-server access/RLS carefully; never expose a service-role key. [Pricing](https://supabase.com/pricing). |
| Cloudinary | Free image/video plan lists 25 monthly credits; credits are not a promise of 25 GB for each usage dimension. | Already integrated for public media, CDN/transforms useful; verify private/authenticated delivery entitlement, file-type restrictions and backup plan before confidential use. [Plans](https://cloudinary.com/pricing). |
| Render disk | Requires paid service; only the mount persists, accessible by one service instance, not other workers/builds; prevents normal horizontal scaling and zero-downtime deploy behavior. | Can support a small single-service installation but requires private-serving/backup design and complicates workers. Not the recommended long-term shared-media solution. No disk purchased. [Limitations](https://render.com/docs/disks). |

No actual usage, existing entitlement, exchange rate or recurring bill is invented. Budget in provider currency plus taxes/payment fees, backups, scanning and compute. Test Bangladesh latency with synthetic files after approval rather than assuming a provider region or CDN guarantees it. No external setup is needed to review this proposal.

## Phase 5 implementation sequence

1. Owner approves provider, public/private policy, file-size/type/video policy, retention/hold rules, budget and recovery objectives. Confirm actual live storage/ACLs and object counts in an approved audit; do not scrape raw private URLs.
2. Back up database metadata and all existing file stores to an independently recoverable encrypted location. Record secure object manifests/checksums and orphan/missing-reference reports. Do not copy production material into this local QA workspace.
3. Build named public/private backends and an authorized delivery service using existing dependencies. Default unknown categories to private. Preserve current API fields, model/app identities and file references; storage configuration is not a reason to rename database columns.
4. Add explicit validators to every write entry point, quarantine/scan originals, safe derivatives and bounds. Separate image/PDF/video handling without removing existing supported product features.
5. Replace sensitive .url output in web/mobile/admin/TOC serializers with protected application routes. Test owner/reviewer/participant boundaries and draft/publication cases. Keep signed URLs ephemeral.
6. Convert remaining filesystem-dependent rendering/lookup code. Exercise actual Linux Cairo/certificates and object streams with synthetic files before enabling the backend.
7. Create approved storage namespaces/credentials and enforce private access at the provider. Keep secrets in approved secret storage, not Git. Configure only necessary CORS/egress; never wildcard credentialed access.
8. Run dry-run backfill with record/category mapping and a manifest. Preserve old object names where safe; use an explicit old/new mapping for opaque private keys. Copy, verify bytes/metadata/ACL, then update a bounded record batch transactionally with checkpoints. No destructive schema migration or financial mutation.
9. Make jobs idempotent and resumable. Apply source-of-truth rules for concurrent uploads; write/read canaries first. A certificate-only flag cannot migrate all fields.
10. Validate canary read/write/delete, ownership denial, raw-object denial, expired signed access and restart/redeploy durability. Test both web and worker processes and old/new application domains.
11. Perform a restore drill into isolated storage/DB with synthetic fixtures or approved protected restored data. Measure agreed RPO/RTO; compare every referenced checksum and authorization policy. Verify evidence and wallet-record associations without financial operations.
12. After separate approval, switch storage reads/writes gradually. Preserve a compatibility reader and reversal manifest; monitor missing objects, 403/404, failures, latency and costs. Do not enable public fallback for private-read errors.
13. Quarantine/deny legacy public confidential objects and purge caches only through an approved containment plan. Keep rollback copies private. Rollback must not restore public KYC URLs.
14. After an approved observation/retention window, schedule audited orphan cleanup and old-store retirement. No deletion before verified independent backup and restore.

## Backup/restore requirements

Database backups do not contain uploaded object bytes; Supabase explicitly separates Storage objects from database backup coverage. Maintain independent media backups and a database-to-object manifest. [Backup scope](https://supabase.com/docs/guides/platform/backups).

Propose DB recovery point <=15 minutes, media <=1 hour and restore time <=4 hours for review; these are unachieved targets, require owner budget/policy approval, and may require paid PITR or more frequent backup infrastructure. Do not claim nightly dumps meet a 15-minute RPO. Keep immutable backup generations, encryption and restricted independent backup/delete credentials; do not assume every S3-compatible provider implements versioning/Object Lock. Protect encryption-key recovery separately and never rotate the existing application key as part of storage setup.

A restore drill must validate database IDs/permissions, object checksums, content types, private access, generated URLs and deleted/held records; restoring bytes with public ACLs is a failed recovery. Django/private-origin authorization must still apply after recovery. Record actual provider snapshot/PITR entitlements during the later approved infrastructure audit. Render restarts, local shadows and bucket replication alone are not independent tested backups.

## Acceptance and rollback gate

Phase 5 is complete only after all 53 fields have deliberate routing/visibility, all sensitive raw URLs are denied, approved public artwork remains accessible, all upload paths validate, rendering works on Linux, persistence survives restart, and backup restoration meets approved objectives. Keep names/IDs/ledger behavior stable.

Rollback restores reviewed application/storage configuration and manifest-backed record mappings; it does not delete new uploads or reset financial/user data. Preserve both stores privately until reconciliation finishes. No Phase 5 action or risk acceptance has been performed in Phase 4.
