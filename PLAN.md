# AeroRehab: Project Plan

Goal: a working, demo-ready prototype that a judge can open in a browser, enter (or simulate) an astronaut's knee-exercise session, and see a Knee Integrity Score, deviation alerts, and clear next-step advice. Keep it simple and finish it. Depth comes from the clinical reasoning and the honesty about limits, not from complex tech.

## 1. Scope (MVP vs. later)

| Must have (MVP) | Nice to have (only if time remains) | Cut |
|---|---|---|
| Log a session (simulated or manual values) | Body-map figure (clickable knee/hip/calf) | Real sensor hardware |
| Personal baseline after 5 sessions | Gamification and streaks | Deep learning models |
| Knee Integrity Score + GREEN/YELLOW/RED | Offline PWA (service worker) | Real NASA data pipeline |
| Trend chart for score and key features | Exportable downlink report (PDF/JSON) | Login and multi-user auth |
| Alerts + safety advice (pain rule) | Voice or text explanations | Mobile app |
| Demo with 2-3 simulated astronauts | More exercises | |

## 2. Architecture (kept deliberately simple)

```
Browser (HTML + JS + Chart.js)
        |  HTTP/JSON
FastAPI backend (Python)
        |-- aerorehab/ (AI + scoring code, already built)
        |-- SQLite database (one file, no setup)
        |-- logs/ (JSONL, offline record)
```

- **Frontend:** plain HTML, CSS, and JavaScript, served by FastAPI. No React or build step needed.
- **Backend:** FastAPI. Few endpoints, all JSON.
- **Database:** SQLite (`users`, `sessions`, `reports`). Simple and works offline.
- **AI:** Statistical baseline, weighted score, CUSUM drift detection, and rules. This is an honest "AI" for a prototype: personal baselines and anomaly detection. A deep-learning model is not needed and would not be better with synthetic data.

## 3. API contract (agree this first, so frontend and backend can work in parallel)

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/users` | Create an astronaut profile (name, id) |
| POST | `/api/users/{id}/sessions` | Submit a session (angle series or simulated, pain 0-10) |
| GET | `/api/users/{id}/status` | Latest KIS, band, baseline progress |
| GET | `/api/users/{id}/history` | List of past reports for charts |
| GET | `/api/users/{id}/recommendations` | Latest advice list |
| POST | `/api/simulate/{scenario}` | Generate demo data for a scenario |

## 4. Roles

| Person | Main job | Also helps with |
|---|---|---|
| **Abdullah** (AI + backend lead) | Backend API, database, connect `aerorehab/` to it, repo setup | AI tuning, code review |
| **Bisma** (clinical lead) | Thresholds, exercise list, advice wording, safety rules, clinical references | Frontend text and content review |
| **Talal** (frontend) | Pages: dashboard, log session, history, advice | Demo video and slides |
| **Fatima / Kashaf** (optional) | Testing, README, slides, research for the report | Demo rehearsal |

Ground rule: nothing gets to `main` without someone else reviewing the pull request.

## 5. Step-by-step plan

**Step 0: Setup (Day 1, about 2 hours)**
- Create one GitHub repo, add everyone as collaborators.
- Folder layout: `backend/`, `frontend/`, `aerorehab/`, `tests/`, `docs/`.
- Branch rule: `main` (stable), and `feature/<name>` for each person's work.
- Done when: everyone can clone, run `python -m pytest`, and open a blank page.

**Step 1: Lock the API contract (Day 1, 1 hour, all together)**
- Agree the endpoints above and the JSON shape for one session and one report.
- Write it in `docs/api.md`.
- Done when: frontend can mock the responses without the backend running.

**Step 2: Backend skeleton (Day 1-2, Abdullah)**
- FastAPI app with the endpoints, returning mock data first.
- Then wire the real `AeroRehabMonitor` into `/sessions` and `/status`.
- Done when: `curl` or the FastAPI docs page (`/docs`) shows a real KIS after 6 simulated sessions.

**Step 3: Frontend pages (Day 2-3, Talal, mock data first)**
- Dashboard: big KIS number with band color, last advice, trend chart (Chart.js).
- Log session: simple form (ROM, peak flexion, asymmetry, pain) or a "run simulated set" button.
- History: table of past sessions.
- Done when: all pages work against the mock API, then against the real one.

**Step 4: Clinical content (Day 1-3, Bisma, in parallel)**
- Write the 5 feature explanations in plain language.
- Review and adjust advice text in `aerorehab/recommend.py`.
- Set pain thresholds (current placeholders: 4 and 7) and confirm the safety wording.
- Add 2-3 exercise lines for the advice (for example, slow eccentric lowering, controlled range).
- Write a short references list (NASA HRP pages, published ARED / bone-loss studies) in `docs/references.md`.
- Done when: every advice line has a clinical reason written next to it.

**Step 5: AI check (Day 3, Abdullah)**
- Confirm that the simulated scenarios give the expected bands (healthy stays GREEN, decline goes RED).
- Reduce noisy alarms (dedupe CUSUM repeats for the same feature in a short window).
- Write `docs/method.md`: formulas, weights, and limits, in simple words for judges.
- Done when: the 4 demo scenarios behave as described in the README.

**Step 6: Integrate and test (Day 4, everyone)**
- Merge the feature branches. Fix the integration issues.
- Test three real flows by hand: new user → 5 sessions → status; pain 8 → STOP message; decline → alert and history.
- Done when: a fresh laptop can run the whole project from the README in under 10 minutes.

**Step 7: Demo and submission (Day 5, everyone)**
- 2-3 minute demo video: problem (muscle and bone loss, communication delay) → live flow → why it works offline → limits and next steps.
- Slide deck or one-page summary. Judges care about "why this matters" and "how we know it works."
- Rehearse once. Record the video with a backup.
- Done when: video, repo link, and README are submitted before the deadline.

## 6. Daily check-in (15 min, every day)
1. What got done yesterday?
2. What is blocked?
3. What is the one thing finished today?

## 7. Risks and how to handle them

| Risk | What to do |
|---|---|
| Time runs short | Cut to the MVP column. Never cut the safety rules or the limitations section. |
| Frontend and backend don't match | Freeze the API contract in Step 1. Change it only by agreement. |
| Scores look random | Check the simulated scenarios first (Step 5). Don't trust one session. |
| Clinical claims too strong | Use "prototype", "simulated data", and "to be validated" in every slide. |
| Team member unavailable | Each task has a backup owner. Keep the README updated so anyone can pick up work. |

## 8. Honesty statement for the submission
- All data is simulated. The sensor pipeline is designed to swap in real sensor data.
- Thresholds and weights are placeholders pending clinical validation.
- The tool supports, and does not replace, flight surgeon or crew medical decisions.
