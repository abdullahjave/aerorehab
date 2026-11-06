# AeroRehab API (v0.1)

Base URL (local): `http://127.0.0.1:8000`. Interactive docs: `/docs`.

All responses are JSON. Prototype only: data is kept in memory and logged to `logs/<user>.jsonl`.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/users/{user_id}` | Create an astronaut profile. 409 if it exists. |
| POST | `/api/users/{user_id}/sessions` | Submit one session (features + pain). Returns a report. |
| GET | `/api/users/{user_id}/status` | Latest KIS, band, subscores, flags, recommendations. |
| GET | `/api/users/{user_id}/history` | List of per-session KIS, band, features (for charts). |
| GET | `/api/users/{user_id}/recommendations` | Advice list from the latest session. |
| POST | `/api/simulate/{scenario}?user_id=demo` | Create user and feed a simulated scenario. |

Scenarios: `healthy`, `gradual_decline`, `asymmetric_form`, `pain_flag`.

## Session body (POST sessions)

```json
{
  "rom_deg": 115,
  "peak_flexion_deg": 120,
  "smoothness": 12.5,
  "asymmetry": 0.01,
  "rep_consistency": 0.01,
  "tempo_s": 4.0,
  "mean_load": 400,
  "pain_0_10": 0
}
```

Validation: `rom_deg` 10–200, `asymmetry` 0–1, `pain_0_10` 0–10. Invalid input returns 422.

## Report (response)

```json
{
  "session_id": 6,
  "baseline_ready": true,
  "kis": 84.2,
  "band": "GREEN",
  "subscores": {"rom_deg": 100.0, "smoothness": 100.0},
  "features": {"rom_deg": 115.0},
  "deviations": [],
  "recommendations": [{"level": "INFO", "message": "Within your baseline. Continue the prescribed program."}]
}
```

- `band`: GREEN (≥ 80), YELLOW (≥ 60), RED (< 60). `null` until the baseline is ready.
- `baseline_ready`: becomes `true` after 5 sessions.
- `recommendations[].level`: INFO, ADVISORY, PRIORITY, STOP.

## Units and meaning

| Field | Meaning |
|---|---|
| rom_deg | Knee range of motion, degrees |
| peak_flexion_deg | Maximum knee bend, degrees |
| smoothness | Mean jerk normalised by ROM (higher = less controlled) |
| asymmetry | Left/right load difference, 0 = balanced |
| rep_consistency | Coefficient of variation of rep peaks (higher = less consistent) |
| tempo_s | Seconds per rep |
| mean_load | Average load, simulated units |

Values are provisional and must be validated by clinicians before real use.
