from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),

    # CKEditor-5
    path("ckeditor5/", include("django_ckeditor_5.urls")),

    path("tournaments/", include("apps.tournaments.urls")),


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
