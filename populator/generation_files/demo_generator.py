import os
import pprint
import sys
import time
import django

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dcmaker.settings")

django.setup()

from populator.utils import (
    call_openai_api,
    parse_location_response,
    parse_faction_response,
    parse_character_description,
    parse_character_sheet,
)
from populator.apps import PopulatorConfig


location_prompt = PopulatorConfig.location_prompt
faction_prompt = PopulatorConfig.faction_prompt
lead_character_prompt = PopulatorConfig.lead_character_prompt
mob_character_prompt = PopulatorConfig.mob_character_prompt
sheet_prompt = PopulatorConfig.character_sheet_prompt


def call_open_api(prompt, parse_function):
    count = 0
    while count < 10:
        try:
            resp = call_openai_api(prompt)
            if resp:
                parsed_data = parse_function(resp)
                if parsed_data:
                    return parsed_data
        except Exception as e:
            print(f"Error during API call or parsing: {e}")
        time.sleep(1)
        count += 1
        print(f"Parse failed {count} times")
        print(resp)
    print("Something went wrong after 10 attempts.")
    return None


def generate_location():
    prompt = location_prompt.format(
        location_prompt="Archapilego of sky islands kept aloft through forgotten magic"
    )
    return call_open_api(prompt, parse_location_response)


def generate_factions(location, num_factions=3):
    prompt = faction_prompt.format(
        location_name=location["name"],
        location_description=location["description"],
        num_factions=num_factions,
    )
    return call_open_api(prompt, parse_faction_response)


def character_generator(
    faction, faction_num: int, character_num: int, amount: int = 5, lead: bool = True
):
    character_type = "Lead" if lead else "Mob"
    prompt = lead_character_prompt if lead else mob_character_prompt
    prompt = prompt.format(
        location_name=location["name"],
        location_summary=location["description"],
        faction_name=faction["name"],
        faction_type=faction["type"],
        faction_alignment=faction["alignment"],
        faction_description=faction["description"],
        amount=amount,
    )

    character_desc = call_open_api(prompt, parse_character_description)

    character_list = []
    for character in character_desc:
        character_info = character
        character_info["lead"] = lead
        prompt_start = sheet_prompt.format(
            # faction_pk=faction["pk"],
            character_info=character_info,
            character_type=character_type,
        )
        character_combat_parse = call_open_api(prompt_start, parse_character_sheet)
        character_info["profession"] = character_combat_parse.pop("profession")
        character_info["combat_sheet"] = character_combat_parse
        character_info["faction"] = faction_num
        character["fields"] = character_info
        character["pk"] = character_num
        character_num += 1
        character_list.append(character)
    return character_list


start_time = time.perf_counter()

# Generate location
location = generate_location()
if not location:
    print("Location generation failed.")
    exit()

print(
    f"Generated Location:\nName: {location['name']}\nDescription: {location['description']}\nSummary: {location['summary']}"
)
proceed = input("Do you want to proceed with this location? (yes/no): ").strip().lower()

if proceed != "yes":
    print("Aborting process.")
    exit()

# Generate factions
num_factions = 5
factions = generate_factions(location, num_factions)
if not factions:
    print("Faction generation failed.")
    exit()

print("Generated Factions:")
for i, (key, faction) in enumerate(factions.items()):
    print(
        f"\nFaction {i+1}:\nName: {faction['name']}\nAlignment: {faction['alignment']}\nDescription: {faction['description']}"
    )

proceed = (
    input("Do you want to proceed with these factions? (yes/no): ").strip().lower()
)

if proceed != "yes":
    print("Aborting process.")
    exit()

# Generate characters for each faction
faction_characters = []
character_num = 1

for faction_key, faction in factions.items():
    lead_characters = character_generator(
        faction,
        faction_num=faction_key,
        character_num=character_num,
        amount=1,
        lead=True,
    )
    mob_characters = character_generator(
        faction,
        faction_num=faction_key,
        character_num=character_num,
        amount=2,
        lead=False,
    )

    faction_characters.extend(lead_characters)
    faction_characters.extend(mob_characters)

print("Generated Characters:")
for character in faction_characters:
    print(
        f"\nName: {character['fields']['name']}\nRace: {character['fields']['race']}\nAlignment: {character['fields']['alignment']}\nDescription: {character['fields']['description']}"
    )

end_time = time.perf_counter()
elapsed_time = end_time - start_time
print(f"Elapsed time: {elapsed_time:.6f} seconds")
