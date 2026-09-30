"""Connection settings and the demos the playground starts from.

Jev is reached through OpenRouter, which fronts TypeSafe's API as a compatible
gateway. Note the tilde: `~typesafe/jev-latest` is OpenRouter's reference to the
System One surface, and it is NOT the same thing as `typesafe/jev-router` in
OpenRouter's chat-completions catalogue. Jev is not a chat model and cannot be
called with an OpenAI client.

The key that authenticates is your OPENROUTER_API_KEY, not a TypeSafe key.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent

BASE_URL = "https://openrouter.ai/api"
MODEL = "~typesafe/jev-latest"      # an alias; the response reports the snapshot
API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
TIMEOUT = 30.0

# Three demos and a blank slate. Each demo makes a different point, so they are
# worth running in order rather than picking one:
#
#   Support ticket  -- the three question types side by side on a one-line state
#   Earnings call   -- state is structured JSON, and a Score can rank a judgment
#                      that has no natural number attached to it
#   Company screen  -- nine questions in a single call, which is the argument for
#                      using this over a chat model in a pipeline
#
# NEW_PRESET is deliberately the smallest thing that still runs.
NEW_PRESET = "New — blank slate"

PRESETS: dict[str, dict] = {
    "Support ticket": {
        "state": {"ticket": "I was charged twice. Please fix this ASAP."},
        "questions": {
            "billing": {
                "type": "noul",
                "instructions": "Is this ticket about billing?",
            },
            "tone": {
                "type": "choice",
                "instructions": "What is the customer's tone?",
                "criteria": {"calm": None, "frustrated": None, "angry": None},
            },
            "urgency": {
                "type": "score",
                "instructions": "How urgently does this need a human?",
                "criteria": ["low", "medium", "high"],
            },
        },
    },
    # State is structured, not a blob: Jev sees the speaker and the quarter, so
    # "does management sound confident" is asked of the CFO's words in context.
    # The criteria on a Noul show how to pin down a term the model would
    # otherwise have to guess at -- here, what counts as a guidance cut.
    "Earnings call": {
        "state": {
            "company": "Cadence Materials",
            "ticker": "CDMT",
            "quarter": "Q3 2026",
            "speaker": "CFO",
            "quote": (
                "We are trimming full-year capex by about ten percent and now expect "
                "gross margin at the low end of our prior range. Bookings remain "
                "healthy, and we are not changing our view of the second half, but "
                "we want to be prudent given what we are seeing in Europe."
            ),
        },
        "questions": {
            "cuts_guidance": {
                "type": "noul",
                "instructions": "Is management lowering guidance?",
                "criteria": {
                    "true": "A forward-looking number is reduced, narrowed downward, or steered to the low end.",
                    "false": "Guidance is reaffirmed, raised, or not addressed.",
                },
            },
            "mentions_margins": {
                "type": "noul",
                "instructions": "Does the speaker discuss gross margin?",
            },
            "hedging": {
                "type": "choice",
                "instructions": "How direct is the speaker being about the bad news?",
                "criteria": {
                    "direct": "States the negative plainly.",
                    "cushioned": "States it, but surrounds it with positives.",
                    "evasive": "Avoids naming the negative at all.",
                },
            },
            "confidence_tone": {
                "type": "score",
                "instructions": "How confident does management sound about the outlook?",
                "criteria": ["defensive", "measured", "confident"],
            },
        },
    },
    # Nine typed judgments, one round trip. Ask a chat model for this and you get
    # a JSON blob you have to parse, validate and repair; the count in the stats
    # panel is the point of the demo.
    "Company screen": {
        "state": {
            "company": "Northwind Logistics",
            "description": (
                "Northwind operates a network of 41 temperature-controlled warehouses "
                "leased on 15-year terms, serving grocery chains under multi-year "
                "contracts that renew automatically. Its two largest customers accounted "
                "for 58% of revenue last year. Volumes track food retail, which held up "
                "through the last two recessions. Rates are set annually and have risen "
                "with an inflation index in every contract since 2019. The company has "
                "spent roughly 9% of revenue on maintenance capex each year and is "
                "building three new sites. Refrigerant handling and food-safety rules "
                "are enforced by federal and state regulators."
            ),
        },
        "questions": {
            "capital_intensive": {
                "type": "noul",
                "instructions": "Is this a capital-intensive business?",
            },
            "recurring_revenue": {
                "type": "noul",
                "instructions": "Is revenue recurring or contracted rather than transactional?",
            },
            "customer_concentration": {
                "type": "noul",
                "instructions": "Is there meaningful customer concentration risk?",
            },
            "regulatory_exposure": {
                "type": "noul",
                "instructions": "Is the business materially exposed to regulation?",
            },
            "asset_light": {
                "type": "noul",
                "instructions": "Would you describe this as an asset-light business?",
            },
            "moat": {
                "type": "score",
                "instructions": "How durable is the competitive advantage?",
                "criteria": ["none", "narrow", "wide"],
            },
            "cyclicality": {
                "type": "score",
                "instructions": "How sensitive are results to the economic cycle?",
                "criteria": ["defensive", "neutral", "cyclical"],
            },
            "pricing_power": {
                "type": "score",
                "instructions": "How much pricing power does the company have?",
                "criteria": ["weak", "moderate", "strong"],
            },
            "stage": {
                "type": "choice",
                "instructions": "What stage is this business in?",
                "criteria": {
                    "early": None,
                    "scaling": None,
                    "mature": None,
                    "declining": None,
                },
            },
        },
    },
    # "blank" means these are shown as greyed-out placeholder text rather than
    # loaded as content: the boxes start genuinely empty, and this is the shape
    # of what to type into them.
    NEW_PRESET: {
        "blank": True,
        "state": {"text": "Paste whatever you want judged here."},
        "questions": {
            "my_question": {
                "type": "noul",
                "instructions": "Ask a yes-or-no question about it.",
            }
        },
    },
}

DEFAULT_PRESET = "Support ticket"

# Templates appended by the "+ Noul / + Choice / + Score" buttons.
TEMPLATES = {
    "noul": {"type": "noul", "instructions": "Yes-or-no question?"},
    "choice": {
        "type": "choice",
        "instructions": "Which one?",
        "criteria": {"first": None, "second": None, "third": None},
    },
    "score": {
        "type": "score",
        "instructions": "How much?",
        "criteria": ["low", "medium", "high"],
    },
}
