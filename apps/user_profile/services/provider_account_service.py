"""Preserve ownership of verified provider identities during concurrent linking."""

from django.db import transaction

from apps.user_profile.models import ProviderAccount


class ProviderIdentityInUse(Exception):
    pass


@transaction.atomic
def claim_provider_account(*, user, provider, provider_account_id, provider_data):
    # get_or_create's unique-key retry may return the competing user's row.
    # Never pass a new user in update_or_create defaults: that can transfer it.
    account, created = ProviderAccount.objects.get_or_create(
        provider=provider,
        provider_account_id=provider_account_id,
        defaults={"user": user, "provider_data": provider_data},
    )
    account = ProviderAccount.objects.select_for_update().get(pk=account.pk)
    if account.user_id != user.pk:
        raise ProviderIdentityInUse("Provider identity belongs to another user")
    if not created:
        account.provider_data = provider_data
        account.save(update_fields=["provider_data", "updated_at"])
    return account
