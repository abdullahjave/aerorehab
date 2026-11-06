"""Run all scenarios offline, print a summary, and save a score chart.

Usage:  python -m aerorehab.demo [output_dir]
"""
from __future__ import annotations

import sys
from pathlib import Path

from .monitor import AeroRehabMonitor
from .sensors import scenario

SCENARIOS = ["healthy", "gradual_decline", "asymmetric_form", "pain_flag"]


def run(outdir="outputs"):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    results = {}
    for name in SCENARIOS:
        mon = AeroRehabMonitor(user_id=f"sim-{name}", log_path=outdir / f"{name}.jsonl")
        reports = [mon.ingest(s) for s in scenario(name, seed=1)]
        results[name] = reports
        last = reports[-1]
        print(f"\n== {name}")
        print(f"   final KIS {last.kis} ({last.band})  deviations flagged: "
              f"{sum(len(r.deviations) for r in reports)}")
        for rec in last.recommendations[:3]:
            print(f"   [{rec['level']}] {rec['message']}")
        print(f"   downlink: {mon.downlink_summary()}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8, 4.5))
        for name, reps in results.items():
            xs = [r.session_id for r in reps if r.kis is not None]
            ys = [r.kis for r in reps if r.kis is not None]
            ax.plot(xs, ys, marker="o", ms=3, label=name)
        ax.axhspan(80, 100, color="#d9f2e3", alpha=0.6, lw=0)
        ax.axhspan(60, 80, color="#fff4cc", alpha=0.6, lw=0)
        ax.axhspan(0, 60, color="#fde0dc", alpha=0.6, lw=0)
        ax.set_xlabel("session")
        ax.set_ylabel("Knee Integrity Score")
        ax.set_ylim(0, 100)
        ax.set_title("AeroRehab simulated trajectories (synthetic data)")
        ax.legend(fontsize=8)
        fig.tight_layout()
        png = outdir / "kis_trajectories.png"
        fig.savefig(png, dpi=130)
        print(f"\nChart saved to {png.resolve()}")
    except ImportError:
        print("\nmatplotlib not installed; skipping chart.")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "outputs")
