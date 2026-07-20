from django.contrib import admin

from .models import Campaign, Location, Faction, Character


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "owner")


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "location_type", "party_level", "campaign")
    list_filter = ("campaign",)


@admin.register(Faction)
class FactionAdmin(admin.ModelAdmin):
    list_display = ("name", "faction_type", "alignment", "location", "is_catchall")
    list_filter = ("location", "is_catchall")


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ("name", "rank_title", "rank_tier", "faction")
    list_filter = ("faction__location__campaign", "faction__location", "rank_tier")
    search_fields = ("name", "rank_title")
