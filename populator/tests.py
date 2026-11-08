"""Tests for generation metering, polite failures, character motivation
and RAG seed loading.

Every test here mocks the engine — nothing in this file may reach the
OpenAI API, both because tests must not cost money and because a failing
network would look like a failing test.
"""

import json
import tempfile
from datetime import timedelta
from io import StringIO
from pathlib import Path
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.template.loader import render_to_string
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from pydantic import ValidationError

from . import orchestrator, rag, usage
from .generation.schemas import (
    Alignment,
    GeneratedCharacter,
    GeneratedLocation,
    MobArchetype,
)
from .models import Campaign, Character, Faction, GenerationEvent, RagDocument


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


class MotivationTests(TestCase):
    """Motivation is a real Character column, filled by both generation
    paths, and absent-but-harmless on rows that predate it."""

    def setUp(self):
        user = User.objects.create_user("dm", "dm@example.com", "pw")
        campaign = Campaign.objects.create(name="Tuesday Nighters", owner=user)
        location = orchestrator.save_location(
            a_location(), party_level=5, campaign=campaign
        )
        self.faction = Faction.objects.create(
            location=location,
            name="The Tide Wardens",
            faction_type="harbour guild",
            alignment="LN",
            description="Keepers of the sluice gates.",
            hierarchy=[
                {"level": 1, "tier": "leadership", "title": "Warden-General", "positions": 1},
                {"level": 2, "tier": "mob", "title": "Gate Guard", "positions": 2},
            ],
        )

    def a_character(self, **kwargs):
        fields = dict(
            name="Ysolde Marsh",
            race="Human",
            alignment=Alignment.LN,
            rank_title="Warden-General",
            description="A stern woman who counts the tides.",
            motivation="Wants the sluices kept shut at any cost; fears the city learning why.",
        )
        fields.update(kwargs)
        return GeneratedCharacter(**fields)

    def test_schema_requires_a_motivation(self):
        """Constrained decoding guarantees the field exists, so a sheet
        without one must not validate."""
        fields = self.a_character().model_dump()
        del fields["motivation"]
        with self.assertRaises(ValidationError):
            GeneratedCharacter(**fields)

    def test_named_character_saves_its_motivation(self):
        character = orchestrator.save_character(self.faction, self.a_character())
        character.refresh_from_db()
        self.assertIn("sluices", character.motivation)

    def test_mob_archetype_saves_its_motivation(self):
        archetype = MobArchetype(
            name="Sluice Guard",
            race="Human",
            alignment=Alignment.LN,
            rank_title="Gate Guard",
            description="Pole-armed watchmen.",
            motivation="Paid by the shift and afraid of the flooded district.",
            instance_names=["Tam", "Orrin"],
        )
        character = orchestrator.save_mob_archetype(self.faction, archetype)
        character.refresh_from_db()
        self.assertIn("flooded district", character.motivation)

    def test_roster_context_carries_motivation(self):
        orchestrator.save_character(self.faction, self.a_character())
        (generated,) = orchestrator.to_generated_characters(self.faction)
        self.assertIn("sluices", generated.motivation)

    def test_rows_that_predate_motivation_still_load(self):
        legacy = Character.objects.create(
            faction=self.faction,
            name="Old Hand",
            race="Human",
            alignment="TN",
            description="Written before motivations existed.",
            rank_title="Gate Guard",
        )
        self.assertEqual(legacy.motivation, "")
        (generated,) = orchestrator.to_generated_characters(self.faction)
        self.assertEqual(generated.motivation, "")

    def test_card_shows_motivation_only_when_present(self):
        with_motive = orchestrator.save_character(self.faction, self.a_character())
        without = Character.objects.create(
            faction=self.faction,
            name="Old Hand",
            race="Human",
            alignment="TN",
            description="Written before motivations existed.",
            rank_title="Gate Guard",
        )
        card = "populator/_character_card.html"
        self.assertIn("Motivation.", render_to_string(card, {"character": with_motive}))
        self.assertNotIn("Motivation.", render_to_string(card, {"character": without}))


def a_seed():
    """The smallest seed that exercises every collection and reference
    block: 4 exemplars plus 3 reference rows = 7 documents."""
    return {
        "meta": {"version": "test"},
        "taxonomy": {"environments": [{"id": "coastal"}]},
        "ip_guardrails": {"disclaimer": "test"},
        "locations": [
            {
                "id": "loc_t",
                "environment": "coastal",
                "genre": "swashbuckling",
                "payload": {
                    "name": "Gullwake",
                    "location_type": "harbour city",
                    "description": "d",
                    "summary": "s",
                },
            }
        ],
        "factions": [
            {
                "id": "fac_t",
                "location_id": "loc_t",
                "faction_category": "commerce",
                "payload": {
                    "name": "The Syndics",
                    "faction_type": "consortium",
                    "alignment": "CN",
                    "description": "d",
                    "hierarchy": [
                        {"level": 1, "tier": "leadership", "title": "Syndic", "positions": 1},
                        {"level": 2, "tier": "mob", "title": "Deckhand", "positions": 3},
                    ],
                },
            }
        ],
        "characters": [
            {
                "id": "chr_t",
                "faction_id": "fac_t",
                "rank_tier": "leadership",
                "class_hint": "Bard",
                "motivation_type": "legacy",
                "relationships": [],
                "payload": {
                    "name": "Ysa",
                    "race": "Human",
                    "alignment": "CN",
                    "rank_title": "Syndic",
                    "description": "d",
                    "motivation": "m",
                },
            }
        ],
        "mob_archetypes": [
            {
                "id": "mob_t",
                "faction_id": "fac_t",
                "class_hint": "Fighter",
                "motivation_type": "duty",
                "payload": {
                    "name": "Deckhand",
                    "race": "Human",
                    "alignment": "CN",
                    "rank_title": "Deckhand",
                    "description": "d",
                    "motivation": "m",
                    "instance_names": ["A", "B", "C"],
                },
            }
        ],
    }


class RagSeedTests(TestCase):
    """Seed loading: validated against the generation schemas, idempotent,
    and never able to clobber rows it does not own."""

    def test_load_stores_payload_and_metadata_separately(self):
        counts = rag.load_docs(rag.parse_seed(a_seed()))
        self.assertEqual(counts["created"], 7)
        location = RagDocument.objects.get(external_id="loc_t")
        self.assertEqual(location.doc_type, "location")
        self.assertEqual(location.source, "seed")
        self.assertEqual(location.payload["name"], "Gullwake")
        self.assertEqual(location.metadata, {"environment": "coastal", "genre": "swashbuckling"})

    def test_metadata_is_filterable_by_json_key(self):
        """Retrieval will be a JSON-key filter, so prove it works here."""
        rag.load_docs(rag.parse_seed(a_seed()))
        hits = RagDocument.objects.filter(doc_type="location", metadata__environment="coastal")
        self.assertEqual([d.external_id for d in hits], ["loc_t"])
        self.assertFalse(
            RagDocument.objects.filter(doc_type="location", metadata__environment="desert").exists()
        )

    def test_reload_is_idempotent_and_writes_only_changes(self):
        rag.load_docs(rag.parse_seed(a_seed()))
        again = rag.load_docs(rag.parse_seed(a_seed()))
        self.assertEqual(again, {"created": 0, "updated": 0, "unchanged": 7, "pruned": 0})

        edited = a_seed()
        edited["locations"][0]["payload"]["summary"] = "A new summary."
        counts = rag.load_docs(rag.parse_seed(edited))
        self.assertEqual((counts["updated"], counts["unchanged"]), (1, 6))
        self.assertEqual(
            RagDocument.objects.get(external_id="loc_t").payload["summary"], "A new summary."
        )

    def test_invalid_payload_is_rejected_naming_the_entry(self):
        seed = a_seed()
        del seed["characters"][0]["payload"]["motivation"]
        with self.assertRaises(rag.SeedError) as ctx:
            rag.parse_seed(seed)
        self.assertIn("chr_t", str(ctx.exception))
        self.assertIn("motivation", str(ctx.exception))

    def test_dangling_references_are_all_reported(self):
        seed = a_seed()
        seed["factions"][0]["location_id"] = "loc_missing"
        seed["characters"][0]["relationships"] = [{"to": "chr_missing", "type": "rival"}]
        with self.assertRaises(rag.SeedError) as ctx:
            rag.parse_seed(seed)
        self.assertEqual(len(ctx.exception.problems), 2)

    def test_duplicate_ids_are_rejected(self):
        seed = a_seed()
        seed["mob_archetypes"][0]["id"] = "chr_t"
        with self.assertRaises(rag.SeedError):
            rag.parse_seed(seed)

    def test_prune_removes_only_missing_seed_rows(self):
        rag.load_docs(rag.parse_seed(a_seed()))
        RagDocument.objects.create(
            external_id="approved_1", doc_type="character", source="dm_approved", payload={}
        )
        smaller = a_seed()
        smaller["mob_archetypes"] = []

        kept = rag.load_docs(rag.parse_seed(smaller))
        self.assertEqual(kept["pruned"], 0)
        self.assertTrue(RagDocument.objects.filter(external_id="mob_t").exists())

        pruned = rag.load_docs(rag.parse_seed(smaller), prune=True)
        self.assertEqual(pruned["pruned"], 1)
        self.assertFalse(RagDocument.objects.filter(external_id="mob_t").exists())
        self.assertTrue(RagDocument.objects.filter(external_id="approved_1").exists())

    def test_dry_run_reports_but_writes_nothing(self):
        counts = rag.load_docs(rag.parse_seed(a_seed()), dry_run=True)
        self.assertEqual(counts["created"], 7)
        self.assertEqual(RagDocument.objects.count(), 0)

    def test_conflict_with_a_foreign_row_aborts_the_whole_load(self):
        """mob_t is the fourth document, so three would already be
        created when the conflict hits: all of them must roll back."""
        RagDocument.objects.create(
            external_id="mob_t", doc_type="mob_archetype", source="dm_approved", payload={}
        )
        with self.assertRaises(rag.SeedError):
            rag.load_docs(rag.parse_seed(a_seed()))
        self.assertEqual(RagDocument.objects.count(), 1)

    def test_command_loads_a_file_and_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "seed.json"
            path.write_text(json.dumps(a_seed()), encoding="utf-8")
            out = StringIO()
            call_command("load_rag_seed", file=str(path), stdout=out)
        self.assertIn("7 created", out.getvalue())
        self.assertEqual(RagDocument.objects.count(), 7)

    def test_command_reports_a_bad_seed_and_saves_nothing(self):
        seed = a_seed()
        del seed["characters"][0]["payload"]["motivation"]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "seed.json"
            path.write_text(json.dumps(seed), encoding="utf-8")
            with self.assertRaises(CommandError) as ctx:
                call_command("load_rag_seed", file=str(path), stdout=StringIO())
        self.assertIn("chr_t", str(ctx.exception))
        self.assertEqual(RagDocument.objects.count(), 0)

    def test_command_reports_a_missing_file(self):
        with self.assertRaises(CommandError):
            call_command("load_rag_seed", file="no/such/seed.json", stdout=StringIO())

    @skipUnless(
        rag.default_seed_path().exists(),
        "prompts/rag/rag_seed.json is private and gitignored, so absent on other machines",
    )
    def test_the_real_seed_validates_and_loads(self):
        """Guards edits to the real seed: it must still satisfy the live
        schemas, load cleanly, reload unchanged, and keep every taxonomy
        environment covered by a location."""
        path = rag.default_seed_path()
        data = json.loads(path.read_text(encoding="utf-8"))
        docs = rag.parse_seed(data)

        self.assertEqual(rag.load_docs(docs)["created"], len(docs))
        self.assertEqual(rag.load_docs(docs)["unchanged"], len(docs))

        environments = {e["id"] for e in data["taxonomy"]["environments"]}
        covered = {
            d.metadata["environment"]
            for d in RagDocument.objects.filter(doc_type="location")
        }
        self.assertEqual(covered, environments)
