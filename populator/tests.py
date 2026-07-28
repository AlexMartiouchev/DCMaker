"""Tests for generation metering and polite failures.

Every test here mocks the engine — nothing in this file may reach the
OpenAI API, both because tests must not cost money and because a failing
network would look like a failing test.
"""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from . import usage
from .generation.schemas import Alignment, GeneratedLocation
from .models import Campaign, GenerationEvent


def a_location():
    return GeneratedLocation(
        name="Veilhold",
        location_type="drowned city",
        description="A city under mist.",
        summary="A city under mist.",
    )


class MeteringTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("dm", "dm@example.com", "pw")
        self.campaign = Campaign.objects.create(name="Tuesday Nighters", owner=self.user)
        self.client.force_login(self.user)
        self.url = reverse("generate_location_slot", args=[self.campaign.pk])

    def event(self, **kwargs):
        return GenerationEvent.objects.create(
            user=kwargs.pop("user", self.user),
            kind=kwargs.pop("kind", "location"),
            model=kwargs.pop("model", "test-model"),
            **kwargs,
        )

    # --- the cap -----------------------------------------------------

    @override_settings(DAILY_GENERATION_CAP=2)
    def test_requests_allowed_under_the_cap(self):
        with patch("populator.views.engine.generate_location", return_value=a_location()):
            response = self.client.post(self.url, {"concept": "a drowned city"})
        self.assertEqual(response.status_code, 200)

    @override_settings(DAILY_GENERATION_CAP=2)
    def test_request_refused_at_the_cap(self):
        self.event()
        self.event()
        with patch("populator.views.engine.generate_location") as generate:
            response = self.client.post(self.url, {"concept": "a drowned city"})
        self.assertEqual(response.status_code, 429)
        self.assertIn("Daily generation limit reached", response.content.decode())
        generate.assert_not_called()  # refused before spending anything

    @override_settings(DAILY_GENERATION_CAP=2)
    def test_events_outside_the_window_do_not_count(self):
        stale = self.event()
        GenerationEvent.objects.filter(pk=stale.pk).update(
            created_at=timezone.now() - timedelta(hours=25)
        )
        self.assertEqual(usage.remaining(self.user), 2)

    @override_settings(DAILY_GENERATION_CAP=0)
    def test_cap_of_zero_disables_the_limit(self):
        """The shipped default: metering still records, nothing refuses."""
        for _ in range(5):
            self.event()
        self.assertIsNone(usage.cap_for(self.user))
        self.assertIsNone(usage.remaining(self.user))
        usage.check(self.user)  # does not raise

        with patch("populator.views.engine.generate_location", return_value=a_location()):
            response = self.client.post(self.url, {"concept": "a drowned city"})
        self.assertEqual(response.status_code, 200)

    @override_settings(DAILY_GENERATION_CAP=1)
    def test_staff_are_exempt(self):
        self.user.is_staff = True
        self.user.save()
        self.event()
        self.assertIsNone(usage.cap_for(self.user))
        self.assertIsNone(usage.remaining(self.user))
        usage.check(self.user)  # does not raise

    @override_settings(DAILY_GENERATION_CAP=2)
    def test_cap_is_per_user(self):
        other = User.objects.create_user("other", "other@example.com", "pw")
        self.event(user=other)
        self.event(user=other)
        self.assertEqual(usage.remaining(self.user), 2)

    # --- telemetry ---------------------------------------------------

    def test_successful_call_records_an_event(self):
        with usage.metering(self.user, "location"):
            usage.record("test-model", 120, 45)

        event = GenerationEvent.objects.get()
        self.assertEqual(event.user, self.user)
        self.assertEqual(event.kind, "location")
        self.assertEqual(event.model, "test-model")
        self.assertEqual((event.input_tokens, event.output_tokens), (120, 45))

    def test_calls_outside_a_request_are_not_metered(self):
        """The management command and shell generate without a user."""
        usage.record("test-model", 10, 10)
        usage.before_call("test-model")  # must not raise
        self.assertEqual(GenerationEvent.objects.count(), 0)

    @override_settings(DAILY_GENERATION_CAP=2)
    def test_before_call_stops_a_batch_mid_flight(self):
        """A roster batch is many calls behind one click; the per-call
        hook is what stops it overshooting after the up-front check."""
        with usage.metering(self.user, "roster_batch"):
            usage.before_call("test-model")
            usage.record("test-model", 10, 10)
            usage.before_call("test-model")
            usage.record("test-model", 10, 10)
            with self.assertRaises(usage.GenerationLimitReached):
                usage.before_call("test-model")

    # --- polite failures ---------------------------------------------

    def test_engine_failure_returns_a_readable_message(self):
        with patch(
            "populator.views.engine.generate_location", side_effect=RuntimeError("boom")
        ):
            with self.assertLogs("populator.views", level="ERROR"):
                response = self.client.post(self.url, {"concept": "a drowned city"})

        self.assertEqual(response.status_code, 502)
        body = response.content.decode()
        self.assertIn("did not answer", body)
        self.assertNotIn("boom", body)  # provider detail stays in the log

    def test_failed_generation_saves_nothing(self):
        with patch(
            "populator.views.engine.generate_location", side_effect=RuntimeError("boom")
        ):
            with self.assertLogs("populator.views", level="ERROR"):
                self.client.post(self.url, {"concept": "a drowned city"})
        self.assertEqual(self.campaign.locations.count(), 0)

    def test_ownership_still_enforced(self):
        """The decorator must not swallow a 404 into a generic 502."""
        intruder = User.objects.create_user("intruder", "i@example.com", "pw")
        self.client.force_login(intruder)
        with patch("populator.views.engine.generate_location") as generate:
            response = self.client.post(self.url, {"concept": "x"})
        self.assertEqual(response.status_code, 404)
        generate.assert_not_called()
