import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.user_profile import models as up_models

target_models = [
    ('PinnedHighlight', up_models.PinnedHighlight),
    ('ProfileAboutItem', up_models.ProfileAboutItem),
    ('BountyProof', up_models.BountyProof),
    ('Bounty', up_models.Bounty),
    ('BountyDispute', up_models.BountyDispute),
    ('SkillEndorsement', up_models.SkillEndorsement),
    ('EndorsementOpportunity', up_models.EndorsementOpportunity),
    ('TrophyShowcaseConfig', up_models.TrophyShowcaseConfig),
]

for name, model in target_models:
    print(f"\n{name} fields:")
    for field in model._meta.get_fields():
        print(f"  - {field.name} ({field.__class__.__name__})")
