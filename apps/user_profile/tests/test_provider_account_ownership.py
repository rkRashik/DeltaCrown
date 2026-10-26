"""Real PostgreSQL transaction regressions for provider identity ownership."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.contrib.auth import get_user_model
from django.db import connections

from apps.user_profile.models import ProviderAccount
from apps.user_profile.services.provider_account_service import (
    ProviderIdentityInUse,
    claim_provider_account,
)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("provider", ["riot", "steam", "epic"])
def test_concurrent_claims_cannot_transfer_identity(provider):
    users = [
        get_user_model().objects.create_user(
            "claim-qa-" + str(i), "claim-qa-" + str(i) + "@example.com", "qa-password"
        )
        for i in range(2)
    ]
    start = Barrier(2)

    def claim(user):
        try:
            start.wait(timeout=10)
            account = claim_provider_account(
                user=user,
                provider=provider,
                provider_account_id="synthetic-shared-id",
                provider_data={"fixture": "qa"},
            )
            return account.user_id
        except ProviderIdentityInUse:
            return None
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim, users))
    assert results.count(None) == 1
    account = ProviderAccount.objects.get(
        provider=provider, provider_account_id="synthetic-shared-id"
    )
    assert account.user_id == next(value for value in results if value is not None)
    assert (
        ProviderAccount.objects.filter(
            provider=provider, provider_account_id="synthetic-shared-id"
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_owner_resync_updates_metadata_without_changing_identity():
    user = get_user_model().objects.create_user("resync-qa", "resync-qa@example.com", "qa-password")
    first = claim_provider_account(
        user=user,
        provider="steam",
        provider_account_id="synthetic-owner-id",
        provider_data={"revision": 1},
    )
    second = claim_provider_account(
        user=user,
        provider="steam",
        provider_account_id="synthetic-owner-id",
        provider_data={"revision": 2},
    )
    assert first.pk == second.pk
    assert second.user_id == user.pk
    assert second.provider_account_id == "synthetic-owner-id"
    assert second.provider_data == {"revision": 2}
