import os
import pprint
import time
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dcmaker.settings")

django.setup()

from populator.utils import call_openai_api, parse_character_demo, parse_character_sheet
from populator.apps import PopulatorConfig


location = """"name": "Aetheria's Reach",
            "location_type": "Skyborne Archipelago",
            "description": "A series of floating islands above a seemingly endless void, connected by bridges of light and ancient magic. The islands are a haven for air elementals, sky pirates, and adventurers seeking the thrill of the unknown.",
            "party_size": 4,
            "party_level": 8"""

factions = [
    {
        "model": "populator.faction",
        "pk": 19,
        "fields": {
            "name": "The Stormfury Raiders",
            "faction_type": "Bandits",
            "description": "A notorious gang of sky pirates and rogue elementals that prey on the islands and airships of Aetheria's Reach. They harness storm magic to attack and plunder, sowing fear and chaos wherever they fly.",
            "location": 3,
        },
    },
    {
        "model": "populator.faction",
        "pk": 20,
        "fields": {
            "name": "The Void Cult",
            "faction_type": "Cultists",
            "description": "A secretive cult that worships the void between the islands, believing in an ancient prophecy that foretells the end of Aetheria's Reach through its consumption by the abyss. They seek to hasten this apocalypse through dark rituals and sabotage.",
            "location": 3,
        },
    },
    {
        "model": "populator.faction",
        "pk": 21,
        "fields": {
            "name": "The Skybreaker Legion",
            "faction_type": "Mercenaries",
            "description": "A mercenary force equipped with advanced weaponry and airships, funded by unknown benefactors. They aim to conquer the archipelago and establish a new order, using their military might to subjugate the islands one by one.",
            "location": 3,
        },
    },
    {
        "model": "populator.faction",
        "pk": 22,
        "fields": {
            "name": "The Windborne Guild",
            "faction_type": "Merchants",
            "description": "An influential guild of traders and inventors who navigate the skies, dealing in rare artifacts, technology, and information. They maintain neutrality, their allegiance swaying with the wind to whoever offers the best price.",
            "location": 3,
        },
    },
    {
        "model": "populator.faction",
        "pk": 23,
        "fields": {
            "name": "The Celestine Scholars",
            "faction_type": "Academics",
            "description": "A society of scholars, mages, and researchers dedicated to uncovering the secrets of the archipelago and the magic that keeps it afloat. They are neutral, focused on their studies and willing to share knowledge with all who seek it.",
            "location": 3,
        },
    },
    {
        "model": "populator.faction",
        "pk": 24,
        "fields": {
            "name": "The Cloudweaver Collective",
            "faction_type": "Artisans",
            "description": "A community of artists, builders, and creators who specialize in crafting from the clouds themselves, shaping them into living spaces, sculptures, and vessels. They value creativity over conflict, remaining neutral and dedicated to their craft.",
            "location": 3,
        },
    },
    {
        "model": "populator.faction",
        "pk": 25,
        "fields": {
            "name": "The Azure Sentinels",
            "faction_type": "Protectors",
            "description": "A knightly order that patrols the skies, defending the archipelago's islands and inhabitants from threats. They are valorous and just, committed to safeguarding the peace and prosperity of Aetheria's Reach.",
            "location": 3,
        },
    },
    {
        "model": "populator.faction",
        "pk": 26,
        "fields": {
            "name": "The Zephyr Alliance",
            "faction_type": "Diplomats",
            "description": "A coalition of island leaders and influential figures working together to ensure the stability and unity of the archipelago. They facilitate communication and cooperation between islands, mediating conflicts and organizing collective defense efforts.",
            "location": 3,
        },
    },
    {
        "model": "populator.faction",
        "pk": 27,
        "fields": {
            "name": "The Lumina Healers",
            "faction_type": "Healers",
            "description": "A revered group of healers and light mages who use their powers to heal wounds, cure diseases, and dispel darkness. They travel across the archipelago, offering their services to all in need, spreading light and hope.",
            "location": 3,
        },
    },
]

lead_character_prompt = PopulatorConfig.lead_character_prompt
mob_character_prompt = PopulatorConfig.mob_character_prompt


def call_open_api(prompt, parse_character: bool = True):
    resp = call_openai_api(prompt)
    count = 0
    if count == 10:
        return print("Something went wrong")
    if parse_character:
        character_desc = parse_character_demo(resp)
        if character_desc:
            return character_desc
        else:
            time.sleep(1)
            count += 1
            return call_open_api(prompt)
    else:
        print(resp)
        character_desc = parse_character_sheet(resp)
        if character_desc:
            return character_desc
        else:
            time.sleep(1)
            count += 1
            return call_open_api(prompt, parse_character=False)


def character_generator(
    faction, faction_num: int, character_num: int, amount: int = 5, lead: bool = True
):
    if lead:
        character_type = "Lead"
        prompt = lead_character_prompt
    else:
        character_type = "Mob"
        amount = 2
        prompt = mob_character_prompt
    prompt += (
        location
        + str(faction["fields"])
        + f"/n Make sure to generate exactly {amount} characters"
        + "Balance this character to be appropriate for 4 level 8 players"
    )

    character_desc = call_open_api(prompt)

    sheet_prompt = PopulatorConfig.character_sheet_prompt
    character_list = []
    for character in character_desc:
        character_info = character["fields"]
        if lead:
            character_info["lead"] = True
        else:
            character_info["lead"] = False
        prompt_start = sheet_prompt
        prompt_start += (
            str(faction["pk"])
            + str(character_info)
            + f"The character type a {character_type} type character"
        )
        character_combat_parse = call_open_api(prompt_start, parse_character=False)
        character_info["profession"] = character_combat_parse.pop("profession")
        character_info["combat_sheet"] = character_combat_parse
        character_info["faction"] = faction_num
        character["fields"] = character_info
        character["pk"] = character_num
        character_num += 1
        character_list.append(character)
    return character_list


start_time = time.perf_counter()
faction_characters = []
character_num = 127

for faction in factions:
    faction_num = faction["pk"]
    lead_characters = character_generator(
        faction=faction, faction_num=faction_num, character_num=character_num
    )
    for character in lead_characters:
        faction_characters.append(character)
    character_num += 5
    mob_characters = character_generator(
        faction=faction,
        faction_num=faction_num,
        character_num=character_num,
        lead=False,
    )
    for character in mob_characters:
        faction_characters.append(character)
    character_num += 2

end_time = time.perf_counter()

print(faction_characters)

elapsed_time = end_time - start_time
print(f"Elapsed time: {elapsed_time:.6f} seconds")
