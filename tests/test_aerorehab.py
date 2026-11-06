import numpy as np
import pytest

from aerorehab import AeroRehabMonitor, Baseline, extract_features, integrity_score, scenario, simulate_session
from aerorehab.scoring import band_for, sub_score


def test_rom_matches_simulated_range():
    rng = np.random.default_rng(0)
    s = simulate_session(0, rng, rom_deg=100.0, roughness=0.0)
    f = extract_features(s)
    assert f["rom_deg"] == pytest.approx(100.0, abs=3.0)
    assert f["tempo_s"] == pytest.approx(4.0, abs=0.3)


def test_asymmetry_detected():
    rng = np.random.default_rng(0)
    balanced = extract_features(simulate_session(0, rng, asymmetry=0.0))
    skewed = extract_features(simulate_session(0, rng, asymmetry=0.4))
    assert skewed["asymmetry"] > balanced["asymmetry"] + 0.2


def test_roughness_raises_smoothness_metric():
    rng = np.random.default_rng(0)
    smooth = extract_features(simulate_session(0, rng, roughness=0.05))
    rough = extract_features(simulate_session(0, rng, roughness=0.6))
    assert rough["smoothness"] > smooth["smoothness"] * 1.2


def test_too_little_motion_rejected():
    rng = np.random.default_rng(0)
    s = simulate_session(0, rng, rom_deg=4.0, roughness=0.0)
    with pytest.raises(ValueError):
        extract_features(s)


def test_sub_score_monotonic_and_bounded():
    vals = [sub_score(w) for w in np.linspace(-2, 6, 50)]
    assert vals[0] == 100.0
    assert all(a >= b for a, b in zip(vals, vals[1:]))
    assert all(0 <= v <= 100 for v in vals)


def test_kis_drops_when_every_feature_worse():
    base = {k: 0.0 for k in ["rom_deg", "peak_flexion_deg", "smoothness", "asymmetry", "rep_consistency"]}
    good, _ = integrity_score(base)
    bad, _ = integrity_score({k: 3.0 for k in base})
    assert good == 100.0
    assert bad < 60 and band_for(bad) == "RED"


def test_baseline_is_robust_to_one_outlier():
    feats = [{"rom_deg": 110, "peak_flexion_deg": 115, "smoothness": 1.0, "asymmetry": 0.02,
              "rep_consistency": 0.01, "tempo_s": 4.0, "mean_load": 400}] * 4
    feats.append(dict(feats[0], rom_deg=40))  # one bad outlier
    b = Baseline.fit(feats)
    assert b.center["rom_deg"] == 110


def test_healthy_trajectory_stays_green_without_alarms():
    mon = AeroRehabMonitor("t-healthy")
    reports = [mon.ingest(s) for s in scenario("healthy", seed=3)]
    judged = [r for r in reports if r.kis is not None]
    assert sum(len(r.deviations) for r in judged) == 0
    assert sum(r.band == "RED" for r in judged) == 0


def test_gradual_decline_is_detected():
    mon = AeroRehabMonitor("t-decline")
    reports = [mon.ingest(s) for s in scenario("gradual_decline", seed=3)]
    assert any(d["feature"] == "rom_deg" for r in reports for d in r.deviations)
    assert reports[-1].kis < reports[5].kis


def test_asymmetric_form_flags_asymmetry():
    mon = AeroRehabMonitor("t-asym")
    reports = [mon.ingest(s) for s in scenario("asymmetric_form", seed=3)]
    assert any(d["feature"] == "asymmetry" for r in reports for d in r.deviations)


def test_pain_triggers_safety_message_and_never_increases_load():
    mon = AeroRehabMonitor("t-pain")
    reports = [mon.ingest(s) for s in scenario("pain_flag", seed=3)]
    msgs = " ".join(r["message"] for r in reports[-1].recommendations).lower()
    assert "hold load progression" in msgs
    assert "increase" not in msgs


def test_high_pain_stop_level():
    rng = np.random.default_rng(0)
    mon = AeroRehabMonitor("t-stop", baseline_n=2)
    mon.ingest(simulate_session(0, rng))
    mon.ingest(simulate_session(1, rng))
    r = mon.ingest(simulate_session(2, rng, pain=8))
    assert any(x["level"] == "STOP" for x in r.recommendations)


def test_offline_log_written_and_downlink_summary(tmp_path):
    log = tmp_path / "log.jsonl"
    mon = AeroRehabMonitor("t-log", baseline_n=3, log_path=log)
    for s in scenario("healthy", n_sessions=6, seed=2):
        mon.ingest(s)
    assert len(log.read_text().splitlines()) == 6
    summary = mon.downlink_summary()
    assert summary["session"] == 5 and summary["band"] in {"GREEN", "YELLOW", "RED"}
