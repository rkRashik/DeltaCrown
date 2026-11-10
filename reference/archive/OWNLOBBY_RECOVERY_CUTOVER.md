# OwnLobby recovery/cutover instructions

Status: STAGED ONLY. No certified rollback yet. Never restore public access to sensitive Cloudinary sources to recover old code.

## Baseline
- Historical live SHA: 903103708b1c85dec86a6d098019ea03f39b3790. NOT a safe post-containment rollback.
- Owned release branch: feature/ownlobby-free-hosting. Record exact new head before release.
- Existing Render Free service, manual deploy, Auto-Deploy OFF, start: bash start.sh; build: bash render_build.sh.
- 111 restricted Cloudinary sources and 2 approved public exclusions; 60 embedded avatars; 11 legacy raw /media/ paths.

## Before release
1. Confirm current live SHA, non-secret environment settings and separate recovery operator. Never copy secrets to GitHub.
2. Run python scripts/ownlobby_cloudinary_containment.py for read-only provider identity preflight on local machine. Compare to encrypted evidence and verify all sources unchanged.
3. Develop/test a media-compatible recovery code/configuration based on the hybrid storage paths. Old production SHA is not media compatible after containment. If none is proven, prepare an explicitly approved access restriction mechanism. This document itself is not rollback proof.
4. Ensure Supabase storage, CDN deny strategy, authorized and anonymous media delivery, runtime and worker dependencies can all be validated within the coordinated window.
5. Redis worker remains off until real broker routing and backlog are verified; no silent task loss. Free instance full container peak target <=448MB.
6. Obtain owner approval for the exact changes and the release window before executing any live mutation, GitHub promotion or Render deploy.

## Live change and recovery rules
- Protect 111 original sources with authenticated delivery and invalidation only within coordinated hybrid deployment; exclude two deliberately public sources.
- CDN invalidate=true requests are not proofs of protection. Verify anonymous GET+HEAD denial for original, versioned, transformed and embedded old URLs after propagation, plus all 11 raw local legacy paths.
- No false MEDIA_*_VERIFIED flags, no disabling REQUIRE_PERSISTENT_MEDIA or safety checks.
- If a source mutation fails, stop immediately, record count and reconcile partial provider state. Do not retry the whole list blindly.
- If new code fails after source containment, keep media private and use a separately reviewed compatible recovery version OR restrict access while repairing. Do not redeploy historic SHA as recovery.
- If Celery worker does not fit memory, hold public launch; temporarily disabling worker is operational containment, not full feature recovery.
- Never restore production database, delete provider objects or publish sensitive assets to achieve rollback.

## Commands
- Read-only metadata preflight: python scripts/ownlobby_cloudinary_containment.py
- Danger: live --apply option exists in script but must NOT run until coordinated cutover, provider CDN denial plan and compatible recovery/access containment are approved.

## Live acceptance
- Build and process startup, session/CSRF/password login, private file GET/HEAD and denial, public org art, avatar snapshots, payment/dispute evidence, WebSockets, actual SMTP email, OAuth, tournament bracket and Celery consumer probe, memory peak and Redis backlog.
- Keep public promotion off until critical canary checks pass.