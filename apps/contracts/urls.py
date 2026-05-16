"""Missions API URL configuration."""
from django.urls import path

from .views import (
    ContractEnrollmentDetailView,
    ContractEnrollView,
    ContractProofListCreateView,
    ContractTemplateListView,
    MyEnrollmentsView,
)


app_name = 'contracts_api'

urlpatterns = [
    path(
        'templates/',
        ContractTemplateListView.as_view(),
        name='template-list',
    ),
    path(
        'enroll/<uuid:template_id>/',
        ContractEnrollView.as_view(),
        name='enroll',
    ),
    path(
        'enrollments/<uuid:enrollment_id>/',
        ContractEnrollmentDetailView.as_view(),
        name='enrollment-detail',
    ),
    path(
        'enrollments/<uuid:enrollment_id>/proofs/',
        ContractProofListCreateView.as_view(),
        name='enrollment-proofs',
    ),
    path(
        'my/',
        MyEnrollmentsView.as_view(),
        name='my-enrollments',
    ),
]
