from django.apps import AppConfig


class PopulatorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'populator'
    location_prompt = ""
    faction_prompt = ""
    character_prompt = ""

    def ready(self):
        with open('prompts/location_prompt.txt', 'r') as file:
            PopulatorConfig.location_prompt = file.read()
        with open('prompts/faction_prompt.txt', 'r') as file:
            PopulatorConfig.faction_prompt = file.read()
        with open('prompts/character_prompt.txt', 'r') as file:
            PopulatorConfig.character_prompt = file.read()

