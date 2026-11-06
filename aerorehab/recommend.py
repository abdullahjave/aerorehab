"""Rule-based interventions. Safety rules come first and never increase load."""
from __future__ import annotations

from dataclasses import dataclass

from .scoring import PERSIST_Z, WEIGHTS

LEVELS = ("INFO", "ADVISORY", "PRIORITY", "STOP")

FEATURE_ADVICE = {
    "rom_deg": "Range of motion is dropping. Add a mobility warm-up before loaded sets and hold load this week.",
    "peak_flexion_deg": "Peak knee flexion is below your baseline. Check the device range setting and use the full range.",
    "smoothness": "Movement is less controlled. Slow the lowering (eccentric) phase and reduce load by one step.",
    "asymmetry": "Load is uneven between the inner and outer knee. Check foot placement and alignment, and cue both sides evenly.",
    "rep_consistency": "Rep depth varies a lot. Use a fixed-tempo cue and end the set if depth drops off.",
}


@dataclass
class Recommendation:
    level: str
    message: str


def recommend(band, worse, deviations, pain, baseline_ready):
    recs = []
    if pain >= 7:
        recs.append(Recommendation("STOP",
            "Pain 7 or higher. Stop this session now and notify the crew medical officer per protocol. Do not progress load."))
    elif pain >= 4:
        recs.append(Recommendation("PRIORITY",
            "Pain 4 or higher. Hold load progression, return to the last comfortable level, log it, and flag for flight surgeon review at the next comm window."))

    if not baseline_ready:
        recs.append(Recommendation("INFO",
            "Baseline still building. Continue the routine; no deviations are judged yet."))
        return recs

    sustained = {d.feature for d in deviations}
    for feat in sorted(FEATURE_ADVICE, key=lambda f: -worse[f]):
        if worse[feat] >= PERSIST_Z:
            level = "PRIORITY" if feat in sustained else "ADVISORY"
            suffix = " Trend is sustained over several sessions." if feat in sustained else ""
            recs.append(Recommendation(level, FEATURE_ADVICE[feat] + suffix))

    if band == "RED":
        recs.append(Recommendation("PRIORITY",
            "Knee Integrity Score is in the RED band. Hold progression and flag for flight surgeon review."))
    elif band == "YELLOW" and not any(r.level != "INFO" for r in recs):
        recs.append(Recommendation("ADVISORY",
            "Knee Integrity Score is in the YELLOW band. Monitor closely over the next sessions."))

    if not recs:
        recs.append(Recommendation("INFO", "Within your baseline. Continue the prescribed program."))
    return recs
