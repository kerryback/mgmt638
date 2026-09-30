"""FastAPI wrapper around the Jev playground.

The web layer is deliberately thin -- it exists so Jev can be driven from a
browser in class, not because there is anything to learn from it here.

`GET /` serves the page. `POST /api/run` forwards a state and a question set to
Jev and returns the typed answers. Errors from the SDK are passed through with
their own wording, because they already say the useful thing
('Question "tone" requires "criteria".') and rewording them would only put a
second vocabulary between the student and the API.
"""

from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

import config
import jev

app = FastAPI(title="Jev playground", docs_url="/docs")


class RunRequest(BaseModel):
    state: object
    questions: dict


@app.post("/api/run")
async def api_run(req: RunRequest):
    if not req.questions:
        raise HTTPException(400, "Add at least one question.")
    try:
        return await jev.run(req.state, req.questions)
    except jev.TypeSafeError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:                     # missing key
        raise HTTPException(500, str(exc)) from exc


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    page = (config.ROOT / "page.html").read_text()
    # ensure_ascii=False so names keep their real characters in the page source;
    # it is served as UTF-8 either way.
    dump = lambda obj: json.dumps(obj, ensure_ascii=False)
    page = (
        page.replace("__PRESETS__", dump(config.PRESETS))
        .replace("__TEMPLATES__", dump(config.TEMPLATES))
        .replace("__DEFAULT__", dump(config.DEFAULT_PRESET))
        .replace("__NEW__", dump(config.NEW_PRESET))
    )
    return HTMLResponse(page)
