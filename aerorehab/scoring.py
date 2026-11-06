"""Personalised baseline, Knee Integrity Score (KIS), and deviation detection.

All worse-than-baseline values are expressed as "worse_z": positive means the
feature moved in the unhealthy direction relative to this astronaut's own baseline.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

# feature: (direction, minimum scale). direction +1 = higher is better, -1 = lower is better.
SPEC = {
    "rom_deg": (+1, 2.0),
    "peak_flexion_deg": (+1, 2.0),
    "smoothness": (-1, 0.5),
    "asymmetry": (-1, 0.02),
    "rep_consistency": (-1, 0.005),
    "tempo_s": (-1, 0.2),     # informational, not scored
    "mean_load": (+1, 5.0),   # informational, not scored
}

# Weights for the Knee Integrity Score (placeholders pending clinical validation).
WEIGHTS = {
    "rom_deg": 0.20,
    "peak_flexion_deg": 0.10,
    "smoothness": 0.25,
    "asymmetry": 0.25,
    "rep_consistency": 0.20,
}

CUSUM_K = 0.5          # slack per session, in SD units
CUSUM_H = 4.0          # alarm threshold
PERSIST_Z = 2.0        # a session counts as "meaningfully worse" at or above this
PERSIST_N = 3          # consecutive such sessions trigger a persistence alarm


@dataclass
class Baseline:
    center: dict
    scale: dict

    @classmethod
    def fit(cls, feature_dicts):
        center, scale = {}, {}
        for k, (_, floor) in SPEC.items():
            vals = np.array([f[k] for f in feature_dicts], dtype=float)
            med = float(np.median(vals))
            mad = 1.4826 * float(np.median(np.abs(vals - med)))  # robust SD estimate
            center[k] = med
            scale[k] = max(mad, floor)
        return cls(center, scale)

    def worse_z(self, feats):
        out = {}
        for k, (direction, _) in SPEC.items():
            z = (feats[k] - self.center[k]) / self.scale[k]
            out[k] = float(-direction * z)
        return out


def sub_score(worse):
    """0-100 sub-score: 100 at or better than baseline, falling steeply as it worsens."""
    if worse <= 0:
        return 100.0
    return 200.0 / (1.0 + math.exp(0.8 * worse))


def integrity_score(worse):
    subs = {k: sub_score(worse[k]) for k in WEIGHTS}
    total = sum(WEIGHTS.values())
    kis = sum(WEIGHTS[k] * subs[k] for k in WEIGHTS) / total
    return round(kis, 1), {k: round(v, 1) for k, v in subs.items()}


def band_for(kis):
    if kis >= 80:
        return "GREEN"
    if kis >= 60:
        return "YELLOW"
    return "RED"


@dataclass
class Deviation:
    session_id: int
    feature: str
    kind: str
    worse_z: float


@dataclass
class DeviationTracker:
    cusum: dict = field(default_factory=dict)
    streak: dict = field(default_factory=dict)

    def update(self, session_id, worse):
        events = []
        for k in WEIGHTS:
            w = worse[k]
            self.cusum[k] = max(0.0, self.cusum.get(k, 0.0) + w - CUSUM_K)
            if self.cusum[k] > CUSUM_H:
                events.append(Deviation(session_id, k, "sustained drift (CUSUM)", round(w, 2)))
                self.cusum[k] = 0.0  # reset after alarm
            self.streak[k] = self.streak.get(k, 0) + 1 if w >= PERSIST_Z else 0
            if self.streak[k] == PERSIST_N:
                events.append(Deviation(session_id, k,
                                        f"{PERSIST_N} consecutive sessions >= {PERSIST_Z} SD worse",
                                        round(w, 2)))
        return events
