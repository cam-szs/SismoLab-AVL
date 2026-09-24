"""Small HTTP boundary for the React client.

Business rules belong in domain and services. This module only exposes
serializable application state until the corresponding services are ready.
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI


app = FastAPI(title="SismoLab AVL API", version="0.1.0")


@app.get("/api/health")
def health() -> dict[str, str]:
    """Return a cheap endpoint used to verify the local connection."""
    return {"status": "ok"}


@app.get("/api/state")
def state() -> dict[str, Any]:
    """Return the initial shape consumed by the React dashboard."""
    return {
        "status": "scaffold",
        "message": "Backend connected; domain services are pending implementation.",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "normal",
        "clock": None,
        "events": [],
        "queue": [],
        "metrics": {
            "active": 0,
            "archived": 0,
            "pending": 0,
            "expensive_access": 0,
        },
    }