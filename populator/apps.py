from django.apps import AppConfig


class PopulatorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'populator'
    location_prompt = ""
    faction_prompt = ""
    lead_character_prompt = ""
    mob_character_prompt = ""

    def ready(self):
        with open('prompts/location_prompt.txt', 'r') as file:
            PopulatorConfig.location_prompt = file.read()
        with open('prompts/faction_prompt.txt', 'r') as file:
            PopulatorConfig.faction_prompt = file.read()
        with open('prompts/lead_character_prompt.txt', 'r') as file:
            PopulatorConfig.lead_character_prompt = file.read()
        with open('prompts/mob_character_prompt.txt', 'r') as file:
            PopulatorConfig.mob_character_prompt = file.read()

