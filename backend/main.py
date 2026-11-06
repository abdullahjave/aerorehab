"""AeroRehab backend (FastAPI). Prototype: in-memory store, JSONL log per user.

Run from the project root:
    uvicorn backend.main:app --reload
Docs: http://127.0.0.1:8000/docs
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from aerorehab import AeroRehabMonitor, scenario

LOG_DIR = Path("logs")
FRONTEND = Path(__file__).resolve().parent.parent / "frontend" / "index.html"

app = FastAPI(title="AeroRehab API", version="0.1")
monitors: dict[str, AeroRehabMonitor] = {}


class SessionIn(BaseModel):
    rom_deg: float = Field(..., gt=10, lt=200, description="Range of motion (deg)")
    peak_flexion_deg: float = Field(..., gt=0, lt=200)
    smoothness: float = Field(..., ge=0)
    asymmetry: float = Field(..., ge=0, le=1)
    rep_consistency: float = Field(..., ge=0)
    tempo_s: float = Field(4.0, gt=0, description="Seconds per rep (optional)")
    mean_load: float = Field(400.0, ge=0, description="Average load, simulated units (optional)")
    pain_0_10: int = Field(0, ge=0, le=10)


def _get(user_id: str) -> AeroRehabMonitor:
    if user_id not in monitors:
        raise HTTPException(404, f"unknown user '{user_id}'. Create it with POST /api/users/{{id}}")
    return monitors[user_id]


def _report_json(r):
    return {
        "session_id": r.session_id,
        "baseline_ready": r.baseline_ready,
        "kis": r.kis,
        "band": r.band,
        "subscores": r.subscores,
        "features": {k: round(v, 3) for k, v in r.features.items()},
        "deviations": r.deviations,
        "recommendations": r.recommendations,
    }


@app.get("/", include_in_schema=False)
def home():
    if FRONTEND.exists():
        return FileResponse(FRONTEND)
    return {"message": "AeroRehab API. See /docs"}


@app.post("/api/users/{user_id}", status_code=201)
def create_user(user_id: str):
    if user_id in monitors:
        raise HTTPException(409, "user already exists")
    monitors[user_id] = AeroRehabMonitor(user_id, baseline_n=5, log_path=LOG_DIR / f"{user_id}.jsonl")
    return {"user_id": user_id, "baseline_sessions_needed": 5}


@app.post("/api/users/{user_id}/sessions")
def add_session(user_id: str, body: SessionIn):
    mon = _get(user_id)
    feats = body.model_dump(exclude={"pain_0_10"})
    feats["tempo_s"] = body.tempo_s
    feats["mean_load"] = body.mean_load
    r = mon.ingest_features(len(mon.history), feats, body.pain_0_10)
    return _report_json(r)


@app.post("/api/simulate/{scenario_name}")
def simulate(scenario_name: str, user_id: str = "demo"):
    """Create a user and feed it a full simulated scenario (for demos)."""
    try:
        sessions = scenario(scenario_name, seed=1)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if user_id not in monitors:
        create_user(user_id)
    mon = monitors[user_id]
    reports = [mon.ingest(s) for s in sessions]
    return {"user_id": user_id, "sessions_added": len(reports), "latest": _report_json(reports[-1])}


@app.get("/api/users/{user_id}/status")
def status(user_id: str):
    mon = _get(user_id)
    if not mon.history:
        return {"user_id": user_id, "sessions": 0, "baseline_ready": False}
    last = mon.history[-1]
    return {"user_id": user_id, "sessions": len(mon.history), **_report_json(last)}


@app.get("/api/users/{user_id}/history")
def history(user_id: str):
    mon = _get(user_id)
    return [{"session_id": r.session_id, "kis": r.kis, "band": r.band,
             "features": {k: round(v, 3) for k, v in r.features.items()}} for r in mon.history]


@app.get("/api/users/{user_id}/recommendations")
def recommendations(user_id: str):
    mon = _get(user_id)
    return mon.history[-1].recommendations if mon.history else []
