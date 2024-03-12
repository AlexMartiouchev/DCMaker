from django.urls import path

from . import views


urlpatterns = [
    path("", views.index, name="index"),
    path("populator", views.populator, name="populator"),
    path("populator/demo/", views.demo, name="demo"),
    path("populator/demo/location/", views.demo_location, name="demo_location"),
    path("populator/demo/factions/", views.demo_factions, name="demo_factions"),
    path("populator/demo/characters/", views.demo_characters, name="demo_characters"),
    path("populator/demo/summary/", views.demo_summary, name="demo_summary"),
]
