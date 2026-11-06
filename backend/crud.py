"""CRUD operations for AeroRehab database.

CRUD = Create, Read, Update, Delete

These functions handle all database operations so that main.py
stays clean and focused on API logic.
"""
import json
from sqlalchemy.orm import Session
from typing import Optional

from . import models


# ============================================================================
# ASTRONAUT OPERATIONS
# ============================================================================

def create_astronaut(db: Session, astronaut_id: str, name: str = None,
                     mission: str = None, baseline_n: int = 5) -> models.Astronaut:
    """Create a new astronaut profile."""
    astronaut = models.Astronaut(
        id=astronaut_id,
        name=name,
        mission=mission,
        baseline_n=baseline_n
    )
    db.add(astronaut)
    db.commit()
    db.refresh(astronaut)
    return astronaut


def get_astronaut(db: Session, astronaut_id: str) -> Optional[models.Astronaut]:
    """Get astronaut by ID. Returns None if not found."""
    return db.query(models.Astronaut).filter(models.Astronaut.id == astronaut_id).first()


def astronaut_exists(db: Session, astronaut_id: str) -> bool:
    """Check if astronaut exists."""
    return db.query(models.Astronaut).filter(models.Astronaut.id == astronaut_id).first() is not None


# ============================================================================
# SESSION OPERATIONS
# ============================================================================

def create_session(db: Session, astronaut_id: str, session_number: int,
                   features: dict, pain_0_10: int = 0) -> models.Session:
    """Create a new exercise session with features.

    Args:
        db: Database session
        astronaut_id: Astronaut ID
        session_number: Session number (0, 1, 2, ...)
        features: Dictionary with keys: rom_deg, peak_flexion_deg, smoothness,
                  asymmetry, rep_consistency, tempo_s, mean_load
        pain_0_10: Pain rating 0-10

    Returns:
        Created Session object
    """
    session = models.Session(
        astronaut_id=astronaut_id,
        session_number=session_number,
        rom_deg=features["rom_deg"],
        peak_flexion_deg=features["peak_flexion_deg"],
        smoothness=features["smoothness"],
        asymmetry=features["asymmetry"],
        rep_consistency=features["rep_consistency"],
        tempo_s=features.get("tempo_s", 4.0),
        mean_load=features.get("mean_load", 400.0),
        pain_0_10=pain_0_10
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_sessions_for_astronaut(db: Session, astronaut_id: str) -> list[models.Session]:
    """Get all sessions for an astronaut, ordered by session_number."""
    return db.query(models.Session)\
        .filter(models.Session.astronaut_id == astronaut_id)\
        .order_by(models.Session.session_number)\
        .all()


def get_session_count(db: Session, astronaut_id: str) -> int:
    """Count how many sessions an astronaut has."""
    return db.query(models.Session)\
        .filter(models.Session.astronaut_id == astronaut_id)\
        .count()


# ============================================================================
# REPORT OPERATIONS
# ============================================================================

def create_report(db: Session, session_id: int, report_data: dict) -> models.Report:
    """Create a KIS report for a session.

    Args:
        db: Database session
        session_id: Session ID (foreign key)
        report_data: Dictionary from AeroRehabMonitor.ingest_features()
                     Keys: baseline_ready, kis, band, subscores, worse_z,
                           deviations, recommendations

    Returns:
        Created Report object
    """
    report = models.Report(
        session_id=session_id,
        baseline_ready=1 if report_data.get("baseline_ready") else 0,
        kis=report_data.get("kis"),
        band=report_data.get("band"),
        subscores_json=json.dumps(report_data.get("subscores", {})),
        worse_z_json=json.dumps(report_data.get("worse_z", {})),
        deviations_json=json.dumps(report_data.get("deviations", [])),
        recommendations_json=json.dumps(report_data.get("recommendations", []))
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_latest_report(db: Session, astronaut_id: str) -> Optional[models.Report]:
    """Get the most recent report for an astronaut."""
    session = db.query(models.Session)\
        .filter(models.Session.astronaut_id == astronaut_id)\
        .order_by(models.Session.session_number.desc())\
        .first()

    if not session:
        return None

    return db.query(models.Report)\
        .filter(models.Report.session_id == session.id)\
        .first()


def report_to_dict(report: models.Report) -> dict:
    """Convert a Report database object to a dictionary (for API responses).

    Parses JSON fields back into Python objects.
    """
    return {
        "baseline_ready": bool(report.baseline_ready),
        "kis": report.kis,
        "band": report.band,
        "subscores": json.loads(report.subscores_json) if report.subscores_json else {},
        "worse_z": json.loads(report.worse_z_json) if report.worse_z_json else {},
        "deviations": json.loads(report.deviations_json) if report.deviations_json else [],
        "recommendations": json.loads(report.recommendations_json) if report.recommendations_json else []
    }
