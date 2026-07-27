"""Front-door tests: the 2024 auth code crashed on successful login, so
these lock in that the whole sign-in / sign-out loop actually works."""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AuthFlowTests(TestCase):
    def setUp(self):
        self.password = "arcane-passphrase-42"
        self.user = User.objects.create_user(
            "dungeonmaster", "dm@example.com", self.password
        )

    def test_login_page_renders(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in")

    def test_login_lands_on_campaign_list(self):
        response = self.client.post(
            reverse("login"),
            {"username": "dungeonmaster", "password": self.password},
        )
        self.assertRedirects(response, reverse("campaign_list"))

    def test_login_honours_next(self):
        target = reverse("campaign_list")
        response = self.client.post(
            f"{reverse('login')}?next={target}",
            {"username": "dungeonmaster", "password": self.password, "next": target},
        )
        self.assertRedirects(response, target)

    def test_login_rejects_offsite_next(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "dungeonmaster",
                "password": self.password,
                "next": "https://evil.example.com/steal",
            },
        )
        self.assertRedirects(response, reverse("campaign_list"))

    def test_bad_password_shows_error(self):
        response = self.client.post(
            reverse("login"), {"username": "dungeonmaster", "password": "wrong"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "correct username and password")

    def test_register_creates_and_signs_in(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "newdm",
                "email": "new@example.com",
                "password1": "arcane-passphrase-42",
                "password2": "arcane-passphrase-42",
            },
        )
        self.assertRedirects(response, reverse("campaign_list"))
        new_user = User.objects.get(username="newdm")
        self.assertEqual(int(self.client.session["_auth_user_id"]), new_user.pk)

    def test_register_rejects_duplicate_email(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "otherdm",
                "email": "DM@example.com",
                "password1": "arcane-passphrase-42",
                "password2": "arcane-passphrase-42",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")
        self.assertFalse(User.objects.filter(username="otherdm").exists())

    def test_logout_is_post_only(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_protected_page_redirects_anonymous_with_next(self):
        response = self.client.get(reverse("campaign_list"))
        self.assertRedirects(
            response, f"{reverse('login')}?next={reverse('campaign_list')}"
        )
