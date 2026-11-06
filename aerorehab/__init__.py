"""AeroRehab: offline musculoskeletal monitoring for long-duration spaceflight.

Prototype only. Not a medical device. Thresholds and weights are placeholders
that must be validated by clinicians and physiologists before any real use.
"""
from .sensors import Session, simulate_session, scenario
from .features import extract_features
from .scoring import Baseline, integrity_score, band_for
from .recommend import Recommendation, recommend
from .monitor import AeroRehabMonitor, Report

__all__ = [
    "Session", "simulate_session", "scenario", "extract_features",
    "Baseline", "integrity_score", "band_for", "Recommendation", "recommend",
    "AeroRehabMonitor", "Report",
]
