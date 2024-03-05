
from populator.utils import call_openai_api
from populator.apps import PopulatorConfig


location = ""

faction = ""

lead_character_prompt = PopulatorConfig.lead_character_prompt

prompt = lead_character_prompt + faction + "/n Generate 3 characters"

character_response = call_openai_api(prompt)