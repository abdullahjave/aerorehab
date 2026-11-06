"""AeroRehab backend (FastAPI). SQLite database for persistence.

Run from the project root:
    uvicorn backend.main:app --reload
Docs: http://127.0.0.1:8000/docs
"""
from __future__ import annotations

from pathlib import Path
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from aerorehab import AeroRehabMonitor, scenario
from .database import get_db, init_db
from . import crud

LOG_DIR = Path("logs")
FRONTEND = Path(__file__).resolve().parent.parent / "frontend" / "index.html"

app = FastAPI(title="AeroRehab API", version="0.2")


@app.on_event("startup")
def startup_event():
    """Initialize database on app startup."""
    init_db()
    print("✅ Database initialized: aerorehab.db")


class SessionIn(BaseModel):
    rom_deg: float = Field(..., gt=10, lt=200, description="Range of motion (deg)")
    peak_flexion_deg: float = Field(..., gt=0, lt=200)
    smoothness: float = Field(..., ge=0)
    asymmetry: float = Field(..., ge=0, le=1)
    rep_consistency: float = Field(..., ge=0)
    tempo_s: float = Field(4.0, gt=0, description="Seconds per rep (optional)")
    mean_load: float = Field(400.0, ge=0, description="Average load, simulated units (optional)")
    pain_0_10: int = Field(0, ge=0, le=10)


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
def create_user(user_id: str, db: Session = Depends(get_db)):
    if crud.astronaut_exists(db, user_id):
        raise HTTPException(409, "user already exists")
    crud.create_astronaut(db, user_id, baseline_n=5)
    return {"user_id": user_id, "baseline_sessions_needed": 5}


@app.post("/api/users/{user_id}/sessions")
def add_session(user_id: str, body: SessionIn, db: Session = Depends(get_db)):
    # Check if astronaut exists
    astronaut = crud.get_astronaut(db, user_id)
    if not astronaut:
        raise HTTPException(404, f"unknown user '{user_id}'. Create it with POST /api/users/{{id}}")

    # Get all previous sessions to rebuild monitor state
    sessions = crud.get_sessions_for_astronaut(db, user_id)

    # Rebuild AeroRehabMonitor from database
    mon = AeroRehabMonitor(user_id, baseline_n=astronaut.baseline_n, log_path=LOG_DIR / f"{user_id}.jsonl")
    for sess in sessions:
        feats = {
            "rom_deg": sess.rom_deg,
            "peak_flexion_deg": sess.peak_flexion_deg,
            "smoothness": sess.smoothness,
            "asymmetry": sess.asymmetry,
            "rep_consistency": sess.rep_consistency,
            "tempo_s": sess.tempo_s,
            "mean_load": sess.mean_load,
        }
        mon.ingest_features(sess.session_number, feats, sess.pain_0_10)

    # Process new session
    feats = body.model_dump(exclude={"pain_0_10"})
    feats["tempo_s"] = body.tempo_s
    feats["mean_load"] = body.mean_load
    session_num = len(sessions)
    report = mon.ingest_features(session_num, feats, body.pain_0_10)

    # Save to database
    db_session = crud.create_session(db, user_id, session_num, feats, body.pain_0_10)
    report_dict = asdict(report)
    crud.create_report(db, db_session.id, report_dict)

    return _report_json(report)


@app.post("/api/simulate/{scenario_name}")
def simulate(scenario_name: str, user_id: str = "demo", db: Session = Depends(get_db)):
    """Create a user and feed it a full simulated scenario (for demos)."""
    try:
        sessions = scenario(scenario_name, seed=1)
    except ValueError as e:
        raise HTTPException(400, str(e))

    # Create user if doesn't exist
    if not crud.astronaut_exists(db, user_id):
        crud.create_astronaut(db, user_id, baseline_n=5)

    astronaut = crud.get_astronaut(db, user_id)

    # Create monitor and ingest all sessions
    mon = AeroRehabMonitor(user_id, baseline_n=astronaut.baseline_n, log_path=LOG_DIR / f"{user_id}.jsonl")
    reports = []

    for i, s in enumerate(sessions):
        report = mon.ingest(s)
        reports.append(report)

        # Save to database
        feats = report.features
        db_session = crud.create_session(db, user_id, i, feats, s.pain_0_10)
        report_dict = asdict(report)
        crud.create_report(db, db_session.id, report_dict)

    return {"user_id": user_id, "sessions_added": len(reports), "latest": _report_json(reports[-1])}


@app.get("/api/users/{user_id}/status")
def status(user_id: str, db: Session = Depends(get_db)):
    astronaut = crud.get_astronaut(db, user_id)
    if not astronaut:
        raise HTTPException(404, f"unknown user '{user_id}'. Create it with POST /api/users/{{id}}")

    sessions = crud.get_sessions_for_astronaut(db, user_id)
    if not sessions:
        return {"user_id": user_id, "sessions": 0, "baseline_ready": False}

    # Get latest report
    latest_report = crud.get_latest_report(db, user_id)
    if not latest_report:
        return {"user_id": user_id, "sessions": len(sessions), "baseline_ready": False}

    report_data = crud.report_to_dict(latest_report)
    latest_session = sessions[-1]

    return {
        "user_id": user_id,
        "sessions": len(sessions),
        "session_id": latest_session.session_number,
        "features": {
            "rom_deg": round(latest_session.rom_deg, 3),
            "peak_flexion_deg": round(latest_session.peak_flexion_deg, 3),
            "smoothness": round(latest_session.smoothness, 3),
            "asymmetry": round(latest_session.asymmetry, 3),
            "rep_consistency": round(latest_session.rep_consistency, 3),
            "tempo_s": round(latest_session.tempo_s, 3),
            "mean_load": round(latest_session.mean_load, 3),
        },
        **report_data
    }


@app.get("/api/users/{user_id}/history")
def history(user_id: str, db: Session = Depends(get_db)):
    astronaut = crud.get_astronaut(db, user_id)
    if not astronaut:
        raise HTTPException(404, f"unknown user '{user_id}'. Create it with POST /api/users/{{id}}")

    sessions = crud.get_sessions_for_astronaut(db, user_id)
    result = []

    for sess in sessions:
        if sess.report:
            report_data = crud.report_to_dict(sess.report)
            result.append({
                "session_id": sess.session_number,
                "kis": report_data.get("kis"),
                "band": report_data.get("band"),
                "features": {
                    "rom_deg": round(sess.rom_deg, 3),
                    "peak_flexion_deg": round(sess.peak_flexion_deg, 3),
                    "smoothness": round(sess.smoothness, 3),
                    "asymmetry": round(sess.asymmetry, 3),
                    "rep_consistency": round(sess.rep_consistency, 3),
                    "tempo_s": round(sess.tempo_s, 3),
                    "mean_load": round(sess.mean_load, 3),
                }
            })

    return result


@app.get("/api/users/{user_id}/recommendations")
def recommendations(user_id: str, db: Session = Depends(get_db)):
    astronaut = crud.get_astronaut(db, user_id)
    if not astronaut:
        raise HTTPException(404, f"unknown user '{user_id}'. Create it with POST /api/users/{{id}}")

    latest_report = crud.get_latest_report(db, user_id)
    if not latest_report:
        return []

    report_data = crud.report_to_dict(latest_report)
    return report_data.get("recommendations", [])
