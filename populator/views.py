"""User-facing pages: campaign-first navigation.

Campaigns -> campaign detail (locations) -> location detail (factions)
-> faction detail (hierarchy with character cards). Read-only skeleton;
generation buttons arrive with htmx in the next phase.

Every query filters by the logged-in user's ownership chain, so users
can only ever see their own campaigns' content.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .models import Campaign, Faction, Location


@login_required
def campaign_list(request):
    campaigns = Campaign.objects.filter(owner=request.user)
    return render(request, "populator/campaign_list.html", {"campaigns": campaigns})


@login_required
def campaign_detail(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk, owner=request.user)
    return render(request, "populator/campaign_detail.html", {"campaign": campaign})


@login_required
def location_detail(request, pk):
    location = get_object_or_404(Location, pk=pk, campaign__owner=request.user)
    return render(request, "populator/location_detail.html", {"location": location})


@login_required
def faction_detail(request, pk):
    faction = get_object_or_404(
        Faction, pk=pk, location__campaign__owner=request.user
    )

    # Group characters by their rank in the faction's hierarchy, ordered
    # by level. Characters whose rank_title matches no hierarchy rank
    # (DM-invented titles) get their own trailing groups.
    by_title: dict[str, list] = {}
    for character in faction.characters.all():
        by_title.setdefault(character.rank_title, []).append(character)

    groups = []
    for rank in sorted(faction.hierarchy, key=lambda r: r.get("level", 99)):
        characters = by_title.pop(rank["title"], [])
        groups.append(
            {
                "rank": rank,
                "characters": characters,
                "empty_slots": range(max(0, rank["positions"] - len(characters)))
                if rank["tier"] != "mob"
                else range(0 if characters else 1),
            }
        )
    for title, characters in by_title.items():
        groups.append({"rank": {"title": title, "tier": "", "positions": len(characters)}, "characters": characters, "empty_slots": range(0)})

    return render(
        request,
        "populator/faction_detail.html",
        {"faction": faction, "groups": groups},
    )
