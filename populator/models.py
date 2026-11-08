from django.conf import settings
from django.db import models


class Campaign(models.Model):
    """The top-level container a DM owns: one campaign, many locations."""

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="campaigns",
    )

    def __str__(self):
        return self.name


class GenerationEvent(models.Model):
    """One API call: who asked, what for, which model, what it cost.

    Two jobs from one row. It is the ledger the daily cap counts against
    (playtesters spend real credit), and it is the cost telemetry that
    answers "what does a full location actually cost?" — which is a
    pricing question, not just a curiosity, once there are paid tiers.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="generation_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    kind = models.CharField(max_length=32)
    model = models.CharField(max_length=64)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)

    class Meta:
        # The cap query is always "this user, since a cutoff", so the
        # composite index matches it exactly.
        indexes = [models.Index(fields=["user", "created_at"])]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} {self.kind} ({self.model})"


class Location(models.Model):
    name = models.CharField(max_length=50)
    location_type = models.CharField(max_length=50)
    description = models.TextField()
    summary = models.TextField(blank=True, default="")
    party_level = models.IntegerField()
    image = models.ImageField(upload_to="location_images/", null=True, blank=True)
    prompt = models.TextField(null=True, blank=True)
    # Nullable for now so existing rows survive the migration; tighten
    # once all locations are assigned to campaigns.
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="locations",
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.name


class Faction(models.Model):
    name = models.CharField(max_length=50)
    alignment = models.CharField(max_length=2)
    faction_type = models.CharField(max_length=50)
    description = models.TextField()
    hierarchy = models.JSONField(default=list, blank=True)
    is_catchall = models.BooleanField(default=False)
    location = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name="factions"
    )
    image = models.ImageField(upload_to="faction_images/", null=True, blank=True)
    prompt = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name


class Character(models.Model):
    class RankTier(models.TextChoices):
        LEADERSHIP = "leadership"
        OFFICER = "officer"
        MEMBER = "member"
        MOB = "mob"

    rank_tier = models.CharField(
        max_length=10, choices=RankTier.choices, default=RankTier.MEMBER
    )
    rank_title = models.CharField(max_length=50, default="")
    name = models.CharField(max_length=50)
    description = models.TextField()
    motivation = models.TextField(blank=True, default="")
    alignment = models.CharField(max_length=2)
    race = models.CharField(max_length=50)
    profession = models.CharField(max_length=50, null=True)
    combat_sheet = models.JSONField(default=dict, null=True)
    image_hs = models.ImageField(
        upload_to="character_images/headshots", null=True, blank=True
    )
    image_iso = models.ImageField(
        upload_to="character_images/isometric", null=True, blank=True
    )
    faction = models.ForeignKey(
        Faction, on_delete=models.CASCADE, related_name="characters"
    )

    instances = models.JSONField(default=list, blank=True)
    # [{"name": "Sister Vex"}, {"name": "Brother Hollow"}, ...]

    def __str__(self):
        return self.name


class RagDocument(models.Model):
    """A retrieval exemplar or reference block for generation.

    Deliberately outside the ownership chain (campaign -> location ->
    faction -> character): these rows are shared, app-wide seed data. They
    live in their own table, never in Location/Faction/Character, so an
    exemplar can never appear on a DM's page as campaign content.

    `payload` holds the schema-valid body (it validates against the
    matching class in generation/schemas.py); `metadata` holds the
    retrieval keys (environment, genre, rank_tier, class_hint, ...), so
    retrieval is a JSON-key filter such as
    RagDocument.objects.filter(doc_type="location", metadata__environment="coastal").
    """

    class DocType(models.TextChoices):
        LOCATION = "location"
        FACTION = "faction"
        CHARACTER = "character"
        MOB_ARCHETYPE = "mob_archetype"
        # Whole-block lookups: taxonomy vocabularies, IP guardrails, seed meta.
        REFERENCE = "reference"

    doc_type = models.CharField(max_length=20, choices=DocType.choices)
    # Stable id from the seed file (e.g. "loc_coastal"), the upsert key.
    external_id = models.CharField(max_length=64, unique=True)
    # "seed" rows are owned by the loader: it may update or prune them.
    # Anything else (future DM-approved exemplars, say) is never touched.
    source = models.CharField(max_length=20, default="seed")
    metadata = models.JSONField(default=dict, blank=True)
    payload = models.JSONField(default=dict)
    # Reserved for the indexing step. A JSON list of floats works on
    # SQLite and Postgres alike; swap for pgvector if retrieval needs it.
    embedding = models.JSONField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["doc_type"])]
        ordering = ["doc_type", "external_id"]

    def __str__(self):
        return f"{self.doc_type}:{self.external_id}"
