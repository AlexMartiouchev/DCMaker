import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dcmaker.settings')

django.setup()

from populator.utils import call_openai_api, parse_character_demo
from populator.apps import PopulatorConfig


location = """"name": "Langfeyglade",
            "location_type": "Fairy Kingdom in Strife",
            "description": "A once serene and hidden kingdom, known for its lush, enchanted forests and mystical creatures, is now on the brink of civil unrest. Ancient magic wanes, and factions vie for control over the remaining sources of magical power.",
            "party_size": 4,
            "party_level": 8"""

faction = """"model": "populator.faction",
        "pk": 1,
        "fields": {
        "name": "The Thornheart Syndicate",
        "faction_type": " Thieves' Guild",
        "description": "An elusive and ruthless band of thieves and assassins who seek to exploit the kingdom's strife for their gain. They thrive in chaos, using the cover of unrest to steal magical artifacts and eliminate those who stand in their way.",
        "location": 1"""

lead_character_prompt = PopulatorConfig.lead_character_prompt

prompt = lead_character_prompt + location + faction + "/n Generate 3 characters"

character_response = call_openai_api(prompt)
print(character_response)
character_response = parse_character_demo(character_response)

sheet_prompt = PopulatorConfig.character_sheet_prompt

for character in character_response:
    character_info = str(character["fields"])
    prompt_start = sheet_prompt
    prompt_start += faction + "The character type is lead" + character_info
    print(call_openai_api(prompt_start))
