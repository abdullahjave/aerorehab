# AeroRehab

Prototype for the NASA Space Apps Challenge 2026, "Create Health Monitoring Software for Astronauts on Space Missions."

AeroRehab tracks knee exercise sessions, learns each astronaut's own baseline, and gives a **Knee Integrity Score (KIS)**, deviation alerts, and safety-first advice. It runs offline on the device.

> **Prototype only.** All data is simulated. Thresholds and weights must be validated by clinicians. Not a medical device.

## Project layout

```
aerorehab/   scoring, features, rules, monitor (the AI and logic core)
backend/     FastAPI server (API + serves the frontend)
frontend/    HTML/JS dashboard
tests/       pytest tests for core logic and API
docs/        API contract, method notes, references
PLAN.md      scope, roles, timeline
```

## Setup (one time, about 5 minutes)

Requires Python 3.10 or newer.

```bash
git clone <repo-url>
cd aerorehab
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python -m pytest -q                              # all tests should pass
uvicorn backend.main:app --reload                # then open http://127.0.0.1:8000
python -m aerorehab.demo outputs                 # offline demo, writes a chart
```

API docs: http://127.0.0.1:8000/docs

## Branch and review rules

- `main` is stable. Do not push broken code to it.
- Work on `feature/<your-name>-<topic>`, for example `feature/talal-dashboard`.
- Open a pull request. Another team member reviews it before merge.
- Run `pytest` before opening a pull request.
- Clinical content (thresholds, advice text) is reviewed by Bisma.

## Where things live

| Need to change | File |
|---|---|
| Score weights, bands, thresholds | `aerorehab/scoring.py` |
| Advice text and safety rules | `aerorehab/recommend.py` |
| Features from raw signals | `aerorehab/features.py` |
| API endpoints | `backend/main.py` (contract in `docs/api.md`) |
| Dashboard page | `frontend/index.html` |
| Simulated data | `aerorehab/sensors.py` |
