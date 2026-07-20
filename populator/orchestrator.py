"""The bridge between the generation engine and the Django models.

The engine (populator/generation/) is Django-free and returns pydantic
objects that live only in memory; this module persists each one as a
database row and wires the relationships. One save function per step,
so views (and the generate_demo management command) can drive the
co-pilot flow step-by-step — a failed step loses only itself.
"""

from .generation.schemas import (
    CombatSheet,
    GeneratedCharacter,
    GeneratedFaction,
    GeneratedLocation,
    MobArchetype,
    RankDefinition,
)
from .models import Campaign, Character, Faction, Location


# --- DB -> pydantic reconstruction ----------------------------------------
# The UI generates one card at a time against *stored* campaign data, so
# the engine's context objects are rebuilt from rows rather than carried
# over from a live pipeline run.


def to_generated_location(location: Location) -> GeneratedLocation:
    return GeneratedLocation(
        name=location.name,
        location_type=location.location_type,
        description=location.description,
        summary=location.summary or location.description,
    )


def to_generated_faction(faction: Faction) -> GeneratedFaction:
    return GeneratedFaction(
        name=faction.name,
        faction_type=faction.faction_type,
        alignment=faction.alignment,
        description=faction.description,
        hierarchy=[RankDefinition(**rank) for rank in faction.hierarchy],
    )


def other_faction_dossier(faction: Faction) -> list[str]:
    """Short lines on named figures in the location's *other* factions,
    so new characters can carry cross-faction relationships. Named
    tiers only — mob flavor would dilute the context for no gain."""
    lines = []
    others = faction.location.factions.exclude(pk=faction.pk).filter(
        is_catchall=False
    )
    for other in others:
        for ch in other.characters.exclude(rank_tier=Character.RankTier.MOB):
            snippet = ch.description.split(".")[0][:120]
            lines.append(
                f"{ch.name} — {ch.rank_title} ({ch.rank_tier}) of {other.name}: {snippet}"
            )
    return lines


def to_generated_characters(faction: Faction) -> list[GeneratedCharacter]:
    """Existing roster as engine context (so new characters don't clash)."""
    return [
        GeneratedCharacter(
            name=c.name,
            race=c.race,
            alignment=c.alignment,
            rank_title=c.rank_title,
            description=c.description,
        )
        for c in faction.characters.all()
    ]


def save_location(
    generated: GeneratedLocation, party_level: int, campaign: Campaign | None = None
) -> Location:
    return Location.objects.create(
        name=generated.name,
        location_type=generated.location_type,
        description=generated.description,
        summary=generated.summary,
        party_level=party_level,
        campaign=campaign,
    )


def save_faction(location: Location, generated: GeneratedFaction) -> Faction:
    return Faction.objects.create(
        location=location,
        name=generated.name,
        faction_type=generated.faction_type,
        alignment=generated.alignment.value,
        description=generated.description,
        # mode="json" flattens the RankTier enums to plain strings so the
        # list is storable in a JSONField.
        hierarchy=[rank.model_dump(mode="json") for rank in generated.hierarchy],
    )


def tier_for_title(faction: Faction, rank_title: str) -> str:
    """Look up which tier a rank title belongs to in the faction's
    hierarchy. Falls back to member if the title isn't found (e.g. the
    DM invented a title on the fly)."""
    for rank in faction.hierarchy:
        if rank["title"] == rank_title:
            return rank["tier"]
    return Character.RankTier.MEMBER


def save_character(faction: Faction, generated: GeneratedCharacter) -> Character:
    return Character.objects.create(
        faction=faction,
        name=generated.name,
        race=generated.race,
        alignment=generated.alignment.value,
        description=generated.description,
        rank_title=generated.rank_title,
        rank_tier=tier_for_title(faction, generated.rank_title),
    )


def save_mob_archetype(faction: Faction, archetype: MobArchetype) -> Character:
    """A mob archetype is one Character row; its table copies live in
    the instances JSON, not as separate rows."""
    return Character.objects.create(
        faction=faction,
        name=archetype.name,
        race=archetype.race,
        alignment=archetype.alignment.value,
        description=archetype.description,
        rank_title=archetype.rank_title,
        rank_tier=Character.RankTier.MOB,
        instances=[{"name": name} for name in archetype.instance_names],
    )


def save_combat_sheet(character: Character, sheet: CombatSheet) -> Character:
    """Sheets are generated on demand, so this updates an existing row
    rather than creating one."""
    character.profession = sheet.profession
    character.combat_sheet = sheet.model_dump(mode="json", exclude={"profession"})
    character.save()
    return character


def unaffiliated_faction(location: Location) -> Faction:
    """Return the location's catch-all faction for unaffiliated
    characters, creating it on first use."""
    faction, created = location.factions.get_or_create(
        is_catchall=True,
        defaults={
            "name": "Unaffiliated",
            "faction_type": "catch-all",
            "alignment": "TN",
            "description": f"Unaffiliated denizens of {location.name}",
            "hierarchy": [],
        },
    )
    return faction
