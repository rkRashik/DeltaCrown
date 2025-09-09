from .site_content import SITE_CONTENT

def site(request):
    """
    Inject a deterministic SITE object so templates never crash even if data is missing.
    """
    # Shallow copy to avoid accidental mutation across requests
    site = {**SITE_CONTENT}
    return {"SITE": site}
