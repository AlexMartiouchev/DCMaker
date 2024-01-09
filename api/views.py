import json
from populator.apps import PopulatorConfig
from django.shortcuts import render

from django.http import JsonResponse

from populator.utils import call_openai_api


def lore_maker_endpoint(request):
    if request.method == "POST":
        structured_data = {
            "location_fields": {
                "locationType": request.POST.getlist("locationType"),
                "locationPrompt": request.POST.getlist("locationPrompt"),
            },
        }

        # Process factions
        faction_types = request.POST.getlist("factionType")
        faction_prompts = request.POST.getlist("factionPrompt")

        for index in range(len(faction_types)):
            structured_data[f"faction_{index+1}_fields"] = {
                "factionType": faction_types[index],
                "factionPrompt": faction_prompts[index],
            }

        # Process characters
        character_factions = request.POST.getlist("characterFactions")
        character_prompts = request.POST.getlist("characterPrompt")

        for index in range(len(character_factions)):
            structured_data[f"character_{index+1}_fields"] = {
                "characterFactions": character_factions[index],
                "characterPrompt": character_prompts[index],
            }
        
        # Construct a string prompt from structured_data
        prompt_text = PopulatorConfig.prompt_template + "\n\n"
        prompt_text += "Location Type: " + ', '.join(request.POST.getlist("locationType")) + "\n"
        prompt_text += "Location Description: " + ', '.join(request.POST.getlist("locationPrompt")) + "\n"

        for index in range(len(faction_types)):
            prompt_text += f"Faction {index + 1} Type: {faction_types[index]}\n"
            prompt_text += f"Faction {index + 1} Description: {faction_prompts[index]}\n"

        for index in range(len(character_factions)):
            prompt_text += f"Character {index + 1} Factions: {character_factions[index]}\n"
            prompt_text += f"Character {index + 1} Description: {character_prompts[index]}\n"

        # Call OpenAI API
        ai_response = call_openai_api(prompt_text)

        # Return the response
        return JsonResponse({"ai_response": ai_response})
