"""Password reset must accept Django SetPasswordForm fields and confirm success.

Synthetic account only; sends no email, touches no production data.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


@override_settings(SITE_URL="https://ownlobby.com")
class PasswordResetSubmissionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="reset-qa", email="reset-qa@example.invalid",
            password="Original-Long-Password-9082"
        )
        self.url = reverse("account:password_reset_confirm", kwargs={
            "uidb64": urlsafe_base64_encode(force_bytes(self.user.pk)),
            "token": default_token_generator.make_token(self.user),
        })

    def _open_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        form_url = response.url
        response = self.client.get(form_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="new_password1"')
        self.assertContains(response, 'name="new_password2"')
        self.assertNotContains(response, 'name="password1"')
        return form_url

    def test_matching_valid_password_redirects_to_success_and_updates_account(self):
        post_url = self._open_form()
        response = self.client.post(post_url, {
            "new_password1": "Updated-Long-Password-9083",
            "new_password2": "Updated-Long-Password-9083",
        })
        self.assertRedirects(response, reverse("account:password_reset_complete"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Updated-Long-Password-9083"))
        self.assertFalse(self.user.check_password("Original-Long-Password-9082"))
        completion = self.client.get(response.url)
        self.assertContains(completion, "Password Updated")

    def test_mismatch_shows_visible_errors_without_updating_password(self):
        post_url = self._open_form()
        response = self.client.post(post_url, {
            "new_password1": "Updated-Long-Password-9083",
            "new_password2": "Different-Long-Password-9084",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'role="alert"')
        self.assertContains(response, "Password not updated")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Original-Long-Password-9082"))

    def test_old_token_cannot_be_used_again_after_success(self):
        post_url = self._open_form()
        self.client.post(post_url, {
            "new_password1": "Updated-Long-Password-9083",
            "new_password2": "Updated-Long-Password-9083",
        })
        response = self.client.get(self.url, follow=True)
        self.assertContains(response, "This password reset link is invalid", status_code=200)
