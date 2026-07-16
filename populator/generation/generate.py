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
    location: GeneratedLocation, num_factions: int = 3
) -> list[GeneratedFaction]:
    prompt = _prompt("factions").format(
        location_name=location.name,
        location_summary=location.summary,
        num_factions=num_factions,
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


def fill_roster(
    location: GeneratedLocation,
    faction: GeneratedFaction,
    slots: list[RankDefinition],
    existing: list[GeneratedCharacter] | None = None,
) -> list[GeneratedCharacter]:
    """Fill several empty slots in one call (planning mode).

    Sending the shared location/faction context once for the whole
    batch is much cheaper than one call per character. `slots` is
    whatever subset of faction.hierarchy the caller wants filled;
    positions counts are respected per slot.
    """
    slot_list = "\n".join(
        f"- {s.positions} x {s.title} ({s.tier.value} tier)" for s in slots
    )
    prompt = _prompt("roster_batch").format(
        slot_list=slot_list,
        existing_roster=_roster_lines(existing or []),
        **_faction_context(location, faction),
    )
    return generate(prompt, CharacterSet, SYSTEM).characters


def generate_character(
    location: GeneratedLocation,
    faction: GeneratedFaction,
    slot: RankDefinition,
    existing: list[GeneratedCharacter] | None = None,
    user_hints: str = "",
) -> GeneratedCharacter:
    """Fill one slot (the (+) button, a regenerate, or in-game use).

    `user_hints` is the DM's typed direction from the card's editable
    fields; empty means the model improvises from context.
    """
    prompt = _prompt("roster_single").format(
        rank_title=slot.title,
        rank_tier=slot.tier.value,
        user_hints=user_hints or "(none provided)",
        existing_roster=_roster_lines(existing or []),
        **_faction_context(location, faction),
    )
    return generate(prompt, GeneratedCharacter, SYSTEM)


def generate_combat_sheet(
    character: GeneratedCharacter,
    faction: GeneratedFaction,
    party_level: int,
    tier: RankTier,
) -> CombatSheet:
    """Stat one character, on demand. Mob-tier characters are balanced
    to be fought in groups; everyone else matches or beats a single
    party member of the same level."""
    prompt = _prompt("combat_sheet").format(
        character_name=character.name,
        character_type="Mob" if tier is RankTier.MOB else "Lead",
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
        for rank in faction.hierarchy:
            reports = f" -> reports to {rank.reports_to}" if rank.reports_to else " (top)"
            print(f"  {rank.positions} x {rank.title} [{rank.tier.value}]{reports}")
        print()

    # Fill only the leadership slots of the first faction (keeps the
    # smoke test cheap); a real planning pass would send the full hierarchy.
    faction = factions[0]
    lead_slots = [r for r in faction.hierarchy if r.tier is RankTier.LEADERSHIP]
    roster = fill_roster(location, faction, lead_slots)
    for character in roster:
        print(f"*** {character.name} ({character.race}, {character.alignment.value}) — {character.rank_title} ***")
        print(character.description, "\n")

    sheet = generate_combat_sheet(roster[0], faction, party_level=6, tier=RankTier.LEADERSHIP)
    print(f"{sheet.profession} | HP {sheet.stats.hp} | AC {sheet.stats.ac}")
    for action in sheet.actions:
        print(f"  Action: {action.name} — {action.description}")
    for ability in sheet.abilities:
        print(f"  Ability: {ability.name} — {ability.description}")
