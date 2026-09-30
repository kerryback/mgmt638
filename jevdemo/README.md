# Jev playground

An interactive page for Jev, TypeSafe's System One model: type a **state** and a
set of **questions**, press Run, get typed answers back from one `system_one`
call.

## Running it

Once, to set up:

```
cd jevdemo
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Then, each time:

```
export OPENROUTER_API_KEY=sk-or-...
.venv/bin/python -m uvicorn app:app --reload --port 8000
```

and open <http://127.0.0.1:8000>. Jev is reached through OpenRouter, so it is
your OpenRouter key that authenticates, not a TypeSafe key. If port 8000 is
already taken, any other port works — `--port 8050`, say.

## The point of the demo

Every other LLM call in this course asks a chat model for JSON and then defends
against what comes back. `newsagent/agents.py` and `earnings/llm.py` both carry
a `_FENCE` regex, a brace-hunting fallback, and a "return None rather than
invent" branch. That machinery exists because a chat model returns text, and
text can be malformed.

Jev does not return text. It takes typed questions and returns typed answers, so
[`jev.py`](jev.py) — the only file here that talks to the model — has no parsing
in it at all.

## The demos

The dropdown holds three demos and a blank slate. They are worth running in
order — each one makes a different argument.

**Support ticket** — the three question types side by side on a one-line state.
The smallest thing that shows what Jev is.

**Earnings call** — two points. The state is structured JSON (company, speaker,
quarter, quote), not a blob, so "does management sound confident" is asked of the
CFO's words in context. And `cuts_guidance` carries `criteria` on a Noul, which
pins down what counts as a cut instead of leaving the model to guess — with them,
"gross margin at the low end of our prior range" comes back at 0.89. Watch
`hedging`: the quote buries a capex cut between "bookings remain healthy" and
"we want to be prudent", and Jev calls it `cushioned` at 0.98.

**Company screen** — nine typed judgments in one round trip, about 250 ms. This
is the argument for using Jev over a chat model in a pipeline. Note that
`asset_light` (0.18) correctly inverts `capital_intensive` (0.90), and that
`cyclicality` reads "defensive" off a single clause about the last two
recessions.

**New — blank slate** — one field, one question, and it runs as-is. Edit it into
whatever you are actually asking.

## The three question types

"Noul" is short for Ber**noul**li, and that is the whole idea: the answer is a
Bernoulli distribution, and the number you get back is its parameter *p*.

| Type | You give it | You get back |
|---|---|---|
| `Noul` | instructions, optionally `criteria` for true/false | `noul`: *p*, the probability the answer is yes |
| `Choice` | `criteria` as a dict of options | `choice`, `confidence`, and `probabilities` over every option |
| `Score` | `criteria` as a ranked list | `score`: a **continuous** position on the scale, plus `legend`, `confidence`, `probabilities` |

Three things are worth pausing on in class:

- A Noul is not a boolean. `0.99` and `0.55` are both "true" at a 0.5 threshold
  and mean very different things. That number is a signal you can size on.
- A Noul carries no `confidence`, and the Bernoulli reading says why: *p*
  specifies the distribution completely, so there is nothing left to summarize.
  A Choice or Score spreads probability over several outcomes, so it needs one.
- *p* is a probability, not a magnitude. Asked "is this candidate strong in
  Python?" about someone who writes "my experience is in Java and Go", a Noul
  returns 0.03 — the chance the answer is yes, not a 3% skill rating. When the
  question is really *how much*, use a Score. That is why `capital_intensive` in
  the Company screen demo is a Noul while `moat` is a Score: "narrow" sits
  between "none" and "wide", and a Score interpolates. An answer of `1.82` on
  `["low", "medium", "high"]` is most of the way from medium to high, which a
  three-way Choice cannot express.

## Files

| File | What it does |
|---|---|
| `config.py` | Connection settings and the demos on the dropdown |
| `jev.py` | The only module that talks to Jev |
| `app.py` | Two routes: the page, and `POST /api/run` |
| `page.html` | The UI. Vanilla JS, no build step |
| `test_jevdemo.py` | Tests, including live calls |

## Reaching Jev

```python
AsyncTypeSafeClient(
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url="https://openrouter.ai/api",
    model="~typesafe/jev-latest",
)
```

Note the tilde. `~typesafe/jev-latest` is OpenRouter's reference to the System
One surface. It is **not** the same thing as `typesafe/jev-router`, which is what
shows up in OpenRouter's chat-completions catalogue — Jev is not a chat model and
cannot be called with an OpenAI client. `jev-latest` is an alias; the response
reports the snapshot that actually answered, currently
`typesafe/jev-1.13-20260917`.

## Tests

```
set -a; . ~/.env; set +a
.venv/bin/python -m pytest test_jevdemo.py -v
```

The Jev tests are live rather than mocked, and skip if there is no API key. A
mocked test of a demo whose whole claim is "the model returns typed answers"
would only prove the mock was written correctly.
