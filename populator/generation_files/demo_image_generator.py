import os
import time
import django
from dcmaker.settings import MEDIA_ROOT
from django.core.files import File

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


def update_model_images(model_class, is_isometric=None):
    folder_map = {
        "Location": "location_images",
        "Faction": "faction_images",
        "Character": {
            True: "character_images/isometric",
            False: "character_images/headshots",
        },
    }

    # Determine folder path based on model class and is_isometric flag
    if model_class == Character:
        assert (
            is_isometric is not None
        ), "is_isometric must be specified for Character model."
        folder = folder_map["Character"][is_isometric]
    else:
        folder = folder_map[model_class.__name__]

    # Iterate over all instances of the model class
    for instance in model_class.objects.all():
        safe_name = "".join(
            c if c.isalnum() or c in "-_" else "" for c in instance.name
        ).rstrip()
        filename = f"{safe_name}_{instance.pk}.png"
        full_path = os.path.join(MEDIA_ROOT, folder, filename)

        # Ensure the directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # If the file exists, attach it to the instance's image field
        if os.path.exists(full_path):
            with open(full_path, "rb") as file:
                instance.image.save(filename, File(file), save=True)
        else:
            print(f"File not found: {full_path}")


# uncomment model to generate AND save, if generating for the first time, there is no need to save as below

# demo_location_image_generate()
# demo_faction_image_generate()
# demo_character_image_generate()


# uncomment models needed to save

# update_model_images(demo_locations)
# update_model_images(demo_factions)
# update_model_images(demo_characters iso=True)
# update_model_images(demo_characters, iso=False)
