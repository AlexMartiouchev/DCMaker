"""User-facing pages: campaign-first navigation.

Campaigns -> campaign detail (locations) -> location detail (factions)
-> faction detail (hierarchy with character cards). Read-only skeleton;
generation buttons arrive with htmx in the next phase.

Every query filters by the logged-in user's ownership chain, so users
can only ever see their own campaigns' content.
"""

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_POST

from . import orchestrator
from .generation import generate as engine
from .generation.schemas import RankTier
from .models import Campaign, Character, Faction, Location


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

    # Named ranks get their own sections ordered by level; all mob-tier
    # content is consolidated into one "Mobs" section. Titles are
    # matched fuzzily (parentheticals stripped, case-insensitive) since
    # the model sometimes decorates rank titles with descriptions.
    def clean(title):
        return title.split("(")[0].strip().lower()

    by_title: dict[str, list] = {}
    stray_mobs = []
    for character in faction.characters.all():
        if character.rank_tier == "mob":
            stray_mobs.append(character)
        else:
            by_title.setdefault(clean(character.rank_title), []).append(character)

    groups = []
    mob_archetypes, mob_unfilled = [], []
    for rank in sorted(faction.hierarchy, key=lambda r: r.get("level", 99)):
        if rank["tier"] == "mob":
            matched = [
                m for m in stray_mobs if clean(m.rank_title) == clean(rank["title"])
            ]
            if matched:
                mob_archetypes.extend(matched)
                stray_mobs = [m for m in stray_mobs if m not in matched]
            else:
                mob_unfilled.append(rank)
            continue
        characters = by_title.pop(clean(rank["title"]), [])
        groups.append(
            {
                "rank": rank,
                "characters": characters,
                "remaining": max(0, rank["positions"] - len(characters)),
            }
        )
    for title, characters in by_title.items():
        groups.append(
            {
                "rank": {"title": characters[0].rank_title, "tier": "", "positions": len(characters)},
                "characters": characters,
                "remaining": 0,
            }
        )
    mob_archetypes.extend(stray_mobs)  # mobs with no matching rank still display

    return render(
        request,
        "populator/faction_detail.html",
        {
            "faction": faction,
            "groups": groups,
            "mob_archetypes": mob_archetypes,
            "mob_unfilled": mob_unfilled,
            "has_characters": faction.characters.exists(),
        },
    )


@login_required
@require_POST
def generate_roster_batch(request, pk):
    """Fill the faction's whole hierarchy in one go: named characters
    (one batch call), mob archetypes (one call), sheets for everyone.
    The button only shows on empty factions, so no duplicate risk."""
    faction = get_object_or_404(
        Faction, pk=pk, location__campaign__owner=request.user
    )
    gen_location = orchestrator.to_generated_location(faction.location)
    gen_faction = orchestrator.to_generated_faction(faction)
    party_level = faction.location.party_level

    named_slots = [s for s in gen_faction.hierarchy if s.tier is not RankTier.MOB]
    mob_slots = [s for s in gen_faction.hierarchy if s.tier is RankTier.MOB]

    if named_slots:
        for generated in engine.fill_roster(
            gen_location,
            gen_faction,
            named_slots,
            other_factions=orchestrator.other_faction_dossier(faction),
        ):
            character = orchestrator.save_character(faction, generated)
            sheet = engine.generate_combat_sheet(
                generated, gen_faction, party_level,
                engine.slot_for_title(gen_faction, generated.rank_title),
            )
            orchestrator.save_combat_sheet(character, sheet)
    if mob_slots:
        for archetype in engine.generate_mob_archetypes(
            gen_location, gen_faction, mob_slots
        ):
            character = orchestrator.save_mob_archetype(faction, archetype)
            sheet = engine.generate_combat_sheet(
                archetype, gen_faction, party_level,
                engine.slot_for_title(gen_faction, archetype.rank_title),
            )
            orchestrator.save_combat_sheet(character, sheet)

    return redirect("faction_detail", pk=faction.pk)


@login_required
@require_POST
def character_delete(request, pk):
    """htmx endpoint: delete one character; the card swaps to nothing."""
    character = get_object_or_404(
        Character, pk=pk, faction__location__campaign__owner=request.user
    )
    character.delete()
    return HttpResponse("")


@login_required
@require_POST
def faction_delete(request, pk):
    """htmx endpoint: delete a faction (cascades to its characters),
    then send the browser to the location page."""
    faction = get_object_or_404(
        Faction, pk=pk, location__campaign__owner=request.user
    )
    location_pk = faction.location.pk
    faction.delete()
    response = HttpResponse("")
    response["HX-Redirect"] = reverse("location_detail", args=[location_pk])
    return response


@login_required
@require_POST
def campaign_create(request):
    """Plain form, no AI: a campaign is just a named container."""
    campaign = Campaign.objects.create(
        name=request.POST.get("name", "").strip() or "Untitled Campaign",
        description=request.POST.get("description", "").strip(),
        owner=request.user,
    )
    return redirect("campaign_detail", pk=campaign.pk)


@login_required
@require_POST
def generate_location_slot(request, pk):
    """htmx endpoint: generate a location from the DM's concept and
    return its card fragment."""
    campaign = get_object_or_404(Campaign, pk=pk, owner=request.user)
    concept = request.POST.get("concept", "").strip() or "A memorable adventuring locale"
    try:
        party_level = int(request.POST.get("party_level", 5))
    except ValueError:
        party_level = 5

    generated = engine.generate_location(concept)
    location = orchestrator.save_location(
        generated, party_level=party_level, campaign=campaign
    )
    return render(request, "populator/_location_card.html", {"location": location})


@login_required
@require_POST
def generate_faction_slots(request, pk):
    """htmx endpoint: generate N factions (with hierarchies) for a
    location and return their card fragments. Characters are then
    generated slot-by-slot on each faction's own page."""
    location = get_object_or_404(Location, pk=pk, campaign__owner=request.user)
    try:
        num_factions = max(1, min(int(request.POST.get("num_factions", 3)), 5))
    except ValueError:
        num_factions = 3
    hints = request.POST.get("hints", "").strip()
    existing = [
        f"{f.name} ({f.faction_type}, {f.alignment})"
        for f in location.factions.filter(is_catchall=False)
    ]

    gen_location = orchestrator.to_generated_location(location)
    factions = [
        orchestrator.save_faction(location, generated)
        for generated in engine.generate_factions(
            gen_location, num_factions, hints=hints, existing=existing
        )
    ]
    return render(request, "populator/_faction_cards.html", {"factions": factions})


@login_required
@require_POST
def generate_character_slot(request, pk):
    """htmx endpoint: fill one empty slot. Returns a single character
    card fragment that swaps in place of the empty-slot form."""
    faction = get_object_or_404(
        Faction, pk=pk, location__campaign__owner=request.user
    )
    rank_title = request.POST.get("rank_title", "")
    hints = request.POST.get("hints", "").strip()

    gen_location = orchestrator.to_generated_location(faction.location)
    gen_faction = orchestrator.to_generated_faction(faction)
    slot = engine.slot_for_title(gen_faction, rank_title)
    # The mob (+) form lets the DM invent a new archetype type; honor
    # the requested tier when the title isn't in the hierarchy.
    if request.POST.get("tier") == "mob" and slot.tier is not RankTier.MOB:
        slot = engine.RankDefinition(
            level=slot.level, tier=RankTier.MOB, title=slot.title, positions=3
        )
    party_level = faction.location.party_level

    if slot.tier is RankTier.MOB:
        archetype = engine.generate_mob_archetypes(gen_location, gen_faction, [slot])[0]
        character = orchestrator.save_mob_archetype(faction, archetype)
        sheet_subject = archetype
    else:
        generated = engine.generate_character(
            gen_location,
            gen_faction,
            slot,
            existing=orchestrator.to_generated_characters(faction),
            user_hints=hints,
            other_factions=orchestrator.other_faction_dossier(faction),
        )
        character = orchestrator.save_character(faction, generated)
        sheet_subject = generated

    sheet = engine.generate_combat_sheet(sheet_subject, gen_faction, party_level, slot)
    orchestrator.save_combat_sheet(character, sheet)

    # Return the new card — plus a fresh slot form if this rank still
    # has unfilled positions, so filling flows without page reloads.
    html = render_to_string(
        "populator/_character_card.html", {"character": character}, request
    )
    try:
        remaining = int(request.POST.get("remaining", 1)) - 1
    except ValueError:
        remaining = 0
    if remaining > 0:
        html += render_to_string(
            "populator/_slot_form.html",
            {
                "faction": faction,
                "rank_title": rank_title,
                "remaining": remaining,
                "tier": request.POST.get("tier", ""),
            },
            request,
        )
    return HttpResponse(html)
