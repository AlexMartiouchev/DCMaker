"""Thin provider layer: the only file that knows which LLM API we use.

Swapping providers later (OpenAI -> Anthropic/Google) means rewriting
this file only; schemas, prompts, and generate.py stay identical.
"""

from decouple import config
from openai import OpenAI
from pydantic import BaseModel

# One line to change when we pick a different model/provider.
MODEL = config("GENERATION_MODEL", default="gpt-4.1")

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        # decouple reads OPENAI_API_KEY from the .env file, so this works
        # from any entry point (manage.py, scripts, shell) without Django.
        _client = OpenAI(api_key=config("OPENAI_API_KEY"))
    return _client


def generate[T: BaseModel](prompt: str, schema: type[T], system: str) -> T:
    """Send one prompt and return a validated instance of `schema`.

    The API constrains generation to the schema, so the result is
    guaranteed to parse; a refusal or empty result raises instead of
    returning None, so callers never have to null-check.
    """
    response = get_client().responses.parse(
        model=MODEL,
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        text_format=schema,
    )
    if response.output_parsed is None:
        raise RuntimeError(f"Model returned no parsed output: {response}")
    return response.output_parsed
