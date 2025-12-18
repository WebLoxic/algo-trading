# scripts/sweep_backtest.py
"""
Parameter sweep runner for backtest_model.py.

Usage:
  conda activate deep3d_py310
  python scripts\sweep_backtest.py

It will run the backtester for combinations of:
 - prob_thresholds
 - holds
 - cooldowns
and write scripts/sweep_results.csv with metrics for each run.

Note: this invokes the backtester as a subprocess and reuses its outputs (backtest_metrics.json).
"""
import subprocess
import json
from itertools import product
from pathlib import Path
import time
import csv

BACKTEST_SCRIPT = "python"
BACKTEST_MODULE = "scripts/backtest_model.py"  # relative path to script
OUT_DIR = Path("scripts")
METRICS_FILE = OUT_DIR / "backtest_metrics.json"
RESULT_CSV = OUT_DIR / "sweep_results.csv"

# Sweep configuration (edit as desired)
prob_thresholds = [0.6, 0.7, 0.75, 0.8, 0.85]
holds = [1, 3, 5]
cooldowns = [0, 2, 5]
fees = [0.0005]  # you can add more fee values e.g. 0.001
slips = [0.0002]

symbol = "RELIANCE.NS"
period = "60d"
interval = "5m"

# build combos
combos = list(product(prob_thresholds, holds, cooldowns, fees, slips))
print(f"Running {len(combos)} backtest jobs...")

results = []
for idx, (pt, hold, cooldown, fee, slip) in enumerate(combos, start=1):
    print(f"\n[{idx}/{len(combos)}] pt={pt} hold={hold} cooldown={cooldown} fee={fee} slip={slip}")
    args = [
        BACKTEST_SCRIPT, BACKTEST_MODULE,
        "--symbol", symbol,
        "--period", period,
        "--interval", interval,
        "--prob-threshold", str(pt),
        "--hold", str(hold),
        "--cooldown", str(cooldown),
        "--fee", str(fee),
        "--slip", str(slip),
    ]
    # run subprocess (block until done)
    start = time.time()
    proc = subprocess.run(args, capture_output=True, text=True)
    elapsed = time.time() - start
    if proc.returncode != 0:
        print("Backtest script failed. stderr:")
        print(proc.stderr)
        # log failure row
        results.append({
            "prob_threshold": pt,
            "hold": hold,
            "cooldown": cooldown,
            "fee": fee,
            "slip": slip,
            "success": False,
            "error": proc.stderr[:1000],
            "elapsed_s": elapsed
        })
        # continue to next combo
        continue

    # read metrics JSON produced by backtest_model.py
    try:
        with open(METRICS_FILE, "r") as f:
            metrics = json.load(f)
    except Exception as e:
        print("Failed to read metrics JSON:", e)
        results.append({
            "prob_threshold": pt,
            "hold": hold,
            "cooldown": cooldown,
            "fee": fee,
            "slip": slip,
            "success": False,
            "error": f"metrics_read_err:{e}",
            "elapsed_s": elapsed
        })
        continue

    # flatten selected metrics for CSV
    row = {
        "prob_threshold": pt,
        "hold": hold,
        "cooldown": cooldown,
        "fee": fee,
        "slip": slip,
        "success": True,
        "elapsed_s": elapsed,
    }
    # copy relevant numeric metrics if present
    for k in ("cumulative_return","total_return","sharpe","max_drawdown","n_trades","win_rate","avg_win","avg_loss","profit_factor"):
        row[k] = metrics.get(k)
    results.append(row)

# write results CSV (sorted by sharpe desc then profit_factor)
results_sorted = sorted([r for r in results if r.get("success")], key=lambda x: (x.get("sharpe") or -9999, x.get("profit_factor") or -9999), reverse=True)
fieldnames = list(results[0].keys()) if results else ["prob_threshold","hold","cooldown","fee","slip","success"]
with open(RESULT_CSV, "w", newline="") as csvf:
    writer = csv.DictWriter(csvf, fieldnames=fieldnames)
    writer.writeheader()
    for r in results:
        writer.writerow(r)

print("\nSweep complete. Results saved to:", RESULT_CSV)
print("Top successful combos (by Sharpe then profit_factor):")
for r in results_sorted[:10]:
    print(r)
