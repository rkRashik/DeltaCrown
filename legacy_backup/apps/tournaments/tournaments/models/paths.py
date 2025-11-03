# apps/tournaments/models/paths.py

def tournament_banner_path(instance, filename):
    return f"tournaments/{instance.id}/banner/{filename}"

def rules_pdf_path(instance, filename):
    return f"tournaments/{instance.id}/rules/{filename}"

def rules_upload_path(instance, filename):
    return f"tournaments/{instance.tournament_id}/rules/{filename}"
