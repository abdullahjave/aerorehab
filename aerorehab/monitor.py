"""Onboard, offline monitor: ingests sessions, scores them, and logs locally.

Everything runs on-device. Summaries are queued for the next comm window, so
no real-time connection to ground is needed.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .features import extract_features
from .recommend import Recommendation, recommend
from .scoring import Baseline, DeviationTracker, band_for, integrity_score
from .sensors import Session


@dataclass
class Report:
    session_id: int
    features: dict
    baseline_ready: bool
    kis: float | None = None
    band: str | None = None
    subscores: dict = field(default_factory=dict)
    worse_z: dict = field(default_factory=dict)
    deviations: list = field(default_factory=list)
    recommendations: list = field(default_factory=list)


class AeroRehabMonitor:
    def __init__(self, user_id, baseline_n=5, log_path=None):
        self.user_id = user_id
        self.baseline_n = baseline_n
        self.log_path = Path(log_path) if log_path else None
        self._baseline_feats = []
        self.baseline = None
        self.tracker = DeviationTracker()
        self.history = []

    def ingest(self, s: Session) -> Report:
        return self.ingest_features(s.session_id, extract_features(s), s.pain_0_10)

    def ingest_features(self, session_id, feats, pain=0) -> Report:
        """Entry point for manual entry or any pipeline that already has features."""
        if self.baseline is None:
            self._baseline_feats.append(feats)
            if len(self._baseline_feats) >= self.baseline_n:
                self.baseline = Baseline.fit(self._baseline_feats)
            recs = recommend(None, {}, [], pain, baseline_ready=False)
            report = Report(session_id, feats, baseline_ready=self.baseline is not None,
                            recommendations=[asdict(r) for r in recs])
        else:
            worse = self.baseline.worse_z(feats)
            kis, subs = integrity_score(worse)
            band = band_for(kis)
            devs = self.tracker.update(session_id, worse)
            recs = recommend(band, worse, devs, pain, baseline_ready=True)
            report = Report(
                session_id, feats, baseline_ready=True, kis=kis, band=band,
                subscores=subs, worse_z={k: round(v, 2) for k, v in worse.items()},
                deviations=[asdict(d) for d in devs],
                recommendations=[asdict(r) for r in recs],
            )
        self.history.append(report)
        self._log(report)
        return report

    def _log(self, report):
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"user": self.user_id, **asdict(report)}, default=float) + "\n")

    def downlink_summary(self):
        """Compact packet for the next comm window."""
        if not self.history:
            return None
        last = self.history[-1]
        top = [r for r in last.recommendations if r["level"] in ("PRIORITY", "STOP")]
        return {"user": self.user_id, "session": last.session_id, "kis": last.kis,
                "band": last.band, "flags": top}
