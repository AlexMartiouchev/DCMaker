import os
import time
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dcmaker.settings")
django.setup()

from populator.models import Location, Faction, Character

from populator.apps import PopulatorConfig
from populator.utils import (
    faction_image,
    location_image,
    save_image_from_url,
)


demo_locations = Location.objects.filter(demo__isnull=False)
demo_factions = Faction.objects.filter(location__demo__isnull=False)
demo_characters = Character.objects.filter(faction__location__demo__isnull=False)


def demo_location_image_generate():
    for location in demo_locations:
        prompt = f"{location.name}\n{location.description}\n{PopulatorConfig.location_image_prompt}"
        location_url = location_image(prompt=prompt)
        save_image_from_url(image_url=location_url, obj=location)


def demo_faction_image_generate():
    for faction in demo_factions:
        base_prompt = f"{PopulatorConfig.faction_image_prompt}{faction.faction_type} who are called {faction.name}"
        full_prompt = (
            f"{base_prompt} who are described to be {faction.description}"
            if faction.description
            else base_prompt
        )

        try:
            faction_url = faction_image(full_prompt)
            if not save_image_from_url(image_url=faction_url, obj=faction):
                raise ValueError("Failed to save image")
        except Exception as e:
            print(
                f"Error on first attempt: {e} for faction {faction.name}. Retrying without description."
            )
            time.sleep(13)
            try:
                faction_url = faction_image(base_prompt)
                if not save_image_from_url(image_url=faction_url, obj=faction):
                    raise ValueError("Failed to save image on retry")
            except Exception as retry_error:
                print(f"Retry failed: {retry_error} for faction {faction.name}")
                time.sleep(25)


def demo_character_image_generate():
    for character in demo_characters:
        prompt = f"{character.name}\n{character.description}\n{PopulatorConfig.character_image_prompt}"
        character_url = faction_image(prompt=prompt)
        save_image_from_url(image_url=character_url, obj=character, iso=True)
        character_url = faction_image(prompt=prompt)
        save_image_from_url(image_url=character_url, obj=character, iso=False)
        time.sleep(25)


demo_faction_image_generate()
