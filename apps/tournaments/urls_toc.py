"""
Tournament Operations Center (TOC) — URL Configuration.

Maps /toc/<slug>/ to the TOC SPA shell.
Future sprints add API endpoints under /api/toc/<slug>/.

Sprint 0 — Foundation Shell
Tracker: S0-B4
"""

from django.urls import path

from apps.tournaments.views.toc import TOCView

app_name = 'toc'

urlpatterns = [
    path('<slug:slug>/', TOCView.as_view(), name='hub'),
]
