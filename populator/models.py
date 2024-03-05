from django.db import models

class Location(models.Model):
    name = models.CharField(max_length=50)
    location_type = models.CharField(max_length=50)
    description = models.TextField()
    party_size = models.IntegerField()
    party_level = models.IntegerField()

    def __str__(self):
        return self.name

class Faction(models.Model):
    name = models.CharField(max_length=50)
    faction_type = models.CharField(max_length=50)
    description = models.TextField()
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='factions')

    def __str__(self):
        return self.name

class Character(models.Model):
    name = models.CharField(max_length=50)
    lead = models.BooleanField()
    profession = models.CharField(max_length=50)
    description = models.TextField()
    stats = models.CharField(max_length=100)
    actions = models.TextField(null=True)
    abilities = models.TextField(null=True)
    faction = models.ForeignKey(Faction, on_delete=models.CASCADE, related_name='characters')

    def __str__(self):
        return self.name


#  setting up user objects here as a reminder for post demo work
# class UserProfile(models.Model):
#     user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True)

#     def __str__(self):
#         return f"{self.user.username}'s profile"


class Demo(models.Model):
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True)
    factions = models.ManyToManyField(Faction)
    characters = models.ManyToManyField(Character)
