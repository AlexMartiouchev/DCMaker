from django.shortcuts import redirect, render
from models import Location, Faction, Character


def index(request):
    return render(request, "populator/index.html")


def populator(request):
    return render(request, "populator/populator.html")


def demo(request):
    return render(request, "populator/demo/demo_index.html")


def demo_location(request):
    if request.method == "POST":
        selected_location_id = request.POST.get("selected_location_id")
        request.session["selected_location_id"] = selected_location_id
        return redirect("demo_factions")
    else:
        demo_locations = Location.objects.filter(demo__isnull=False)
        return render(
            request,
            "populator/demo/demo_location.html",
            {"demo_locations": demo_locations},
        )


def demo_factions(request):
    selected_location_id = request.session.get("selected_location_id")
    factions = Faction.objects.filter(location_id=selected_location_id)
    if request.method == "POST":
        selected_faction_ids = request.POST.getlist("selected_faction_ids")
        request.session["selected_faction_ids"] = selected_faction_ids
        return redirect("demo_characters")
    else:
        return render(
            request, "populator/demo/demo_factions.html", {"factions": factions}
        )


def demo_characters(request):
    selected_location_id = request.session.get("selected_location_id")
    factions = Faction.objects.filter(location_id=selected_location_id)
    selected_faction_ids = request.session.get("selected_faction_ids")
    characters = Character.objects.filter(faction_id__in=selected_faction_ids)
    return render(
        request,
        "populator/demo/demo_characters.html",
        {"factions": factions, "characters": characters},
    )


def demo_summary(request):
    return render(request, "populator/demo/demo_summary.html")
