from django.contrib import admin
from apps.user_profile import models as up_models

print("\n==== CHECKING ADMIN REGISTRATION ====\n")

# Get all registered models
registered_models = admin.site._registry

print(f"Total registered models: {len(registered_models)}\n")

# Filter for user_profile app
up_registered = {}
for model, model_admin in registered_models.items():
    app_label = model._meta.app_label
    if app_label == 'user_profile':
        up_registered[model.__name__] = {
            'model': model,
            'admin': model_admin.__class__.__name__,
            'app_label': app_label,
            'db_table': model._meta.db_table
        }

print(f"user_profile app registered models: {len(up_registered)}\n")

# List them all
for model_name in sorted(up_registered.keys()):
    info = up_registered[model_name]
    print(f"✓ {model_name}")
    print(f"  Admin: {info['admin']}")
    print(f"  Table: {info['db_table']}")
    print()

# Check specific models we're looking for
target_models = [
    'StreamConfig', 'HighlightClip', 'PinnedHighlight',
    'HardwareGear', 'GameConfig',
    'ProfileShowcase', 'ProfileAboutItem',
    'TrophyShowcaseConfig',
    'SkillEndorsement', 'EndorsementOpportunity',
    'Bounty', 'BountyAcceptance', 'BountyProof', 'BountyDispute'
]

print("\n==== TARGET MODELS CHECK ====\n")
for model_name in target_models:
    if model_name in up_registered:
        print(f"✓ {model_name} - REGISTERED")
    else:
        print(f"✗ {model_name} - NOT REGISTERED")
