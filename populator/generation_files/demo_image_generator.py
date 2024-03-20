import os
import sys
import time
import django
from dcmaker.settings import MEDIA_ROOT
from django.core.files import File

# project_path = "path_to_project_directory"

# sys.path.append(project_path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dcmaker.settings")

import django

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
        time.sleep(13)
        character_url = faction_image(prompt=prompt)
        save_image_from_url(image_url=character_url, obj=character, iso=False)
        time.sleep(13)


def update_model_images(model_queryset, iso=None):
    folder_map = {
        "Location": "location_images",
        "Faction": "faction_images",
        "Character": {
            True: "character_images/isometric",
            False: "character_images/headshots",
        },
    }

    # Get the model class from the queryset
    if model_queryset.model:
        model_class = model_queryset.model
        model_name = model_class.__name__

        if iso is not None:
            folder = folder_map["Character"][iso]
        else:
            folder = folder_map.get(model_name, "")

        for instance in model_queryset:
            safe_name = "".join(
                c if c.isalnum() or c in "-_" else "" for c in instance.name
            ).rstrip()
            filename = f"{model_name}_{instance.pk}_{safe_name}.png"
            filepath = os.path.join(MEDIA_ROOT, folder, filename)

            if os.path.exists(filepath):
                with open(filepath, "rb") as f:
                    instance.image.save(filename, File(f), save=True)
            else:
                print(f"File not found: {filepath}")


# uncomment model to generate AND save, if generating for the first time, there is no need to save as below

# demo_location_image_generate()
# demo_faction_image_generate()
demo_character_image_generate()


# uncomment models needed to save

# update_model_images(demo_locations)
# update_model_images(demo_factions)
# update_model_images(demo_characters iso=True)
# update_model_images(demo_characters, iso=False)
