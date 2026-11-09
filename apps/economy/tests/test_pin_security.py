"""Wallet PIN policy and security regression tests (synthetic users, disposable database).

Policy: new PINs are 6 digits; an existing PIN (including a legacy 4-digit hash, and a hash with
pin_enabled=False) is never replaced without verifying it; failed verification shares one lockout
across the withdrawal form, the PIN APIs and the PIN change form; PINs are only ever stored hashed.
"""
import logging
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.test import Client
from django.utils import timezone

from apps.economy.forms import PINSetupForm, WithdrawalRequestForm
from apps.economy.models import DeltaCrownTransaction, DeltaCrownWallet, WalletPINOTP, WithdrawalRequest
from apps.economy.services import wallet_pin
from apps.user_profile.models import UserProfile

pytestmark = pytest.mark.django_db
User = get_user_model()
HTML, SETUP_API, VERIFY_API = '/pin/setup/', '/api/wallet/pin/setup/', '/api/wallet/pin/verify/'
OTP_REQUEST, OTP_VERIFY, WITHDRAW_API = '/api/wallet/pin/otp/request/', '/api/wallet/pin/otp/verify/', '/api/withdraw/request/'
GOOD, GOOD2 = '482916', '735204'


def _make_user(name):
    user = User.objects.create_user(username=name, email=f'{name}@example.test', password='pw-12345!')
    profile, _ = UserProfile.objects.get_or_create(user=user)
    wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=profile)
    return user, wallet


@pytest.fixture
def owner():
    return _make_user('pin_owner')


@pytest.fixture
def client_for():
    def make(user, strict=False):
        client = Client(enforce_csrf_checks=strict)
        client.force_login(user)
        return client
    return make


def _give_pin(wallet, pin, enabled=True):
    DeltaCrownWallet.objects.filter(pk=wallet.pk).update(pin_hash=make_password(pin), pin_enabled=enabled)
    wallet.refresh_from_db()


def _fresh(wallet):
    return DeltaCrownWallet.objects.get(pk=wallet.pk)


def _html_post(client, **data):
    return client.post(HTML, data, secure=True)


# ------------------------------------------------------------------ setup ------
class TestFirstTimeSetup:
    def test_html_setup_persists_a_hashed_enabled_pin(self, owner, client_for):
        user, wallet = owner
        client = client_for(user)
        assert 'id_current_pin' not in client.get(HTML, secure=True).content.decode()  # nothing to verify yet
        response = _html_post(client, pin=GOOD, pin_confirm=GOOD)
        assert response.status_code == 302
        stored = _fresh(wallet)
        assert stored.pin_enabled and stored.pin_hash and GOOD not in stored.pin_hash
        assert check_password(GOOD, stored.pin_hash)

    @pytest.mark.parametrize('pin', ['1234', '12345', '1234567', 'abcdef', '12 456', '000000', '111111', '123456', '654321'])
    def test_invalid_or_weak_pins_are_rejected_and_nothing_is_stored(self, owner, client_for, pin):
        user, wallet = owner
        _html_post(client_for(user), pin=pin, pin_confirm=pin)
        assert not _fresh(wallet).pin_hash

    def test_mismatched_confirmation_is_rejected(self, owner, client_for):
        user, wallet = owner
        _html_post(client_for(user), pin=GOOD, pin_confirm=GOOD2)
        assert not _fresh(wallet).pin_hash

    def test_api_and_html_apply_the_same_policy(self, owner, client_for):
        user, wallet = owner
        client = client_for(user)
        for pin in ('1234', '12345', '111111', '123456', 'abcdef'):
            response = client.post(SETUP_API, {'pin': pin, 'confirm_pin': pin}, secure=True)
            assert response.status_code == 400, pin
        assert not _fresh(wallet).pin_hash
        ok = client.post(SETUP_API, {'pin': GOOD, 'confirm_pin': GOOD}, secure=True)
        assert ok.status_code == 200 and check_password(GOOD, _fresh(wallet).pin_hash)

    def test_plaintext_pin_is_never_logged_or_returned(self, owner, client_for, caplog):
        user, wallet = owner
        with caplog.at_level(logging.DEBUG):
            body = client_for(user).post(SETUP_API, {'pin': GOOD, 'confirm_pin': GOOD}, secure=True).content.decode()
            _html_post(client_for(user), pin=GOOD2, current_pin=GOOD, pin_confirm=GOOD2)
        assert GOOD not in body and GOOD not in caplog.text and GOOD2 not in caplog.text


# ----------------------------------------------------------------- change ------
class TestChangingAnExistingPin:
    def test_correct_current_pin_changes_it(self, owner, client_for):
        user, wallet = owner
        _give_pin(wallet, GOOD)
        assert 'id_current_pin' in client_for(user).get(HTML, secure=True).content.decode()
        _html_post(client_for(user), current_pin=GOOD, pin=GOOD2, pin_confirm=GOOD2)
        assert check_password(GOOD2, _fresh(wallet).pin_hash)

    def test_missing_or_wrong_current_pin_never_changes_it(self, owner, client_for):
        user, wallet = owner
        _give_pin(wallet, GOOD)
        before = _fresh(wallet).pin_hash
        _html_post(client_for(user), pin=GOOD2, pin_confirm=GOOD2)
        _html_post(client_for(user), current_pin='999888', pin=GOOD2, pin_confirm=GOOD2)
        assert _fresh(wallet).pin_hash == before and _fresh(wallet).pin_failed_attempts == 1

    def test_a_typo_in_the_new_pin_does_not_burn_a_lockout_attempt(self, owner, client_for):
        user, wallet = owner
        _give_pin(wallet, GOOD)
        _html_post(client_for(user), current_pin='999888', pin=GOOD2, pin_confirm='000001')
        assert _fresh(wallet).pin_failed_attempts == 0

    def test_api_requires_the_current_pin_to_change(self, owner, client_for):
        user, wallet = owner
        _give_pin(wallet, GOOD)
        client = client_for(user)
        assert client.post(SETUP_API, {'pin': GOOD2, 'confirm_pin': GOOD2}, secure=True).status_code == 400
        assert client.post(SETUP_API, {'pin': GOOD2, 'confirm_pin': GOOD2, 'current_pin': '999888'}, secure=True).status_code == 403
        assert check_password(GOOD, _fresh(wallet).pin_hash)
        assert client.post(SETUP_API, {'pin': GOOD2, 'confirm_pin': GOOD2, 'current_pin': GOOD}, secure=True).status_code == 200
        assert check_password(GOOD2, _fresh(wallet).pin_hash)


# ----------------------------------------------------- legacy / odd states ------
class TestLegacyAndInconsistentStates:
    def test_legacy_four_digit_pin_still_verifies_everywhere(self, owner, client_for):
        user, wallet = owner
        _give_pin(wallet, '4821', enabled=False)  # legacy: short PIN, flag never set
        assert wallet_pin.verify_pin_with_lockout(wallet.pk, '4821').ok
        assert client_for(user).post(VERIFY_API, {'pin': '4821'}, secure=True).status_code == 200
        form = WithdrawalRequestForm({'pin': '4821', 'amount': 10, 'payment_method': 'bkash'}, wallet=_fresh(wallet))
        form.is_valid()
        assert 'pin' not in form.errors

    def test_an_existing_pin_with_pin_enabled_false_is_never_overwritten_without_verification(self, owner, client_for):
        user, wallet = owner
        _give_pin(wallet, '4821', enabled=False)
        before = _fresh(wallet).pin_hash
        client = client_for(user)
        assert client.post(SETUP_API, {'pin': GOOD, 'confirm_pin': GOOD}, secure=True).status_code == 400
        _html_post(client, pin=GOOD, pin_confirm=GOOD)
        assert client.post(OTP_REQUEST, {'purpose': 'pin_setup'}, secure=True).status_code == 400
        assert _fresh(wallet).pin_hash == before
        # the legacy PIN holder can rotate to a 6-digit PIN by proving the old one
        assert client.post(SETUP_API, {'pin': GOOD, 'confirm_pin': GOOD, 'current_pin': '4821'}, secure=True).status_code == 200
        assert check_password(GOOD, _fresh(wallet).pin_hash)

    def test_enabled_flag_without_a_hash_counts_as_no_pin(self, owner, client_for):
        user, wallet = owner
        DeltaCrownWallet.objects.filter(pk=wallet.pk).update(pin_enabled=True, pin_hash='')
        client = client_for(user)
        assert client.post(VERIFY_API, {'pin': GOOD}, secure=True).status_code == 400  # "not set up"
        assert client.post(SETUP_API, {'pin': GOOD, 'confirm_pin': GOOD}, secure=True).status_code == 200  # not locked out forever
        assert check_password(GOOD, _fresh(wallet).pin_hash)

    def test_model_set_pin_uses_the_six_digit_policy(self, owner):
        _user, wallet = owner
        with pytest.raises(ValueError):
            wallet.set_pin('1234')
        wallet.set_pin(GOOD)
        wallet.save()
        assert check_password(GOOD, _fresh(wallet).pin_hash) and _fresh(wallet).pin_enabled


# ---------------------------------------------------------------- lockout ------
class TestSharedLockout:
    def test_withdrawal_form_locks_after_five_failures_and_stays_locked_for_the_right_pin(self, owner):
        _user, wallet = owner
        _give_pin(wallet, GOOD)
        for _ in range(5):
            form = WithdrawalRequestForm({'pin': '999888', 'amount': 10, 'payment_method': 'bkash'}, wallet=_fresh(wallet))
            form.is_valid()
            assert 'pin' in form.errors
        assert _fresh(wallet).pin_locked_until > timezone.now()
        form = WithdrawalRequestForm({'pin': GOOD, 'amount': 10, 'payment_method': 'bkash'}, wallet=_fresh(wallet))
        form.is_valid()
        assert 'locked' in str(form.errors['pin']).lower()

    def test_failures_are_counted_across_entry_points(self, owner, client_for):
        user, wallet = owner
        DeltaCrownWallet.objects.filter(pk=wallet.pk).update(cached_balance=500)
        _give_pin(wallet, GOOD)
        client = client_for(user)
        for _ in range(2):
            client.post(VERIFY_API, {'pin': '999888'}, secure=True)
        for _ in range(2):
            form = WithdrawalRequestForm({'pin': '999888', 'amount': 10, 'payment_method': 'bkash'}, wallet=_fresh(wallet))
            form.is_valid()
        _html_post(client, current_pin='999888', pin=GOOD2, pin_confirm=GOOD2)
        assert _fresh(wallet).pin_locked_until is not None
        # every entry point now refuses, even with the correct PIN
        assert client.post(VERIFY_API, {'pin': GOOD}, secure=True).status_code == 403
        assert client.post(SETUP_API, {'pin': GOOD2, 'confirm_pin': GOOD2, 'current_pin': GOOD}, secure=True).status_code == 403
        assert client.post(WITHDRAW_API, {'amount': 100, 'pin': GOOD, 'payment_method': 'bkash', 'payment_number': '01700000000'}, secure=True).status_code == 403
        assert check_password(GOOD, _fresh(wallet).pin_hash)

    def test_withdraw_api_wrong_pins_lock_the_wallet_and_create_no_request(self, owner, client_for):
        user, wallet = owner
        DeltaCrownWallet.objects.filter(pk=wallet.pk).update(cached_balance=500)
        _give_pin(wallet, GOOD, enabled=False)  # legacy-style flag state must still be enforced
        client = client_for(user)
        for _ in range(5):
            assert client.post(WITHDRAW_API, {'amount': 100, 'pin': '999888', 'payment_method': 'bkash', 'payment_number': '01700000000'}, secure=True).status_code == 403
        assert _fresh(wallet).pin_locked_until > timezone.now()
        assert WithdrawalRequest.objects.count() == 0

    def test_expired_lock_allows_the_correct_pin_and_resets_the_counter(self, owner):
        _user, wallet = owner
        _give_pin(wallet, GOOD)
        DeltaCrownWallet.objects.filter(pk=wallet.pk).update(pin_failed_attempts=5, pin_locked_until=timezone.now() - timedelta(minutes=1))
        assert wallet_pin.verify_pin_with_lockout(wallet.pk, GOOD).ok
        assert _fresh(wallet).pin_failed_attempts == 0 and _fresh(wallet).pin_locked_until is None

    def test_no_pin_means_withdrawals_are_refused(self, owner, client_for):
        user, wallet = owner
        DeltaCrownWallet.objects.filter(pk=wallet.pk).update(cached_balance=500)
        response = client_for(user).post(WITHDRAW_API, {'amount': 100, 'pin': GOOD, 'payment_method': 'bkash', 'payment_number': '01700000000'}, secure=True)
        assert response.status_code == 400 and response.json().get('pin_required') is True
        assert WithdrawalRequest.objects.count() == 0


# ------------------------------------------------------------------- OTP -------
class TestOtpFlow:
    def _otp(self, wallet, purpose):
        return WalletPINOTP.objects.create(
            wallet=wallet, code_hash=make_password('246810'), purpose=purpose,
            expires_at=timezone.now() + timedelta(minutes=10),
        )

    def test_stale_setup_otp_cannot_replace_an_existing_pin(self, owner, client_for):
        user, wallet = owner
        _give_pin(wallet, GOOD)
        self._otp(wallet, 'pin_setup')
        response = client_for(user).post(OTP_VERIFY, {'otp_code': '246810', 'pin': GOOD2, 'confirm_pin': GOOD2}, secure=True)
        assert response.status_code == 403
        assert check_password(GOOD, _fresh(wallet).pin_hash)

    def test_change_otp_replaces_the_pin_and_first_time_setup_still_works(self, owner, client_for):
        user, wallet = owner
        self._otp(wallet, 'pin_setup')
        assert client_for(user).post(OTP_VERIFY, {'otp_code': '246810', 'pin': GOOD, 'confirm_pin': GOOD}, secure=True).status_code == 200
        assert check_password(GOOD, _fresh(wallet).pin_hash)
        self._otp(wallet, 'pin_change')
        assert client_for(user).post(OTP_VERIFY, {'otp_code': '246810', 'pin': GOOD2, 'confirm_pin': GOOD2}, secure=True).status_code == 200
        assert check_password(GOOD2, _fresh(wallet).pin_hash)

    def test_otp_flow_rejects_weak_pins(self, owner, client_for):
        user, wallet = owner
        self._otp(wallet, 'pin_setup')
        assert client_for(user).post(OTP_VERIFY, {'otp_code': '246810', 'pin': '111111', 'confirm_pin': '111111'}, secure=True).status_code == 400
        assert not _fresh(wallet).pin_hash

    def test_pin_change_otp_request_needs_the_current_pin(self, owner, client_for):
        user, wallet = owner
        _give_pin(wallet, GOOD, enabled=False)
        client = client_for(user)
        assert client.post(OTP_REQUEST, {'purpose': 'pin_change'}, secure=True).status_code == 400
        assert client.post(OTP_REQUEST, {'purpose': 'pin_change', 'current_pin': '999888'}, secure=True).status_code == 403


# ------------------------------------------------- authentication boundaries ------
class TestAuthenticationAndOwnership:
    @pytest.mark.parametrize('path', [HTML, SETUP_API, VERIFY_API, OTP_REQUEST, OTP_VERIFY, WITHDRAW_API])
    def test_anonymous_requests_are_redirected_to_login(self, path):
        response = Client().post(path, {'pin': GOOD, 'confirm_pin': GOOD}, secure=True)
        assert response.status_code == 302 and '/login' in response['Location']

    def test_csrf_is_enforced_on_every_pin_post(self, owner, client_for):
        user, wallet = owner
        strict = client_for(user, strict=True)
        for path in (HTML, SETUP_API, VERIFY_API, OTP_REQUEST):
            assert strict.post(path, {'pin': GOOD, 'confirm_pin': GOOD, 'pin_confirm': GOOD}, secure=True).status_code == 403
        assert not _fresh(wallet).pin_hash

    def test_a_player_can_only_touch_their_own_wallet(self, owner, client_for):
        user, wallet = owner
        other, other_wallet = _make_user('pin_other')
        _give_pin(other_wallet, GOOD)
        before = _fresh(other_wallet).pin_hash
        client = client_for(user)
        # No parameter selects a wallet: even with hostile extra fields the other wallet is untouched.
        client.post(SETUP_API, {'pin': GOOD2, 'confirm_pin': GOOD2, 'wallet_id': other_wallet.pk, 'profile': other.profile.pk}, secure=True)
        _html_post(client, pin=GOOD2, pin_confirm=GOOD2, wallet=other_wallet.pk)
        assert _fresh(other_wallet).pin_hash == before and _fresh(other_wallet).pin_failed_attempts == 0
        assert check_password(GOOD2, _fresh(wallet).pin_hash)


# ----------------------------------------------------------- side effects -------
def test_pin_operations_have_no_financial_side_effects(owner, client_for):
    user, wallet = owner
    DeltaCrownWallet.objects.filter(pk=wallet.pk).update(cached_balance=777, pending_balance=0)
    client = client_for(user)
    client.post(SETUP_API, {'pin': GOOD, 'confirm_pin': GOOD}, secure=True)
    client.post(VERIFY_API, {'pin': '999888'}, secure=True)
    _html_post(client, current_pin=GOOD, pin=GOOD2, pin_confirm=GOOD2)
    stored = _fresh(wallet)
    assert (stored.cached_balance, stored.pending_balance) == (777, 0)
    assert DeltaCrownTransaction.objects.count() == 0 and WithdrawalRequest.objects.count() == 0


def test_setup_form_only_asks_for_the_current_pin_when_one_exists(owner):
    _user, wallet = owner
    assert 'current_pin' not in PINSetupForm(wallet=wallet).fields
    _give_pin(wallet, GOOD)
    assert 'current_pin' in PINSetupForm(wallet=_fresh(wallet)).fields
