from django.apps import AppConfig


class PopulatorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'populator'
    prompt_template = ""
    def ready(self):
        with open('prompt.txt', 'r') as file:
            PopulatorConfig.prompt_template = file.read()
