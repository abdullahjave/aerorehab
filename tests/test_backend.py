from fastapi.testclient import TestClient

from backend.main import app
from backend.database import Base, SessionLocal
from backend import crud

client = TestClient(app)

GOOD = dict(rom_deg=115, peak_flexion_deg=120, smoothness=12.5, asymmetry=0.01,
            rep_consistency=0.01, pain_0_10=0)


def setup_function():
    """Clean up test database before each test."""
    # Create tables first
    Base.metadata.create_all(bind=SessionLocal().bind)
    db = SessionLocal()
    # Delete all test data
    db.query(crud.models.Session).delete()
    db.query(crud.models.Report).delete()
    db.query(crud.models.Astronaut).delete()
    db.commit()
    db.close()


def test_manual_flow_reaches_baseline_then_scores():
    client.post("/api/users/a1")
    for _ in range(5):
        r = client.post("/api/users/a1/sessions", json=GOOD)
        assert r.status_code == 200
    r = client.post("/api/users/a1/sessions", json=dict(GOOD, rom_deg=60))
    body = r.json()
    assert body["baseline_ready"] is True
    assert body["kis"] < 100 and body["band"] in {"GREEN", "YELLOW", "RED"}


def test_unknown_user_is_404():
    assert client.get("/api/users/nobody/status").status_code == 404


def test_duplicate_user_is_409():
    client.post("/api/users/x")
    assert client.post("/api/users/x").status_code == 409


def test_simulated_scenario_endpoint():
    r = client.post("/api/simulate/gradual_decline?user_id=demo")
    assert r.status_code == 200
    h = client.get("/api/users/demo/history").json()
    assert len(h) == 20 and h[-1]["band"] in {"YELLOW", "RED"}


def test_bad_input_rejected():
    client.post("/api/users/b1")
    r = client.post("/api/users/b1/sessions", json=dict(GOOD, pain_0_10=42))
    assert r.status_code == 422


def test_data_persists_after_restart():
    """Test that data survives server restart (simulated by creating a new client)."""
    # Create user and add sessions
    client.post("/api/users/persist-test")
    for _ in range(5):
        client.post("/api/users/persist-test/sessions", json=GOOD)

    # Simulate restart by creating a new TestClient
    client2 = TestClient(app)
    r = client2.get("/api/users/persist-test/status")
    assert r.status_code == 200
    body = r.json()
    assert body["sessions"] == 5
    assert body["baseline_ready"] is True