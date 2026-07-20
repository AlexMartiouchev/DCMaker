from django.urls import path

from . import views


urlpatterns = [
    path("", views.campaign_list, name="campaign_list"),
    path("campaigns/create/", views.campaign_create, name="campaign_create"),
    path("campaigns/<int:pk>/", views.campaign_detail, name="campaign_detail"),
    path(
        "campaigns/<int:pk>/generate-location/",
        views.generate_location_slot,
        name="generate_location_slot",
    ),
    path(
        "locations/<int:pk>/generate-factions/",
        views.generate_faction_slots,
        name="generate_faction_slots",
    ),
    path("locations/<int:pk>/", views.location_detail, name="location_detail"),
    path("factions/<int:pk>/", views.faction_detail, name="faction_detail"),
    path(
        "factions/<int:pk>/generate/",
        views.generate_character_slot,
        name="generate_character_slot",
    ),
    path(
        "factions/<int:pk>/generate-roster/",
        views.generate_roster_batch,
        name="generate_roster_batch",
    ),
    path("factions/<int:pk>/delete/", views.faction_delete, name="faction_delete"),
    path(
        "characters/<int:pk>/delete/",
        views.character_delete,
        name="character_delete",
    ),
]
