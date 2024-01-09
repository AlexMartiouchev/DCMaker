import json
from populator.apps import PopulatorConfig
from django.shortcuts import render

from django.http import JsonResponse


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
        print(structured_data)
        
        prompt = PopulatorConfig.prompt_template

        return JsonResponse(structured_data)
