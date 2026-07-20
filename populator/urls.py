from django.urls import path

from . import views


urlpatterns = [
    path("", views.campaign_list, name="campaign_list"),
    path("campaigns/<int:pk>/", views.campaign_detail, name="campaign_detail"),
    path("locations/<int:pk>/", views.location_detail, name="location_detail"),
    path("factions/<int:pk>/", views.faction_detail, name="faction_detail"),
]
