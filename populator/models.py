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
