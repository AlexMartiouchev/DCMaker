from django.contrib import admin

from .models import Campaign, Location, Faction, Character

admin.site.register(Campaign)
admin.site.register(Location)
admin.site.register(Faction)
admin.site.register(Character)
