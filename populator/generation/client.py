"""Thin provider layer: the only file that knows which LLM API we use.

Swapping providers later (OpenAI -> Anthropic/Google) means rewriting
this file only; schemas, prompts, and generate.py stay identical.
"""

from typing import Callable

from decouple import config
from openai import OpenAI
from pydantic import BaseModel

# One line to change when we pick a different model/provider.
#
# Pin a dated snapshot rather than a bare alias ("gpt-5.4-mini"): aliases
# move under you, which would change output quality in production without
# a deploy, and invalidate a model comparison halfway through it.
MODEL = config("GENERATION_MODEL", default="gpt-5.4-mini-2026-03-17")

_client: OpenAI | None = None

# Metering hooks. These let the Django layer count and cap generation
# without this file importing Django — it stays provider-specific and
# framework-free, which is the point of keeping it separate.
#   before_call: may raise to refuse the call, which is how the daily cap
#                stops a batch part-way rather than after it is paid for
#   after_call:  receives token usage for telemetry
_before_call: Callable[[str], None] | None = None
_after_call: Callable[[str, int, int], None] | None = None


def set_hooks(
    before: Callable[[str], None] | None = None,
    after: Callable[[str, int, int], None] | None = None,
) -> None:
    """Register metering callbacks. Called once from PopulatorConfig.ready."""
    global _before_call, _after_call
    _before_call, _after_call = before, after


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
    if _before_call is not None:
        _before_call(MODEL)

    response = get_client().responses.parse(
        model=MODEL,
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        text_format=schema,
    )

    if _after_call is not None:
        # getattr guards a provider that reports usage differently — we
        # would rather lose telemetry than fail a generation over it.
        usage = getattr(response, "usage", None)
        _after_call(
            MODEL,
            getattr(usage, "input_tokens", 0) or 0,
            getattr(usage, "output_tokens", 0) or 0,
        )

    if response.output_parsed is None:
        raise RuntimeError(f"Model returned no parsed output: {response}")
    return response.output_parsed
