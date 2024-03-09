from models import Location, Faction, Character
import requests

from openai import OpenAI

client = OpenAI()


def location_image():
    pass


def faction_image():
    pass


def character_image_iso(prompt: str):
    try:
        with open("../prompts/character_isometric.png", "rb") as image_file:
            response = client.images.create_variation(
                image=image_file, n=1, size="512x512"
            )
        image_url = response["data"][0]["url"]
        return image_url
    except Exception as e:
        print(f"Error generating isometric character image: {e}")
        return None


def character_image_hs(prompt: str):
    try:
        with open("../prompts/character_headshot.png", "rb") as image_file:
            response = client.images.create_variation(
                image=image_file, n=1, size="256x256"
            )
        image_url = response["data"][0]["url"]
        return image_url
    except Exception as e:
        print(f"Error generating headshot character image: {e}")
        return None


def save_image_from_url(image_url, local_path):
    try:
        response = requests.get(image_url)
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code.

        with open(local_path, "wb") as f:
            f.write(response.content)

        print(f"Image saved to {local_path}")
    except requests.exceptions.HTTPError as err:
        print(f"HTTP Error occurred: {err}")
    except Exception as e:
        print(f"Error saving the image: {e}")
