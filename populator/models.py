from django.db import models

class Location(models.Model):
    name = models.CharField(max_length=50)
    location_type = models.CharField(max_length=50)
    description = models.TextField()
    parent_location = models.ForeignKey(
        'self',
        on_delete=models.CASCADE, 
        related_name='sublocations', 
        null=True, 
        blank=True
    )

    def __str__(self):
        return self.name

class Faction(models.Model):
    name = models.CharField(max_length=50)
    faction_type = models.CharField(max_length=50)
    description = models.TextField()
    base_location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        related_name="base_factions",
        null=True,
        blank=True,
        limit_choices_to={'parent_location__isnull': False} 
    )

    def __str__(self):
        return self.name

class Character(models.Model):
    name = models.CharField(max_length=50)
    role = models.CharField(max_length=50)
    profession = models.CharField(max_length=50)
    description = models.TextField()
    stats = models.CharField(max_length=100)
    abilities = models.TextField()
    faction = models.ManyToManyField(
        Faction,
        blank=True,
        related_name="characters",
    )
    frequent_locations = models.ManyToManyField(
        Location,
        blank=True,
        related_name="frequent_characters",
    )

    def __str__(self):
        return self.name


#  setting up user objects here as a reminder for post demo work
# class UserProfile(models.Model):
#     user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True)
#     factions = models.ManyToManyField(Faction, blank=True)
#     characters = models.ManyToManyField(Character, blank=True)

#     def __str__(self):
#         return f"{self.user.username}'s profile"


class Demo(models.Model):
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True)
    factions = models.ManyToManyField(Faction)
    characters = models.ManyToManyField(Character)
