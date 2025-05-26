from __future__ import annotations

from flask import Flask
from flask.typing import ResponseReturnValue

app = Flask(__name__)

# Register routes defined in sibling module
from . import routes  # noqa: F401  (import side-effects)


@app.after_request
def add_header(resp) -> ResponseReturnValue:  # type: ignore[valid-type]
    # Disable caching so HTMX always gets fresh data
    resp.headers["Cache-Control"] = "no-store"
    return resp
