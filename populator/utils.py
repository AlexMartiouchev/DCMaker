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
            r"character(?:s)?_(\d+)_name:\s*(.+?)\r?\n"
            r"character(?:s)?_\1_description:\s*(.+?)\r?\n"
            r"character(?:s)?_\1_race:\s*(.+?)(?:\r?\n){2,}",
            re.DOTALL
        )

        # Remove AI context if given
        start_marker = "character_1_name:"
        start_index = response_text.find(start_marker)
        if start_index != -1:
            processed_text = response_text[start_index:]
        else:
            processed_text = response_text

        # Find all matches
        matches = pattern.findall(processed_text)

        # Convert matches to list of dictionaries
        characters = [{
            "name": match[1].strip(),
            "description": match[2].strip(),
            "race": match[3].strip()
        } for match in matches]

        # Convert list of dictionaries to JSON
        return characters


def parse_character_demo(response_text):
        # Pattern to match factions and their characters in one sweep
        pattern = re.compile(
            r"character(?:s)?_(\d+)_name:\s*(.+?)\r?\n"
            r"character(?:s)?_\1_description:\s*(.+?)\r?\n"
            r"character(?:s)?_\1_race:\s*(.+?)(?:\r?\n){2,}",
            re.DOTALL
        )

        # Remove AI context if given
        start_marker = "character_1_name:"
        start_index = response_text.find(start_marker)
        if start_index != -1:
            processed_text = response_text[start_index:]
        else:
            processed_text = response_text

        # Find all matches
        matches = pattern.findall(processed_text)

        # Convert matches to list of dictionaries
        characters = [{
            "model": "populator.faction",
            "fields": {
                "pk": match[0],
                "name": match[1].strip(),
                "description": match[2].strip(),
                "race": match[3].strip()
            }
        } for match in matches]

        return characters
