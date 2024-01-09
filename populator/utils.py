import openai
from django.conf import settings

def call_openai_api(prompt_text):
    openai.api_key = settings.OPENAI_API_KEY

    response = openai.Completion.create(
        engine="davinci",  # wil need to decide
        prompt=prompt_text,
        max_tokens=150  # will need to test this
    )
    return response.choices[0].text.strip()
