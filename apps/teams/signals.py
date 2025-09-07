from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.apps import apps


def _lower_or_none(value):
    if value is None:
        return None
    s = str(value).strip()
    return s.lower() if s else None


@receiver(pre_save)
def team_ci_autofill(sender, instance, **kwargs):
    """
    Populate Team.name_ci / Team.tag_ci from name/tag without touching the legacy model code.
    Only runs for the Team model.
    """
    Team = apps.get_model("teams", "Team")
    if sender is not Team:
        return

    # Only set if fields exist on the model (during migrations they might not)
    if hasattr(instance, "name_ci") and hasattr(instance, "name"):
        instance.name_ci = _lower_or_none(getattr(instance, "name", None))
    if hasattr(instance, "tag_ci") and hasattr(instance, "tag"):
        instance.tag_ci = _lower_or_none(getattr(instance, "tag", None))
