"""Pydantic schemas for structured-output generation.

Each class here does double duty:
  1. Sent to the LLM API as a JSON schema, constraining what it can return.
  2. The typed, validated Python object we get back.

Field descriptions are visible to the model and steer what it writes,
so treat them as part of the prompt.
"""

from enum import Enum

from pydantic import BaseModel, Field


class Alignment(str, Enum):
    """The nine D&D alignments, as stored in the Django models."""

    LG = "LG"
    NG = "NG"
    CG = "CG"
    LN = "LN"
    TN = "TN"
    CN = "CN"
    LE = "LE"
    NE = "NE"
    CE = "CE"


class GeneratedLocation(BaseModel):
    name: str = Field(description="Evocative location name, under 50 characters")
    location_type: str = Field(
        description="Short category, e.g. 'floating archipelago', 'ruined city', 'jungle temple'"
    )
    description: str = Field(
        description=(
            "2-3 rich paragraphs for the DM: geography, atmosphere, history, "
            "and the tensions that make it a good adventure setting"
        )
    )
    summary: str = Field(
        description=(
            "One tight paragraph capturing the location's essence, used as "
            "context when generating factions and characters"
        )
    )


class RankTier(str, Enum):
    """Structural layer of a rank — what the UI groups character cards by.

    The faction-flavored *name* of a rank lives in RankDefinition.title;
    this enum is the machine-readable layer underneath it.
    """

    LEADERSHIP = "leadership"
    OFFICER = "officer"
    MEMBER = "member"
    MOB = "mob"


class RankDefinition(BaseModel):
    """One rung of a faction's hierarchy, designed by the model when the
    faction itself is generated. positions -> how many character card
    slots the UI pre-renders for this rank."""

    tier: RankTier
    title: str = Field(
        description=(
            "Faction-flavored rank name, e.g. 'The Dark One', 'Veil-Speaker', "
            "'Dock Boss', 'Initiate'"
        )
    )
    positions: int = Field(
        description=(
            "How many characters hold this rank. Leadership ranks: 1-3. "
            "Mob ranks: 2-6 generic rank-and-file combatants."
        )
    )
    reports_to: str | None = Field(
        description=(
            "The title of the rank this one answers to, exactly as written in "
            "this hierarchy. null only for the top rank."
        )
    )


class GeneratedFaction(BaseModel):
    name: str = Field(description="Faction name, under 50 characters")
    faction_type: str = Field(
        description="Short category, e.g. 'thieves guild', 'merchant house', 'druidic circle'"
    )
    alignment: Alignment
    description: str = Field(
        description=(
            "1-2 paragraphs: the faction's goals, methods, and its "
            "relationship to the location and rival factions"
        )
    )
    hierarchy: list[RankDefinition] = Field(
        description=(
            "The faction's org chart, 3-6 ranks. Choose a structure that fits "
            "the faction: lone commander, council of equals, prophet with an "
            "inner circle. Include at least one mob-tier rank for the generic "
            "rank-and-file."
        )
    )


class FactionSet(BaseModel):
    """Wrapper so one API call returns several factions together —
    generating them jointly makes the model give them contrasting
    goals instead of five copies of the same guild."""

    factions: list[GeneratedFaction]


class AbilityScores(BaseModel):
    """Classic six-stat block plus derived combat numbers."""

    hp: int = Field(description="Hit points appropriate to the party level")
    ac: int = Field(description="Armor class")
    strength: int
    dexterity: int
    constitution: int
    intelligence: int
    wisdom: int
    charisma: int


class NamedEffect(BaseModel):
    """An action or ability: a name plus its rules text."""

    name: str
    description: str = Field(
        description="Rules text including to-hit/damage or effect, kept to 1-2 sentences"
    )


class CombatSheet(BaseModel):
    profession: str = Field(
        description="Class or role, e.g. 'Rogue', 'Storm Cleric', 'Sellsword'"
    )
    stats: AbilityScores
    actions: list[NamedEffect] = Field(
        description="2-4 combat actions the character can take"
    )
    abilities: list[NamedEffect] = Field(
        description="1-3 passive or special abilities"
    )


class GeneratedCharacter(BaseModel):
    name: str = Field(
        description=(
            "Personal name for leadership/officer/member characters, under 50 "
            "characters. Mob-tier characters get generic descriptive names "
            "instead, e.g. 'Sword-wielding Guard'."
        )
    )
    race: str = Field(description="e.g. 'Human', 'Tiefling', 'Goliath'")
    alignment: Alignment
    rank_title: str = Field(
        description=(
            "The hierarchy rank this character holds, copied exactly from "
            "the slot being filled"
        )
    )
    description: str = Field(
        description=(
            "Leadership/officer/member: 4-6 full sentences — appearance, "
            "personality, role in the faction, and a hook the party could "
            "pull on. Mob tier: at most 2 sentences of combat-relevant flavor."
        )
    )


class CharacterSet(BaseModel):
    """Several characters generated together for one faction, so the
    model makes them distinct from each other."""

    characters: list[GeneratedCharacter]
