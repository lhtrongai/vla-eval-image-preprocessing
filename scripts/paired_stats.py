"""Paired statistics of every image-pipeline cell against its model's reference cell (LIBERO-Spatial, 500 pairs).

Pairs episodes by (task, initial state). Per cell: success with a 95% Wilson interval; paired difference to the
reference with a 95% bootstrap interval over paired episodes; episodes lost and gained; exact two-sided McNemar test;
Holm adjustment over the seven secondary comparisons; one-sided 95% upper bound on the loss; flips per task.
Usage: python scripts/paired_stats.py [results_dir]
"""
import glob
import json
import math
import os
import re
import sys

import numpy as np

RESULTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "results")
SECONDARY = ["openvla7b_spatial_crop_off", "openvla7b_spatial_bilinear", "openvla7b_spatial_render224",
             "oft_spatial_jpeg_off", "oft_spatial_crop_off", "oft_spatial_bilinear", "oft_spatial_render224"]


def wilson(k, n, z=1.96):
    p, d = k / n, 1 + z * z / n
    c, h = (p + z * z / (2 * n)) / d, z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return 100 * (c - h), 100 * (c + h)


def mcnemar(b, c):
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


def from_episodes(path):
    out = {}
    for r in map(json.loads, open(path)):
        out[(r["task_id"], r.get("initial_state", r["episode_idx"]))] = int(r["success"])
    return out


def from_oft_logs(folder):
    """Reference OFT cell: the original evaluation script's logs for initial states 0-19 and 20-49."""
    out = {}
    for seg, start, per_task in (("states_0-19", 0, 20), ("states_20-49", 20, 30)):
        txt = open(glob.glob(os.path.join(folder, seg, "EVAL-*.txt"))[0]).read()
        succ = [s == "True" for s in re.findall(r"Success: (True|False)", txt)]
        assert len(succ) == 10 * per_task, (seg, len(succ))
        for k, s in enumerate(succ):
            out[(k // per_task, start + k % per_task)] = int(s)
    return out


def vector(d):
    keys = [(t, i) for t in range(10) for i in range(50)]
    assert set(d) == set(keys), "every cell must hold the 500 (task, initial state) pairs"
    return np.array([d[k] for k in keys])


refs = {"openvla7b": vector(from_episodes(os.path.join(RESULTS, "openvla7b_spatial_reference", "episodes.jsonl"))),
        "oft": vector(from_oft_logs(os.path.join(RESULTS, "oft_spatial_reference")))}
rng = np.random.default_rng(20261029)
rows = []
for model, ref in refs.items():
    k = int(ref.sum()); lo, hi = wilson(k, 500)
    print(f"{model} reference: {k}/500 = {k / 5:.1f}% [{lo:.1f}, {hi:.1f}]")
for path in sorted(glob.glob(os.path.join(RESULTS, "*", "episodes.jsonl"))):
    cell = os.path.basename(os.path.dirname(path))
    if cell.endswith("_reference"):
        continue
    model = "openvla7b" if cell.startswith("openvla7b") else "oft"
    x, r = vector(from_episodes(path)), refs[model]
    lost, gained = int(((r == 1) & (x == 0)).sum()), int(((r == 0) & (x == 1)).sum())
    boot = (r - x)[rng.integers(0, 500, (20000, 500))].mean(1) * 100   # loss in points, per bootstrap draw
    k = int(x.sum()); lo, hi = wilson(k, 500)
    rows.append(dict(cell=cell, k=k, wilson=(lo, hi), diff=100 * (x.mean() - r.mean()),
                     ci=(-np.percentile(boot, 97.5), -np.percentile(boot, 2.5)), lost=lost, gained=gained,
                     p=mcnemar(lost, gained), ub_loss=np.percentile(boot, 95),
                     flips_per_task=[int((r[t * 50:(t + 1) * 50] != x[t * 50:(t + 1) * 50]).sum()) for t in range(10)]))
ps = sorted((row["p"], row["cell"]) for row in rows if row["cell"] in SECONDARY)
holm, run = {}, 0.0
for i, (p, cell) in enumerate(ps):
    run = max(run, min(1.0, (len(ps) - i) * p)); holm[cell] = run
print("\n| Cell | Success (Wilson 95%) | Difference, points (95% CI) | Lost / gained | McNemar p | Holm p | Upper bound on loss |")
print("|---|---|---|---|---|---|---|")
for row in rows:
    h = holm.get(row["cell"])
    print(f"| {row['cell']} | {row['k']}/500 = {row['k'] / 5:.1f}% [{row['wilson'][0]:.1f}, {row['wilson'][1]:.1f}] | "
          f"{row['diff']:+.1f} [{row['ci'][0]:+.1f}, {row['ci'][1]:+.1f}] | {row['lost']} / {row['gained']} | "
          f"{row['p']:.3g} | {'-' if h is None else f'{h:.3g}'} | {row['ub_loss']:.1f} |")
print("\nFlips per task:")
for row in rows:
    print(f"  {row['cell']}: {row['flips_per_task']}")
