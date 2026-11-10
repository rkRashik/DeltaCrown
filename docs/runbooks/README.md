# Runbooks

Procedures for features that are implemented but switched off, or that need owner approval. None of them authorizes a production action by itself; each step that changes production needs explicit owner approval and a rollback target.

| Runbook | Scope |
|---|---|
| [signing-key-rotation.md](signing-key-rotation.md) | Rotating `DJANGO_SECRET_KEY` and the OAuth field-encryption key |
| [public-image-derivatives.md](public-image-derivatives.md) | Resized WebP variants of public images (flag off) |
| [public-cdn-delivery.md](public-cdn-delivery.md) | Cloudinary delivery of reviewed public artwork (flag off) |
| [media-origin-governor.md](media-origin-governor.md) | Admission control for media origin reads |

Release, rollback and environment checks: [deployment.md](../deployment.md). Backups: [deployment.md](../deployment.md#resource-limits-and-operations-notes).
