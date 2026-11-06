"""Per-session biomechanical features from raw knee-angle and pressure signals."""
from __future__ import annotations

import numpy as np

from .sensors import FS_HZ, Session


def extract_features(s: Session) -> dict[str, float]:
    a = np.asarray(s.angle_deg, dtype=float)
    p5, p95 = np.percentile(a, [5, 95])
    rom = float(p95 - p5)
    if rom < 10:
        raise ValueError("range of motion too small to analyse; check sensor placement")

    # Rep segmentation: rising crossings of the mid-range level.
    mid = (p5 + p95) / 2
    above = a > mid
    rises = np.flatnonzero(~above[:-1] & above[1:])
    if len(rises) < 2:
        raise ValueError("fewer than 2 full reps detected")
    periods = np.diff(rises) / FS_HZ
    peaks = np.array([a[i:j].max() for i, j in zip(rises[:-1], rises[1:])])

    # Smoothness: mean absolute jerk (3rd derivative) of a lightly smoothed
    # signal, normalised by ROM. Jerk emphasises rapid wobble, which is what
    # poor motor control produces. Higher means less controlled movement.
    smooth = np.convolve(a, np.ones(5) / 5, mode="valid")
    jerk = np.diff(smooth, 3) * FS_HZ ** 3
    smoothness = float(np.mean(np.abs(jerk)) / rom)

    med = float(np.mean(s.pressure_medial))
    lat = float(np.mean(s.pressure_lateral))
    return {
        "rom_deg": rom,
        "peak_flexion_deg": float(p95),
        "smoothness": smoothness,
        "asymmetry": abs(med - lat) / (med + lat),
        "rep_consistency": float(np.std(peaks) / np.mean(peaks)),
        "tempo_s": float(np.median(periods)),
        "mean_load": (med + lat) / 2,
    }
