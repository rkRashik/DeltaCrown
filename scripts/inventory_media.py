"""Inventory model upload declarations, never user records or object contents.

Requires guarded local QA settings; classification is a Phase 5 policy proposal,
not proof of production bucket ACLs or endpoint authorization.
"""

import argparse
import inspect
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def policy(label, field):
    if any(
        part in label
        for part in (
            "KYCSubmission",
            "VerificationRecord",
            "Payment",
            "DisputeEvidence",
            "MatchResultSubmission",
            "FormResponse",
            "ContractProofSubmission",
        )
    ):
        return (
            "private",
            "Owner and explicitly authorized reviewers/participants; never a public object URL",
        )
    if label.endswith("MatchMedia"):
        return (
            "conditional-private",
            "Evidence private; publish only explicitly reviewed non-evidence media",
        )
    if any(
        part in label
        for part in ("TeamMedia", "TeamMembership", "CommunityPostMedia", "Certificate")
    ):
        return (
            "conditional-private",
            "Inherit team/post/profile/certificate access; private until publication policy is approved",
        )
    if field in {"rules_pdf", "terms_pdf"}:
        return (
            "conditional-public",
            "Public only for eligible published tournament; organizer/staff for drafts",
        )
    public_artwork_models = {
        "games.Game",
        "games.GameMapPool",
        "organizations.Organization",
        "organizations.Team",
        "organizations.TeamAdminProxy",
        "user_profile.UserProfile",
        "user_profile.GameProfile",
        "ecommerce.Category",
        "ecommerce.Brand",
        "ecommerce.Product",
        "ecommerce.ProductImage",
        "economy.InventoryItem",
        "siteui.ArenaHighlight",
        "siteui.ArenaStream",
        "tournaments.Tournament",
        "tournaments.RegistrationFormTemplate",
        "tournaments.TournamentSponsor",
    }
    if label in public_artwork_models:
        return (
            "public-intended",
            "Published artwork only; writes require existing owner/organizer/editor permissions",
        )
    return "private", "Unclassified field: keep private pending explicit policy review"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("DJANGO_SETTINGS_MODULE") != "deltacrown.settings_brand_qa":
        raise RuntimeError("Set guarded local DJANGO_SETTINGS_MODULE=deltacrown.settings_brand_qa")
    import django

    django.setup()
    from django.apps import apps
    from django.db.models import FileField

    rows = []
    for model in apps.get_models():
        for field in model._meta.fields:
            if not isinstance(field, FileField):
                continue
            kwargs = field.deconstruct()[3]
            upload = field.upload_to
            category, access = policy(model._meta.label, field.name)
            rows.append(
                {
                    "model": model._meta.label,
                    "concrete_model": model._meta.concrete_model._meta.label,
                    "proxy": model._meta.proxy,
                    "field": field.name,
                    "type": type(field).__name__,
                    "source": Path(inspect.getfile(model)).relative_to(ROOT).as_posix(),
                    "upload_to": (
                        upload
                        if isinstance(upload, str)
                        else upload.__module__ + "." + upload.__qualname__
                    ),
                    "declared_storage": (
                        "settings.STORAGES default"
                        if "storage" not in kwargs
                        else type(field.storage).__module__ + "." + type(field.storage).__name__
                    ),
                    "validators": [
                        getattr(value, "__name__", type(value).__name__)
                        for value in field.validators
                    ],
                    "proposed_policy": category,
                    "required_authorization": access,
                    "lifecycle": "FieldFile.save/open/url/delete through configured backend; model save does not automatically run validators or delete replaced/orphaned objects",
                }
            )
    report = {
        "scope": "All registered model FileField/ImageField declarations, including proxy aliases; no DB rows or files read",
        "registered_fields": len(rows),
        "concrete_fields": len({(row["concrete_model"], row["field"]) for row in rows}),
        "production_backend_rule": "CLOUDINARY_URL present selects MediaCloudinaryStorage globally; otherwise FileSystemStorage. Live provider configuration/ACLs not queried.",
        "non_field_uploads": [
            {
                "route": "/ckeditor5/image_upload/",
                "handler": "django_ckeditor_5.storage_utils.handle_uploaded_file",
                "storage": "CKEDITOR_5_FILE_STORAGE, then legacy DEFAULT_FILE_STORAGE, then STORAGES default backend",
                "access": "Configured staff-only upload; PIL verification; raw URL embedded in rich-text HTML needs publication/backup review",
            }
        ],
        "fields": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        "Inventoried",
        report["registered_fields"],
        "registered /",
        report["concrete_fields"],
        "concrete file fields",
    )


if __name__ == "__main__":
    main()
