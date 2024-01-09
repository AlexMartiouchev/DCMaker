from openai import OpenAI

client = OpenAI(api_key=settings.OPENAI_API_KEY)
from django.conf import settings

def call_openai_api(prompt_text):

    try:
        response = client.completions.create(model="text-davinci-003",  # Update the model name as per the new API
        prompt=prompt_text,
        max_tokens=150)
        return response.choices[0].text.strip()
    except Exception as e:
        # Handle any exceptions (e.g., API errors, network issues)
        print(f"Error calling OpenAI API: {e}")
        return None