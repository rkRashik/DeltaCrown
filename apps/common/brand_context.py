from django.conf import settings


def brand_context(request):
    return {"brand": settings.BRAND}
