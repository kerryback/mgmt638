"""The only module that talks to Jev.

Compare this file with `newsagent/agents.py` or `earnings/llm.py`. Those ask a
chat model for JSON and then spend most of their lines defending against what
comes back: stripping code fences, hunting for the outermost brace, returning
None when the parse fails. None of that is here, because Jev does not return
text. `system_one` takes typed questions and gives back typed answers, so the
failure mode those files exist to handle cannot occur.

The question types in the SDK are TypedDicts, which is why the JSON typed into
the playground can be handed to `system_one` as-is. Validation is the SDK's job
and its complaints are already readable ('Question "tone" requires "criteria".'),
so they are passed through to the browser rather than reworded here.
"""

from __future__ import annotations

import time

from typesafe_sdk import AsyncTypeSafeClient, TypeSafeError

import config


def client() -> AsyncTypeSafeClient:
    if not config.API_KEY:
        raise RuntimeError(
            "No OPENROUTER_API_KEY in the environment. Jev is reached through "
            "OpenRouter, so it is your OpenRouter key that authenticates."
        )
    return AsyncTypeSafeClient(
        api_key=config.API_KEY,
        base_url=config.BASE_URL,
        model=config.MODEL,
        timeout=config.TIMEOUT,
    )


async def run(state, questions: dict) -> dict:
    """Send one state and one set of questions. Returns the response plus timing."""
    started = time.perf_counter()
    async with client() as c:
        response = await c.system_one(state=state, questions=questions)
    elapsed = time.perf_counter() - started

    return {
        "model": response.model,
        "elapsed_ms": round(elapsed * 1000),
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
        "answers": {name: a.model_dump() for name, a in response.answers.items()},
    }


__all__ = ["client", "run", "TypeSafeError"]
