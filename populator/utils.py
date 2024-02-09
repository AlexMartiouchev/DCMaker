from openai import OpenAI
from django.conf import settings
import re

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def call_openai_api(prompt_text):

    try:
        response = client.completions.create(
            model="gpt-3.5-turbo-instruct",  # Update the model name as per the new API
            prompt=prompt_text,
            max_tokens=1000
        )
        return response.choices[0].text.strip()
    except Exception as e:
        # Handle any exceptions (e.g., API errors, network issues)
        print(f"Error calling OpenAI API: {e}")
        return None


def parse_location_response(response_text):
    match = re.search(
    r'(?:location_name|Location Name|location name): (.*?)\n' +
    r'(?:location_response|Location Response|location response): (.*?)\n' +
    r'(?:location_summary|Location Summary|location summary): (.*)', 
    response_text, 
    re.S | re.IGNORECASE
)

    if match:
        location_name = match.group(1).strip()
        detailed_scenario = match.group(2).strip()
        location_summary = match.group(3).strip()
        return location_name, detailed_scenario, location_summary
    else:
        raise ValueError("Unable to parse location response")


def find_highest_faction_number(response_text):
    faction_numbers = re.findall(r'faction_(\d+)_', response_text)
    if not faction_numbers:
        return 0
    return max(map(int, faction_numbers))


def parse_faction_response(response_text):
    faction_pattern = r"(?:.*?)" \
                    r"faction_(\d+)_name: (.*?)\n" \
                    r"faction_\1_response: (.*?)\n" \
                    r"faction_\1_summary: (.*?)(?:\n\n|\Z)"
    
    matches = re.findall(faction_pattern, response_text, re.DOTALL)
    faction_data = {}

    for index, name, response, summary in matches:
        faction_key = f"faction_{index}"
        faction_details = {
            "name": name.strip(),
            "response": response.strip(),
            "summary": summary.strip()
        }
        faction_data[faction_key] = faction_details

    return faction_data


def parse_character_response(response_text):
    # Pattern to match factions and their characters in one sweep
    pattern = re.compile(
        r"faction_(\d+)_name: (.+?)\n((?:character_\d+_name: .+?\n"
        r"character_\d+_response: .+?\ncharacter_\d+_summary: .+?\n\n)+)",
        re.DOTALL
    )

    # Pattern to extract character details within a matched faction block
    char_detail_pattern = re.compile(
        r"character_(\d+)_name: (.+?)\n"
        r"character_\1_response: (.+?)\n"
        r"character_\1_summary: (.+?)\n\n",
        re.DOTALL
    )

    structured_response = {}

    # Extract factions and associated character blocks
    factions = pattern.findall(response_text)

    for faction_index, faction_name, characters_block in factions:
        # Extract individual character details within this faction's block
        characters = char_detail_pattern.findall(characters_block)

        # List to store structured character details
        character_details = []

        for _, char_name, char_response, char_summary in characters:
            character_details.append({
                "name": char_name.strip(),
                "response": char_response.strip(),
                "summary": char_summary.strip(),
            })

        # Assign faction name and characters to the structured response
        structured_response[f"faction_{faction_index}_name"] = faction_name.strip()
        structured_response[f"faction_{faction_index}_characters"] = character_details

    return structured_response

