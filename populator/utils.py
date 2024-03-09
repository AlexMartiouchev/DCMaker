from openai import OpenAI
from django.conf import settings
import re

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def call_openai_api(prompt_text):

    try:
        response = client.completions.create(
            model="gpt-3.5-turbo-instruct",  # Update the model name as per the new API
            prompt=prompt_text,
            max_tokens=1000,
        )
        return response.choices[0].text.strip()
    except Exception as e:
        # Handle any exceptions (e.g., API errors, network issues)
        print(f"Error calling OpenAI API: {e}")
        return None


def parse_location_response(response_text):
    match = re.search(
        r"(?:location_name|Location Name|location name): (.*?)\n"
        + r"(?:location_response|Location Response|location response): (.*?)\n"
        + r"(?:location_summary|Location Summary|location summary): (.*)",
        response_text,
        re.S | re.IGNORECASE,
    )

    if match:
        location_name = match.group(1).strip()
        detailed_scenario = match.group(2).strip()
        location_summary = match.group(3).strip()
        return location_name, detailed_scenario, location_summary
    else:
        raise ValueError("Unable to parse location response")


def find_highest_faction_number(response_text):
    faction_numbers = re.findall(r"faction_(\d+)_", response_text)
    if not faction_numbers:
        return 0
    return max(map(int, faction_numbers))


def parse_faction_response(response_text):
    faction_pattern = (
        r"(?:.*?)"
        r"faction_(\d+)_name: (.*?)\n"
        r"faction_\1_response: (.*?)\n"
        r"faction_\1_summary: (.*?)(?:\n\n|\Z)"
    )

    matches = re.findall(faction_pattern, response_text, re.DOTALL)
    faction_data = {}

    for index, name, response, summary in matches:
        faction_key = f"faction_{index}"
        faction_details = {
            "name": name.strip(),
            "response": response.strip(),
            "summary": summary.strip(),
        }
        faction_data[faction_key] = faction_details

    return faction_data


def parse_character_demo(response_text):
    # Only start capturing from character_1_name or characters_1_name
    start_marker = "character_1_name:"
    start_index = response_text.find(start_marker)
    if start_index == -1:
        start_marker = "characters_1_name:"
        start_index = response_text.find(start_marker)

    processed_text = response_text[start_index:] if start_index != -1 else response_text

    # Updated pattern to correctly parse character details
    pattern = re.compile(
        r"character(?:s)?_(\d+)_name:\s*(.+?)\s*\n"
        r"character(?:s)?_\1_description:\s*(.+?)\s*\n"
        r"character(?:s)?_\1_race:\s*(.+?)\s*(?:\n|$)",
        re.DOTALL,
    )

    matches = pattern.findall(processed_text)

    # Convert matches to list of dictionaries
    characters = [
        {
            "name": match[1].strip(),
            "description": match[2].strip(),
            "race": match[3].strip(),
        }
        for match in matches
    ]

    # Convert list of dictionaries to JSON
    return characters


def parse_actions_and_abilities(section_text):
    ignore_headers = [
        "Faction",
        "End of example",
        "End of character sheet",
        "Description",
    ]
    items_dict = {}
    lines = section_text.split("\n")
    for line in lines:
        if line.strip():
            # Check if the line starts with any of the ignore headers
            if any(line.startswith(header) for header in ignore_headers):
                continue  # Stop processing further if an ignore header is found
            try:
                key, value = line.split(": ", 1)
            except ValueError:
                print("find me here")
                print(line)
                continue
            items_dict[key.strip()] = value.strip()
    return items_dict


def parse_character_sheet(input_text):
    # Initialize a dictionary to hold the parsed data
    character_data = {}

    # Define regex patterns for each section
    profession_pattern = re.compile(r"Profession: (.+?)\n")
    hp_ac_pattern = re.compile(r"HP: (\d+)(?:\s|\D).*AC: (\d+)(?:\s|\D).*")
    stats_pattern = re.compile(r"Stats: ((?:\w+ \d+,?\s?)+)")
    actions_pattern = re.compile(r"Actions:\n(.*?)(?=Abilities:|\Z)", re.DOTALL)
    abilities_pattern = re.compile(r"Abilities:\n(.+)", re.DOTALL)

    # Extract data using regex patterns
    profession_match = profession_pattern.search(input_text)
    hp_ac_match = hp_ac_pattern.search(input_text)
    stats_match = stats_pattern.search(input_text)
    actions_match = actions_pattern.search(input_text)
    abilities_match = abilities_pattern.search(input_text)

    if not all([profession_match, hp_ac_match, stats_match, actions_match]):
        return {}

    # Populate the dictionary
    character_data["profession"] = profession_match.group(1).strip()
    stats_dict = {}
    stats_dict["hp"] = int(hp_ac_match.group(1))
    stats_dict["ac"] = int(hp_ac_match.group(2))
    # Process the matched stats string into a dictionary
    stats_list = stats_match.group(1).split(", ")
    for stat in stats_list:
        key, value = stat.split()
        stats_dict[key.lower()] = int(value)
    character_data["stats"] = stats_dict
    # Split actions into a list, trimming whitespace
    character_data["actions"] = parse_actions_and_abilities(actions_match.group(1))

    # Process abilities into a dictionary
    if abilities_match:
        character_data["abilities"] = parse_actions_and_abilities(
            abilities_match.group(1)
        )

    return character_data


def parse_character_demo(response_text):
    # Only start capturing from character_1_name or characters_1_name
    start_marker = "character_1_name:"
    start_index = response_text.find(start_marker)
    if start_index == -1:
        start_marker = "characters_1_name:"
        start_index = response_text.find(start_marker)

    processed_text = response_text[start_index:] if start_index != -1 else response_text

    # Updated pattern to correctly parse character details
    pattern = re.compile(
        r"character(?:s)?_(\d+)_name:\s*(.+?)\s*\n"
        r"character(?:s)?_\1_description:\s*(.+?)\s*\n"
        r"character(?:s)?_\1_race:\s*(.+?)\s*(?:\n|$)",
        re.DOTALL,
    )

    matches = pattern.findall(processed_text)

    characters = [
        {
            "model": "populator.character",
            "fields": {
                "name": match[1].strip(),
                "description": match[2].strip(),
                "race": match[3].strip(),
            },
        }
        for match in matches
    ]

    return characters
