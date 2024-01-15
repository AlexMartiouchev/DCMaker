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
    faction_pattern = r"faction_(\d+)_name: (.+?)\n" \
                    r"faction_\1_response: (.+?)\n" \
                    r"faction_\1_summary: (.+?)\n\n"
    
    factions = re.findall(faction_pattern, response_text, re.DOTALL)
    faction_data = []
    for index, name, response, summary in factions:
        faction_dict = {
            f"faction_{index}_name": name.strip(),
            f"faction_{index}_response": response.strip(),
            f"faction_{index}_summary": summary.strip()
        }
        faction_data.append(faction_dict)

    return faction_data

def parse_character_response(response_text):
    character_pattern = r"character_(\d+)_faction: (.+?)\n" \
                        r"character_\1_name: (.+?)\n" \
                        r"character_\1_response: (.+?)\n" \
                        r"character_\1_summary: (.+?)\n\n"
    
    characters = re.findall(character_pattern, response_text, re.DOTALL)
    character_data = []
    for index, faction, name, response, summary in characters:
        character_dict = {
            f"character_{index}_faction": faction.strip(),
            f"character_{index}_name": name.strip(),
            f"character_{index}_response": response.strip(),
            f"character_{index}_summary": summary.strip()
        }
        character_data.append(character_dict)

    return character_data
