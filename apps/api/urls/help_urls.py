"""
URL Configuration for Help & Onboarding API

Phase 7, Epic 7.6: Guidance & Help Overlays
Routes for organizer help, onboarding, and tooltips.
"""

from django.urls import path
from apps.api.views.organizer_help_views import (
    HelpBundleView,
    CompleteOnboardingStepView,
    DismissHelpItemView,
    OnboardingProgressView,
)

urlpatterns = [
    # Get help bundle for a page
    path('bundle/', HelpBundleView.as_view(), name='help-bundle'),
    
    # Complete onboarding step
    path('complete-step/', CompleteOnboardingStepView.as_view(), name='complete-onboarding-step'),
    
    # Dismiss help item
    path('dismiss/', DismissHelpItemView.as_view(), name='dismiss-help-item'),
    
    # Get onboarding progress
    path('progress/', OnboardingProgressView.as_view(), name='onboarding-progress'),
]
