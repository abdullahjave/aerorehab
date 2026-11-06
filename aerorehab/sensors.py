"""Synthetic wearable-sensor generator.

Simulates resistive knee-extension sessions: knee flexion angle (deg) and
medial / lateral patellofemoral pressure (simulated units). This is NOT
astronaut data. It lets the pipeline run and be tested offline until real
sensor streams or validated datasets are available.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

FS_HZ = 50.0
BASE_ANGLE_DEG = 5.0


@dataclass
class Session:
    session_id: int
    angle_deg: np.ndarray
    pressure_medial: np.ndarray
    pressure_lateral: np.ndarray
    pain_0_10: int = 0


def simulate_session(session_id, rng, *, n_reps=8, rep_s=4.0, rom_deg=115.0,
                     asymmetry=0.0, roughness=0.05, pain=0):
    """One set of reps.

    asymmetry: -1..1, positive means the medial side carries more load.
    roughness: amplitude (deg) of a 3 Hz wobble, a proxy for poor motor control.
    """
    angles, med, lat = [], [], []
    for _ in range(n_reps):
        T = max(1.5, rep_s * (1 + 0.05 * rng.standard_normal()))
        n = int(round(T * FS_HZ))
        tl = np.arange(n) / FS_HZ
        rep_rom = rom_deg * (1 + 0.02 * rng.standard_normal())
        shape = 0.5 * (1 - np.cos(2 * np.pi * tl / T))  # 0 -> 1 -> 0
        wobble = roughness * np.sin(2 * np.pi * 3.0 * tl + rng.uniform(0, 2 * np.pi)) * shape
        angle = BASE_ANGLE_DEG + rep_rom * shape + wobble + 0.02 * rng.standard_normal(n)
        load = 400.0 * shape * (1 + 0.03 * rng.standard_normal())
        med.append(load * (1 + asymmetry) / 2 + 2 * rng.standard_normal(n))
        lat.append(load * (1 - asymmetry) / 2 + 2 * rng.standard_normal(n))
        angles.append(angle)
    return Session(
        session_id=session_id,
        angle_deg=np.concatenate(angles),
        pressure_medial=np.concatenate(med),
        pressure_lateral=np.concatenate(lat),
        pain_0_10=pain,
    )


def scenario(name, n_sessions=20, seed=0):
    """Named multi-session trajectories used for demos and tests."""
    rng = np.random.default_rng(seed)
    sessions = []
    for i in range(n_sessions):
        frac = i / max(1, n_sessions - 1)
        if name == "healthy":
            kw = dict(rom_deg=115, asymmetry=rng.normal(0, 0.02), roughness=0.05, pain=0)
        elif name == "gradual_decline":
            kw = dict(rom_deg=115 - 22 * frac, asymmetry=0.02,
                      roughness=0.05 + 0.25 * frac, pain=int(3 * frac))
        elif name == "asymmetric_form":
            late = frac >= 0.5
            kw = dict(rom_deg=115, asymmetry=0.35 if late else 0.0,
                      roughness=0.05, pain=2 if late else 0)
        elif name == "pain_flag":
            kw = dict(rom_deg=115, asymmetry=0.02, roughness=0.05,
                      pain=6 if i >= n_sessions - 2 else 0)
        else:
            raise ValueError(f"unknown scenario: {name}")
        sessions.append(simulate_session(i, rng, **kw))
    return sessions
