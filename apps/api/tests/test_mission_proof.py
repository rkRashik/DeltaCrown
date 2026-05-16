from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from apps.contracts.models import ContractEnrollment, ContractProofSubmission, ContractTemplate
from apps.contracts.services import ContractService
from apps.organizations.tests.factories import GameFactory, UserFactory


@pytest.fixture
def api_client():
    return APIClient()


def authenticate(client, user):
    client.force_authenticate(user=user)
    return client


def create_enrollment(user):
    game = GameFactory(short_code="MPF")
    template = ContractTemplate.objects.create(
        title="Proof Mission",
        game=game,
        entry_fee_dc=0,
        reward_dc=50,
    )
    return ContractEnrollment.objects.create(
        user=user,
        template=template,
        status="ACTIVE",
        deadline_at=timezone.now() + timedelta(hours=12),
    )


@pytest.mark.django_db
def test_owner_submits_mission_proof(api_client):
    user = UserFactory()
    enrollment = create_enrollment(user)

    response = authenticate(api_client, user).post(
        f"/api/v1/contracts/enrollments/{enrollment.id}/proofs/",
        {"proof_url": "https://example.com/proof.png", "notes": "Final scoreboard"},
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["status"] == "PENDING_REVIEW"
    assert ContractProofSubmission.objects.filter(enrollment=enrollment).count() == 1


@pytest.mark.django_db
def test_owner_uploads_mission_proof_file(api_client):
    user = UserFactory()
    enrollment = create_enrollment(user)
    proof_file = SimpleUploadedFile(
        "scoreboard.png",
        b"\x89PNG\r\n\x1a\n" + b"0" * 128,
        content_type="image/png",
    )

    response = authenticate(api_client, user).post(
        f"/api/v1/contracts/enrollments/{enrollment.id}/proofs/",
        {"proof_file": proof_file, "notes": "Uploaded scoreboard"},
        format="multipart",
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "PENDING_REVIEW"
    assert payload["proof_file_url"]
    proof = ContractProofSubmission.objects.get(enrollment=enrollment)
    assert proof.proof_file


@pytest.mark.django_db
def test_invalid_mission_proof_file_rejected(api_client):
    user = UserFactory()
    enrollment = create_enrollment(user)
    bad_file = SimpleUploadedFile(
        "payload.exe",
        b"MZ" + b"0" * 128,
        content_type="application/x-msdownload",
    )

    response = authenticate(api_client, user).post(
        f"/api/v1/contracts/enrollments/{enrollment.id}/proofs/",
        {"proof_file": bad_file},
        format="multipart",
    )

    assert response.status_code == 400
    assert ContractProofSubmission.objects.filter(enrollment=enrollment).count() == 0


@pytest.mark.django_db
def test_unrelated_user_cannot_submit_mission_proof(api_client):
    owner = UserFactory()
    outsider = UserFactory()
    enrollment = create_enrollment(owner)

    response = authenticate(api_client, outsider).post(
        f"/api/v1/contracts/enrollments/{enrollment.id}/proofs/",
        {"proof_url": "https://example.com/proof.png"},
        format="json",
    )

    assert response.status_code == 400
    assert ContractProofSubmission.objects.filter(enrollment=enrollment).count() == 0


@pytest.mark.django_db
def test_admin_review_proof_does_not_auto_complete_mission():
    user = UserFactory()
    admin = UserFactory(is_staff=True)
    enrollment = create_enrollment(user)
    proof = ContractService.submit_proof(
        enrollment_id=enrollment.id,
        user=user,
        proof_url="https://example.com/proof.png",
        notes="Result proof",
    )

    ContractService.review_proof(
        proof_id=proof.id,
        actor=admin,
        decision="ACCEPTED",
        note="Proof looks valid.",
    )

    proof.refresh_from_db()
    enrollment.refresh_from_db()
    assert proof.status == "ACCEPTED"
    assert enrollment.status == "ACTIVE"
    assert enrollment.resolved_at is None


@pytest.mark.django_db
def test_admin_rejects_mission_proof():
    user = UserFactory()
    admin = UserFactory(is_staff=True)
    enrollment = create_enrollment(user)
    proof = ContractService.submit_proof(
        enrollment_id=enrollment.id,
        user=user,
        proof_url="https://example.com/proof.png",
    )

    ContractService.review_proof(
        proof_id=proof.id,
        actor=admin,
        decision="REJECTED",
        note="Wrong match.",
    )

    proof.refresh_from_db()
    enrollment.refresh_from_db()
    assert proof.status == "REJECTED"
    assert enrollment.status == "ACTIVE"
