from django.db import models


class Location(models.Model):
    name = models.CharField(max_length=50)
    location_type = models.CharField(max_length=50)
    description = models.CharField(max_length=1000)

    def __str__(self):
        return self.name


class Faction(models.Model):
    name = models.CharField(max_length=50)
    faction_type = models.CharField(max_length=50)
    description = models.CharField(max_length=1000)
    base_location = models.ForeignKey(
        Location,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="base_factions",
    )
    affiliated_locations = models.ManyToManyField(
        Location,
        blank=True,
        related_name="affiliated_factions",
    )

    def __str__(self):
        return self.name


class Character(models.Model):
    name = models.CharField(max_length=50)
    role = models.CharField(max_length=50)
    profession = models.CharField(max_length=50)
    description = models.CharField(max_length=1000)
    stats = models.CharField(max_length=100)
    abilities = models.CharField(max_length=500)
    faction = models.ManyToManyField(
        Faction,
        blank=True,
        related_name="characters",
    )
    location = models.ForeignKey(
        Location,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="characters",
    )

    def __str__(self):
        return self.name
