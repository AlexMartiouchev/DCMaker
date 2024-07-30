import os
from openai import OpenAI
from django.conf import settings
import re

import requests

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def call_openai_api(prompt_text):

    try:
        response = client.completions.create(
            model="gpt-3.5-turbo-instruct",
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
        + r"(?:location_description|Location Description|location description): (.*?)\n"
        + r"(?:location_summary|Location Summary|location summary): (.*)",
        response_text,
        re.S | re.IGNORECASE,
    )

    if match:
        location_data = {
            "name": match.group(1).strip(),
            "description": match.group(2).strip(),
            "summary": match.group(3).strip(),
        }
        return location_data
    else:
        raise ValueError("Unable to parse location response")


def parse_faction_response(response_text):
    faction_pattern = (
        r"faction_(\d+)_name:\s*(.*?)\s*\n"
        r"faction_\1_type:\s*(.*?)\s*\n"
        r"faction_\1_alignment:\s*(.*?)\s*\n"
        r"faction_\1_description:\s*(.*?)(?:\n\n|\Z)"
    )

    matches = re.findall(faction_pattern, response_text, re.DOTALL)
    faction_data = {}

    for index, name, type, alignment, description in matches:
        faction_key = f"faction_{index}"
        faction_details = {
            "name": name.strip(),
            "type": type.strip(),
            "alignment": alignment.strip(),
            "description": description.strip(),
        }
        faction_data[faction_key] = faction_details

    return faction_data


def parse_character_description(response_text):
    # Only start capturing from character_1_name or characters_1_name
    start_marker = "character_1_name:"
    start_index = response_text.find(start_marker)
    if start_index == -1:
        start_marker = "characters_1_name:"
        start_index = response_text.find(start_marker)

    processed_text = response_text[start_index:] if start_index != -1 else response_text

    pattern = re.compile(
        r"character(?:s)?_(\d+)_name:\s*(.+?)\s*\n"
        r"character(?:s)?_\1_race:\s*(.+?)\s*\n"
        r"character(?:s)?_\1_alignment:\s*(.+?)\s*\n"
        r"character(?:s)?_\1_description:\s*(.+?)\s*(?:\n|$)",
        re.DOTALL,
    )

    matches = pattern.findall(processed_text)

    # Convert matches to list of dictionaries
    characters = [
        {
            "name": match[1].strip(),
            "race": match[2].strip(),
            "alignment": match[3].strip(),
            "description": match[4].strip(),
        }
        for match in matches
    ]

    # Convert list of dictionaries to JSON
    return characters


def parse_character_actions(section_text):
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
    character_data["actions"] = parse_character_actions(actions_match.group(1))

    # Process abilities into a dictionary
    if abilities_match:
        character_data["abilities"] = parse_character_actions(abilities_match.group(1))

    return character_data


def location_image(prompt: str):
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )

        image_url = response.data[0].url
        return image_url
    except Exception as e:
        print(f"Error generating location image: {e}")
        return None


def faction_image(prompt: str):
    try:
        response = client.images.generate(
            model="dall-e-2",
            prompt=prompt,
            size="256x256",
            quality="standard",
            n=1,
        )

        image_url = response.data[0].url
        return image_url
    except Exception as e:
        print(f"Error generating faction image: {e}")
        return None


def character_image_iso(prompt: str):
    try:
        with open("../prompts/character_isometric.png", "rb") as image_file:
            response = client.images.edit(image=image_file, n=1, size="512x512")
        image_url = response["data"][0]["url"]
        return image_url
    except Exception as e:
        print(f"Error generating isometric character image: {e}")
        return None


def character_image_hs(prompt: str):
    try:
        with open("../prompts/character_headshot.png", "rb") as image_file:
            response = client.images.edit(image=image_file, n=1, size="256x256")
        image_url = response["data"][0]["url"]
        return image_url
    except Exception as e:
        print(f"Error generating headshot character image: {e}")
        return None


def save_image_from_url(image_url, obj, iso=None):
    folder_map = {
        "Location": "location_images",
        "Faction": "faction_images",
        "Character": {
            True: "character_images/isometric",  # Assuming 'True' implies isometric
            False: "character_images/headshots",
        },
    }

    # Determine the folder based on the category or object type
    if iso:
        folder = folder_map.get(iso, "")
    else:
        # Dynamically determine the folder based on the object type and properties
        model_name = obj.__class__.__name__
        if model_name in folder_map:
            if model_name == "Character":
                if iso == True:
                    folder = folder_map[model_name][True]
                else:
                    folder = folder_map[model_name][False]
            else:
                folder = folder_map[model_name]
        else:
            print(f"Unknown model or category: {model_name}")
            return

    safe_name = "".join(
        c if c.isalnum() or c in "-_" else "" for c in obj.name
    ).rstrip()
    if model_name == "Character":
        if iso:
            os.path.join(folder, f"{model_name}iso_{obj.pk}_{safe_name}.png")
        else:
            os.path.join(folder, f"{model_name}headshot_{obj.pk}_{safe_name}.png")
    else:
        local_path = os.path.join(folder, f"{model_name}_{obj.pk}_{safe_name}.png")

    # Ensure the directory exists
    full_path = os.path.join(settings.MEDIA_ROOT, local_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    # Download and save the image
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        try:
            obj.image = local_path
            obj.save()
        except:
            pass

        with open(full_path, "wb") as f:
            f.write(response.content)

        print(f"Image saved to {full_path}")
        # Here you might also want to update the object's image field
        # and save the object, e.g., obj.image = local_path; obj.save()
        return local_path

    except requests.exceptions.RequestException as e:
        print(f"Error saving the image: {e}")
        return None
