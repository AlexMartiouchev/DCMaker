from openai import OpenAI
from django.conf import settings
import re

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def call_openai_api(prompt_text):

    try:
        response = client.completions.create(
            model="gpt-3.5-turbo-instruct",  # Update the model name as per the new API
            prompt=prompt_text,
            max_tokens=1000
        )
        return response.choices[0].text.strip()
    except Exception as e:
        # Handle any exceptions (e.g., API errors, network issues)
        print(f"Error calling OpenAI API: {e}")
        return None


def parse_location_response(response_text):
    match = re.search(r'location_name: (.*?)\nlocation_response: (.*?)\nlocation_summary: (.*)', response_text, re.S)
    if match:
        location_name = match.group(1).strip()
        detailed_scenario = match.group(2).strip()
        location_summary = match.group(3).strip()
        return location_name, detailed_scenario, location_summary
    else:
        raise ValueError("Unable to parse location response")
