from django.conf import settings
from django.db import models


class Location(models.Model):
    name = models.CharField(max_length=50)
    location_type = models.CharField(max_length=50)
    description = models.TextField()
    party_level = models.IntegerField()
    image = models.ImageField(upload_to="location_images/", null=True, blank=True)
    prompt = models.TextField(null=True, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
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
    location = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name="factions"
    )
    image = models.ImageField(upload_to="faction_images/", null=True, blank=True)
    prompt = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name


class Character(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField()
    alignment = models.CharField(max_length=2)
    lead = models.BooleanField()
    race = models.CharField(max_length=20)
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

    def __str__(self):
        return self.name


class Demo(models.Model):
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True)
