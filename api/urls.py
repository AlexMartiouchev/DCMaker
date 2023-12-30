from django.urls import path
from . import views

urlpatterns = [
    path("lore-maker/", views.lore_maker_endpoint, name="lore_maker_endpoint"),
]
