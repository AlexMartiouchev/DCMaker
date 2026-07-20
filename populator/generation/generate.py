"""Generator functions: one per content type.

Each function formats a prompt template from prompts/engine/ with its
context and asks the client for a schema-validated result. No parsing,
no retry loops — the API guarantees the shape.

Character generation is slot-based: a faction's hierarchy (designed at
faction-generation time) defines the roster slots, and characters are
created to fill them — in batch during planning, or one at a time for
the (+) button / in-game use.

Run a quick end-to-end smoke test with:
    python -m populator.generation.generate "your location concept here"
"""

from pathlib import Path

from .client import generate
from .schemas import (
    CharacterSet,
    CombatSheet,
    FactionSet,
    GeneratedCharacter,
    GeneratedFaction,
    GeneratedLocation,
    MobArchetype,
    MobArchetypeSet,
    RankDefinition,
    RankTier,
)

# prompts/ lives at the repo root, two levels up from this file.
PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts" / "engine"


def _prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8")


SYSTEM = _prompt("system")


def generate_location(concept: str) -> GeneratedLocation:
    prompt = _prompt("location").format(concept=concept)
    return generate(prompt, GeneratedLocation, SYSTEM)


def generate_factions(
    location: GeneratedLocation,
    num_factions: int = 3,
    hints: str = "",
    existing: list[str] | None = None,
) -> list[GeneratedFaction]:
    """`existing` is short one-line summaries of factions already at the
    location, so additions (especially single ones) contrast rather
    than duplicate."""
    prompt = _prompt("factions").format(
        location_name=location.name,
        location_summary=location.summary,
        num_factions=num_factions,
        faction_hints=hints or "(none provided)",
        existing_factions="\n".join(f"- {line}" for line in existing) if existing else "(none yet)",
    )
    return generate(prompt, FactionSet, SYSTEM).factions


def _faction_context(location: GeneratedLocation, faction: GeneratedFaction) -> dict:
    return {
        "location_name": location.name,
        "location_summary": location.summary,
        "faction_name": faction.name,
        "faction_type": faction.faction_type,
        "faction_alignment": faction.alignment.value,
        "faction_description": faction.description,
    }


def _roster_lines(existing: list[GeneratedCharacter]) -> str:
    if not existing:
        return "(none yet)"
    return "\n".join(
        f"- {c.name} ({c.race}), {c.rank_title}" for c in existing
    )


def _other_faction_lines(other_factions: list[str] | None) -> str:
    if not other_factions:
        return "(none known)"
    return "\n".join(f"- {line}" for line in other_factions)


def fill_roster(
    location: GeneratedLocation,
    faction: GeneratedFaction,
    slots: list[RankDefinition],
    existing: list[GeneratedCharacter] | None = None,
    other_factions: list[str] | None = None,
) -> list[GeneratedCharacter]:
    """Fill several empty named-character slots in one call (planning
    mode). Mob-tier slots don't belong here — they become archetypes
    via generate_mob_archetypes.

    Sending the shared location/faction context once for the whole
    batch is much cheaper than one call per character. `slots` is
    whatever subset of faction.hierarchy the caller wants filled;
    positions counts are respected per slot.
    """
    slot_list = "\n".join(
        f"- {s.positions} x {s.title} ({s.tier.value} tier, level {s.level})"
        for s in slots
    )
    prompt = _prompt("roster_batch").format(
        slot_list=slot_list,
        existing_roster=_roster_lines(existing or []),
        other_factions=_other_faction_lines(other_factions),
        **_faction_context(location, faction),
    )
    return generate(prompt, CharacterSet, SYSTEM).characters


def generate_mob_archetypes(
    location: GeneratedLocation,
    faction: GeneratedFaction,
    slots: list[RankDefinition],
) -> list[MobArchetype]:
    """One archetype per mob-tier slot, generated together so they
    complement each other as a fighting force. Each archetype carries
    instance_names for its table copies instead of being N characters."""
    slot_list = "\n".join(
        f"- {s.title}: {s.positions} copies" for s in slots
    )
    prompt = _prompt("mob_archetypes").format(
        slot_list=slot_list,
        **_faction_context(location, faction),
    )
    return generate(prompt, MobArchetypeSet, SYSTEM).archetypes


def generate_character(
    location: GeneratedLocation,
    faction: GeneratedFaction,
    slot: RankDefinition,
    existing: list[GeneratedCharacter] | None = None,
    user_hints: str = "",
    other_factions: list[str] | None = None,
) -> GeneratedCharacter:
    """Fill one slot (the (+) button, a regenerate, or in-game use).

    `user_hints` is the DM's typed direction from the card's editable
    fields; empty means the model improvises from context.
    `other_factions` is short dossier lines on named figures elsewhere
    at the location, enabling cross-faction relationships.
    """
    prompt = _prompt("roster_single").format(
        rank_title=slot.title,
        rank_tier=slot.tier.value,
        user_hints=user_hints or "(none provided)",
        existing_roster=_roster_lines(existing or []),
        other_factions=_other_faction_lines(other_factions),
        **_faction_context(location, faction),
    )
    return generate(prompt, GeneratedCharacter, SYSTEM)


def slot_for_title(
    faction: GeneratedFaction, rank_title: str
) -> RankDefinition:
    """Find the hierarchy slot a character belongs to. Falls back to a
    mid-hierarchy member slot if the title isn't found (e.g. the DM
    typed a custom title)."""
    for rank in faction.hierarchy:
        if rank.title == rank_title:
            return rank
    return RankDefinition(
        level=3, tier=RankTier.MEMBER, title=rank_title, positions=1
    )


def generate_combat_sheet(
    character: GeneratedCharacter | MobArchetype,
    faction: GeneratedFaction,
    party_level: int,
    slot: RankDefinition,
) -> CombatSheet:
    """Stat one character or mob archetype. The slot's tier and level
    drive power scaling: level 1 = apex threat (and the only legitimate
    holder of legendary actions), mobs = balanced for group fights."""
    prompt = _prompt("combat_sheet").format(
        character_name=character.name,
        rank_title=slot.title,
        rank_tier=slot.tier.value,
        rank_level=slot.level,
        character_race=character.race,
        character_description=character.description,
        faction_name=faction.name,
        faction_description=faction.description,
        party_level=party_level,
    )
    return generate(prompt, CombatSheet, SYSTEM)


if __name__ == "__main__":
    import sys

    concept = " ".join(sys.argv[1:]) or "Archipelago of sky islands kept aloft through forgotten magic"
    print(f"Generating location for concept: {concept!r}\n")

    location = generate_location(concept)
    print(f"=== {location.name} ({location.location_type}) ===\n")
    print(location.description, "\n")

    factions = generate_factions(location, num_factions=2)
    for faction in factions:
        print(f"--- {faction.name} [{faction.faction_type}, {faction.alignment.value}] ---")
        print(faction.description)
        print("Hierarchy:")
        for rank in sorted(faction.hierarchy, key=lambda r: r.level):
            print(f"  L{rank.level}: {rank.positions} x {rank.title} [{rank.tier.value}]")
        print()

    # Fill only the leadership slots of the first faction (keeps the
    # smoke test cheap); a real planning pass would send the full hierarchy.
    faction = factions[0]
    lead_slots = [r for r in faction.hierarchy if r.tier is RankTier.LEADERSHIP]
    roster = fill_roster(location, faction, lead_slots)
    for character in roster:
        print(f"*** {character.name} ({character.race}, {character.alignment.value}) — {character.rank_title} ***")
        print(character.description, "\n")

    sheet = generate_combat_sheet(
        roster[0], faction, party_level=6, slot=slot_for_title(faction, roster[0].rank_title)
    )
    print(f"{sheet.profession} | HP {sheet.stats.hp} | AC {sheet.stats.ac}")
    for action in sheet.actions:
        print(f"  Action: {action.name} — {action.description}")
    for ability in sheet.abilities:
        print(f"  Ability: {ability.name} — {ability.description}")
