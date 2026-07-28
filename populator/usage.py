"""Generation metering: a per-user cap, and token telemetry.

Playtesters spend Sasha's OpenAI credit, so every call is counted before
it is made and recorded after. Both halves live here because they share
the same ledger row (`GenerationEvent`).

Why a context variable rather than passing the user down: the engine
(`populator/generation/`) is deliberately Django-free and knows nothing
about requests or users. The view sets the context, the engine calls the
hooks, and the two never import each other.
"""

import contextvars
import logging
from contextlib import contextmanager
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import GenerationEvent

logger = logging.getLogger(__name__)

# (user, kind) for the request currently generating, or None outside one.
_context: contextvars.ContextVar = contextvars.ContextVar(
    "generation_context", default=None
)

# A rolling window rather than a calendar day: midnight resets let someone
# spend two full allowances within a few minutes of each other, and
# "resets in 3 hours" is no harder to explain than "resets at midnight".
WINDOW = timedelta(hours=24)


class GenerationLimitReached(Exception):
    """The user has spent their allowance. Carries a message fit to show."""

    def __init__(self, used: int, cap: int, resets_in: timedelta):
        self.used, self.cap, self.resets_in = used, cap, resets_in
        hours = max(1, round(resets_in.total_seconds() / 3600))
        super().__init__(
            f"Daily generation limit reached ({used} of {cap} requests in the "
            f"last 24 hours). More become available in about {hours} "
            f"hour{'s' if hours != 1 else ''}."
        )


def cap_for(user) -> int | None:
    """None means uncapped.

    Two ways to be uncapped: DAILY_GENERATION_CAP of 0 turns the limit off
    for everyone (the current default — see settings), and staff are
    always exempt so Sasha cannot cap himself out of his own app.
    """
    if user.is_staff:
        return None
    cap = settings.DAILY_GENERATION_CAP
    return cap if cap > 0 else None


def _events_in_window(user):
    return GenerationEvent.objects.filter(
        user=user, created_at__gte=timezone.now() - WINDOW
    )


def check(user) -> None:
    """Raise GenerationLimitReached if this user has no allowance left."""
    cap = cap_for(user)
    if cap is None:
        return

    events = _events_in_window(user)
    used = events.count()
    if used < cap:
        return

    # Time until the oldest counted call drops out of the window.
    oldest = events.order_by("created_at").first()
    resets_in = (oldest.created_at + WINDOW) - timezone.now() if oldest else WINDOW
    raise GenerationLimitReached(used, cap, max(resets_in, timedelta(0)))


def remaining(user) -> int | None:
    """Calls left in the window; None when uncapped."""
    cap = cap_for(user)
    if cap is None:
        return None
    return max(0, cap - _events_in_window(user).count())


@contextmanager
def metering(user, kind: str):
    """Mark a block as generating on behalf of `user`, for `kind` of work.

    Checks the allowance up front so an over-limit request fails before
    spending anything; the before-call hook then re-checks per call, which
    is what stops a 40-call batch roster from blowing through the cap
    after a single successful check.
    """
    check(user)
    token = _context.set((user, kind))
    try:
        yield
    finally:
        _context.reset(token)


def before_call(model: str) -> None:
    """client.generate hook: refuse a call the user cannot afford."""
    ctx = _context.get()
    if ctx is None:
        return  # management commands and the shell are not metered
    check(ctx[0])


def record(model: str, input_tokens: int, output_tokens: int) -> None:
    """client.generate hook: write the ledger row after a successful call."""
    ctx = _context.get()
    if ctx is None:
        return
    user, kind = ctx
    try:
        GenerationEvent.objects.create(
            user=user,
            kind=kind,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    except Exception:
        # Telemetry must never be the reason a DM loses generated content
        # they have already paid for.
        logger.exception("Failed to record GenerationEvent")
