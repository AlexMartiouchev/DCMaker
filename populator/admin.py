from django.contrib import admin

from .models import Location, Faction, Character, Demo

admin.site.register(Location)
admin.site.register(Faction)
admin.site.register(Character)
admin.site.register(Demo)
