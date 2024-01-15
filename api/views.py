import json
from populator.apps import PopulatorConfig

from django.http import JsonResponse

from populator.utils import call_openai_api, find_highest_faction_number, parse_character_response, parse_location_response, parse_faction_response


def lore_maker_endpoint(request):
    if request.method == "POST":

        # keep structured_data for logging?

        # structured_data = {
        #     "location_fields": {
        #         "locationType": request.POST.getlist("locationType"),
        #         "locationPrompt": request.POST.getlist("locationPrompt"),
        #     },
        # }

        # # Process factions
        faction_types = request.POST.getlist("factionType")
        faction_prompts = request.POST.getlist("factionPrompt")

        # for index in range(len(faction_types)):
        #     structured_data[f"faction_{index+1}_fields"] = {
        #         "factionType": faction_types[index],
        #         "factionPrompt": faction_prompts[index],
        #     }

        # Process characters
        character_factions = request.POST.getlist("characterFactions")
        character_prompts = request.POST.getlist("characterPrompt")
        party_number = request.POST.get("partyNumber", 4)
        party_level = request.POST.get("partyLevel", 4)


        # for index in range(len(character_factions)):
        #     structured_data[f"character_{index+1}_fields"] = {
        #         "characterFactions": character_factions[index],
        #         "characterPrompt": character_prompts[index],
        #     }
        
        # Send fields for location, receiving response as a full description and a summary
        location_prompt_text = PopulatorConfig.location_prompt + "\n\n"
        location_prompt_text += "Location Type: " + ', '.join(request.POST.getlist("locationType")) + "\n"
        location_prompt_text += "Location Description: " + ', '.join(request.POST.getlist("locationPrompt")) + "\n"

        location_response = call_openai_api(location_prompt_text)
        # Convert response from JSON string to Python dictionary

        # parsing does not always work, so a few tries are allowed
        max_attempts = 10
        attempts = 0
        location_name, detailed_scenario, location_summary = None, None, None

        while attempts < max_attempts:
            try:
                location_name, detailed_scenario, location_summary = parse_location_response(location_response)
                location_data = {
                    "location_name": location_name,
                    "detailed_scenario": detailed_scenario,
                    "location_summary": location_summary
                }
                break  # Exit the loop if parsing is successful
            except ValueError:
                print("Parsing attempt", attempts + 1, "failed.")
                print("Response:\n" + location_response)  # Logging the response for debugging
                attempts += 1

        # Check if parsing was successful
        if location_name is None or detailed_scenario is None or location_summary is None:
            return JsonResponse({"error": "Unable to parse location response after multiple attempts"}, status=500)


        # send fields for factions, as well as a summary of location, receiving response as a full description and summary
        faction_prompt_text = PopulatorConfig.faction_prompt + "\n"
        faction_prompt_text += location_summary + "\n\n"
        if len(faction_types) >0:
            faction_prompt_text += "Below here are the user inputs:" + "\n\n"
            for index in range(len(faction_types)):
                faction_prompt_text += f"Faction {index + 1} Type: {faction_types[index]}\n"
                faction_prompt_text += f"Faction {index + 1} Description: {faction_prompts[index]}\n"
        else:
            faction_prompt_text += "The user has not inputted any faction specific information, instead imaginatively expand on factions using the location summary"


        faction_response = call_openai_api(faction_prompt_text)
        max_attempts = 10
        attempts = 0

        # Attempt to parse faction data
        while attempts < max_attempts:
            try:
                faction_data = parse_faction_response(faction_response)
                if faction_data:  # Check if the parsed data is not empty
                    break  # Exit the loop if parsing is successful
                else:
                    raise ValueError("Parsed faction data is empty")
            except ValueError as e:
                print("Parsing attempt", attempts + 1, "failed:", e)
                print("Response:\n" + faction_response)  # Logging the response for debugging
                attempts += 1

        # Check if parsing was successful
        if not faction_data:
            return JsonResponse({"error": "Unable to parse faction response after multiple attempts"}, status=500)


        # character response will be broken into two types, lead roles and mobs

        lead_character_prompt_text = PopulatorConfig.lead_character_prompt + "\n"
        lead_character_prompt_text += location_summary + "\n"
        lead_character_prompt_text += str(faction_data) + "\n"
        if len(character_prompts) >0:
            lead_character_prompt_text += "Below here are the user inputs:" + "\n\n"
            for index in range(len(faction_types)):
                lead_character_prompt_text += f"Character {index + 1} Faction: {character_factions[index]}\n"
                lead_character_prompt_text += f"Character {index + 1} Description: {character_prompts[index]}\n"
        else:
            faction_prompt_text += "The user has not inputted any character specific information, instead imaginatively expand on characters using the faction summary"

        lead_character_response = call_openai_api(lead_character_prompt_text)
        max_attempts = 10
        attempts = 0

        # Attempt to parse faction data
        while attempts < max_attempts:
            try:
                lead_character_data = parse_character_response(lead_character_response)
                if lead_character_data:  # Check if the parsed data is not empty
                    print(lead_character_data)
                    break
                else:
                    raise ValueError("Parsed faction data is empty")
            except ValueError as e:
                print("Parsing attempt", attempts + 1, "failed:", e)
                print("Response:\n" + faction_response)  # Logging the response for debugging
                attempts += 1

        # Check if parsing was successful
        if not lead_character_data:
            return JsonResponse({"error": "Unable to parse lead characters response after multiple attempts"}, status=500)



        # faction_response = call_openai_api(faction_prompt_text)
        # print(faction_response)
        # faction_summary = faction_response["summary"]

        # # send fields for factions, as well as a summary of location, receiving response as a full description and summary
        # character_prompt_text = PopulatorConfig.character_prompt + "\n"
        # character_prompt_text += location_summary + "\n"
        # character_prompt_text += faction_summary + "\n\n"
        # for index in range(len(character_factions)):
        #     character_prompt_text += f"Character {index + 1} Factions: {character_factions[index]}\n"
        #     character_prompt_text += f"Character {index + 1} Description: {character_prompts[index]}\n"
        
        # character_response = call_openai_api(character_prompt_text)

        # # Return the response
        # return JsonResponse({{"location_response": location_response},
        #                     {"faction_response": faction_response},
        #                     {"character_response": character_response}})
