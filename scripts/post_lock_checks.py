"""Exploratory checks made after the results were locked (not registered beforehand, no new runs).

Why does every image-pipeline change flip so many episodes, and how should the differences in results/summary.md be
read? Per model, the five pipelines are the reference cell and the four variant cells (jpeg_off, crop_off, bilinear,
render224); episodes are paired by (task, initial state).
1. Fragile episodes: how many succeed under all five pipelines, under none, or under some.
2. Flips between every pair of pipelines, overlap of the variants' flip sets against chance, exact McNemar test of
   every variant against every other variant.
3. Success on initial states 0-19 and 20-49 per pipeline, and each pipeline against the mean of the other four.
4. Step budget: reference success step of the episodes a variant loses; flips if the budget were cut shorter.
5. Trajectory divergence: among episodes that succeed in both, how often the variant succeeds at the very same step.
6. OpenVLA-OFT crop_off: lost and gained per task, the test without task 5, task 5 successes per pipeline.
7. Primary comparison with a task-stratified bootstrap, and the 95% band that a change with no systematic effect
   leaves on a 500-episode score given its number of flips.
The OFT reference cell has no per-episode step count (original script logs), so OFT step comparisons use the identical
rerun, whose outcomes match the reference in all 500 pairs.
Usage: python scripts/post_lock_checks.py [results_dir]
"""
import glob
import json
import math
import os
import re
import sys
from itertools import combinations

import numpy as np

RESULTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "results")
KEYS = [(t, i) for t in range(10) for i in range(50)]
VARIANTS = ["jpeg_off", "crop_off", "bilinear", "render224"]
BUDGET = 230  # env steps per episode: 220 policy steps plus 10 settle steps


def mcnemar(b, c):
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


def load_cell(cell):
    """Success and env steps per (task, initial state), in KEYS order."""
    rows = {}
    for r in map(json.loads, open(os.path.join(RESULTS, cell, "episodes.jsonl"))):
        rows[(r["task_id"], r.get("initial_state", r["episode_idx"]))] = r
    assert set(rows) == set(KEYS), f"{cell}: every cell must hold the 500 (task, initial state) pairs"
    return np.array([int(rows[k]["success"]) for k in KEYS]), np.array([rows[k]["env_steps"] for k in KEYS])


def load_oft_reference():
    """Reference OFT cell: success only, from the original evaluation script's logs for states 0-19 and 20-49."""
    out = {}
    for seg, start, per_task in (("states_0-19", 0, 20), ("states_20-49", 20, 30)):
        txt = open(glob.glob(os.path.join(RESULTS, "oft_spatial_reference", seg, "EVAL-*.txt"))[0]).read()
        succ = [s == "True" for s in re.findall(r"Success: (True|False)", txt)]
        assert len(succ) == 10 * per_task, (seg, len(succ))
        for k, s in enumerate(succ):
            out[(k // per_task, start + k % per_task)] = int(s)
    return np.array([out[k] for k in KEYS])


def per_task(mask):
    return [int(mask[t * 50:(t + 1) * 50].sum()) for t in range(10)]


success, steps = {}, {}
for model in ("openvla7b", "oft"):
    for name in ["reference", "rerun"] + VARIANTS:
        cell = f"{model}_spatial_{name}"
        if cell == "oft_spatial_reference":
            success[cell] = load_oft_reference()
        else:
            success[cell], steps[cell] = load_cell(cell)
assert (success["oft_spatial_rerun"] == success["oft_spatial_reference"]).all()
step_ref = {"openvla7b": "openvla7b_spatial_reference", "oft": "oft_spatial_rerun"}

for model in ("openvla7b", "oft"):
    ref = success[f"{model}_spatial_reference"]
    runs = {"reference": ref, **{v: success[f"{model}_spatial_{v}"] for v in VARIANTS}}
    M = np.vstack(list(runs.values()))
    print(f"\n========== {model}: reference {ref.sum()}/500")

    # 1. Fragile episodes
    count = M.sum(0)
    always, never = int((count == 5).sum()), int((count == 0).sum())
    print(f"1. Over the 5 pipelines: {always} episodes always succeed, {never} always fail, "
          f"{500 - always - never} change ({(500 - always - never) / 5:.0f}%); by number of successes 0..5: "
          f"{np.bincount(count, minlength=6).tolist()}")
    print(f"   changing episodes per task: {per_task((count > 0) & (count < 5))}")
    print(f"   reference failures that succeed in at least one variant: "
          f"{int(((ref == 0) & (M[1:].max(0) == 1)).sum())}/{int((ref == 0).sum())}")

    # 2. Flips between pipelines
    print("2. Flips between pipelines: " + ", ".join(f"{a} vs {b} {int((runs[a] != runs[b]).sum())}"
                                                  for a, b in combinations(runs, 2)))
    flips = {v: runs[v] != ref for v in VARIANTS}
    print("   flipped (against the reference) in both variants, observed vs chance: " + ", ".join(
        f"{a} & {b} {int((flips[a] & flips[b]).sum())} vs {flips[a].sum() * flips[b].sum() / 500:.1f}"
        for a, b in combinations(VARIANTS, 2)))
    for a, b in combinations(VARIANTS, 2):
        gained, lost = int(((runs[a] == 0) & (runs[b] == 1)).sum()), int(((runs[a] == 1) & (runs[b] == 0)).sum())
        print(f"   {b} vs {a}: gained {gained}, lost {lost}, McNemar p {mcnemar(gained, lost):.3f}")

    # 3. Initial-state halves
    first = np.array([i < 20 for _, i in KEYS])
    print("3. Successes on states 0-19: " + ", ".join(f"{n} {int(x[first].sum())}" for n, x in runs.items()))
    print("   Successes on states 20-49: " + ", ".join(f"{n} {int(x[~first].sum())}" for n, x in runs.items()))
    print("   Each pipeline minus the mean of the other four: " + ", ".join(
        f"{n} {M[j].sum() - np.delete(M, j, 0).sum(1).mean():+.1f}" for j, n in enumerate(runs)))

    # 4. Step budget and 5. trajectory divergence
    sr, tr = success[step_ref[model]], steps[step_ref[model]]
    print(f"4-5. Step reference {step_ref[model]}: success step median {np.median(tr[sr == 1]):.0f} "
          f"(IQR {np.percentile(tr[sr == 1], 25):.0f}-{np.percentile(tr[sr == 1], 75):.0f}) of {BUDGET} env steps")
    for v in VARIANTS:
        x, tx = success[f"{model}_spatial_{v}"], steps[f"{model}_spatial_{v}"]
        both, lost = (sr == 1) & (x == 1), (sr == 1) & (x == 0)
        diff = np.abs(tx[both] - tr[both])
        print(f"   {v}: lost episodes had succeeded at step {np.median(tr[lost]):.0f} (median) in the step reference; "
              f"among {both.sum()} episodes that succeed in both, same success step in {100 * (diff == 0).mean():.0f}%, "
              f"step difference median {np.median(diff):.0f}, mean {diff.mean():.1f}")
    if model == "openvla7b":
        for k in (120, 150, 180, BUDGET):
            r = (sr == 1) & (tr <= k)
            print(f"   budget cut at {k} env steps: reference {r.sum()} successes, flips " + ", ".join(
                f"{v} {int((r != ((success[f'{model}_spatial_{v}'] == 1) & (steps[f'{model}_spatial_{v}'] <= k))).sum())}"
                for v in VARIANTS))
        rr, trr = success["openvla7b_spatial_rerun"], steps["openvla7b_spatial_rerun"]
        both = (rr == 1) & (sr == 1)
        print(f"   identical rerun: {int((rr == sr).sum())}/500 outcomes and the same success step in "
              f"{int((trr[both] == tr[both]).sum())} of {both.sum()} episodes that succeed in both")

# 6. OpenVLA-OFT crop_off
ref, x = success["oft_spatial_reference"], success["oft_spatial_crop_off"]
print("\n========== 6. OpenVLA-OFT crop_off against the reference")
print("   lost / gained per task: " + ", ".join(
    f"{t}: {int(((ref == 1) & (x == 0))[t * 50:(t + 1) * 50].sum())}/{int(((ref == 0) & (x == 1))[t * 50:(t + 1) * 50].sum())}"
    for t in range(10)))
keep = np.array([t != 5 for t, _ in KEYS])
lost, gained = int(((ref == 1) & (x == 0) & keep).sum()), int(((ref == 0) & (x == 1) & keep).sum())
print(f"   without task 5: lost {lost}, gained {gained}, McNemar p {mcnemar(lost, gained):.3f}")
print("   task 5 successes: " + ", ".join(f"{n} {int(success[f'oft_spatial_{n}'][250:300].sum())}"
                                         for n in ["reference", "rerun"] + VARIANTS))

# 7. Primary comparison, task-stratified bootstrap; band of a change with no systematic effect
rng = np.random.default_rng(20261029)
r, x = success["openvla7b_spatial_reference"], success["openvla7b_spatial_jpeg_off"]
d = (r - x).reshape(10, 50)
idx = rng.integers(0, 50, (20000, 10, 50))
boot = np.take_along_axis(np.broadcast_to(d, (20000, 10, 50)), idx, 2).mean((1, 2)) * 100
print(f"\n========== 7. Primary comparison (JPEG off, OpenVLA-7B), bootstrap within tasks: difference "
      f"{-d.mean() * 100:+.1f} points, 95% CI [{-np.percentile(boot, 97.5):+.1f}, {-np.percentile(boot, 2.5):+.1f}], "
      f"one-sided upper bound on the loss {np.percentile(boot, 95):.1f}")
print("   With f episodes flipped and no systematic effect, the 500-episode score moves within "
      "+-1.96 * sqrt(f) / 500 (95%):")
for model in ("openvla7b", "oft"):
    ref = success[f"{model}_spatial_reference"]
    f = [int((success[f"{model}_spatial_{v}"] != ref).sum()) for v in VARIANTS]
    print(f"   {model}: flips {f}, band +-{', +-'.join(f'{196 * math.sqrt(n) / 500:.1f}' for n in f)} points")
