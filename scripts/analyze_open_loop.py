"""Summarize the open-loop action check (open_loop_actions.py) against the reference pipeline.

Both models are compared in the same unit: action bins of OpenVLA-7B. OpenVLA-7B discretizes each normalized action
dimension (range q01..q99 mapped to [-1, 1]) into 256 bins, so a token difference is a bin difference. OpenVLA-OFT
predicts continuous actions; its difference is converted to the same unit, |a_n - a_n'| / (2 / 256).
Arm dimensions are the first 6; the gripper (7th) is reported separately.

Usage: python analyze_open_loop.py <dir with actions_*.jsonl> [<closed-loop results dir>]
With the results directory, first-frame changes are related to the closed-loop flips of the same (task, state).
"""
import glob
import json
import os
import sys

import numpy as np

D = sys.argv[1]
RES = sys.argv[2] if len(sys.argv) > 2 else None
VARS = ["reference_again", "jpeg_off", "crop_off", "bilinear", "render224"]


def load(path):
    return [json.loads(l) for l in open(path)]


def closed_loop_flips(model, var):
    if RES is None or var == "reference_again":
        return None
    prefix = "openvla7b" if model == "openvla7b" else "oft"

    def succ(cell):
        out = {}
        for r in map(json.loads, open(os.path.join(RES, f"{prefix}_spatial_{cell}", "episodes.jsonl"))):
            out[(r["task_id"], r.get("initial_state", r["episode_idx"]))] = int(r["success"])
        return out

    ref = succ("rerun" if prefix == "oft" else "reference")  # the OFT rerun repeats the reference in all 500 pairs
    v = succ(var)
    return {k: ref[k] != v[k] for k in ref}


for path in sorted(glob.glob(os.path.join(D, "actions_*.jsonl"))):
    model, mode = os.path.basename(path)[len("actions_"):-len(".jsonl")].split("_")
    rows = load(path)
    meta = json.load(open(os.path.join(D, f"meta_{model}_{mode}.json")))
    q01, q99 = np.array(meta["action_q01"]), np.array(meta["action_q99"])
    print(f"\n===== {model}, {mode}: {len(rows)} observations, "
          f"{len({(r['task_id'], r['initial_state']) for r in rows})} episodes, "
          f"fixtures of the 224 env identical in {np.mean([r['same_fixtures_224'] for r in rows]):.0%}")
    for var in VARS:
        if model == "openvla7b":
            ref = np.array([r["pred"]["reference"]["tokens"] for r in rows])
            x = np.array([r["pred"][var]["tokens"] for r in rows])
            dbin = np.abs(ref - x).astype(float)
        else:
            ref = np.array([r["pred"]["reference"]["chunk"] for r in rows])  # (n, 8, 7)
            x = np.array([r["pred"][var]["chunk"] for r in rows])
            scale = 2.0 / (q99 - q01)
            dbin = np.abs(ref - x) * scale / (2.0 / 256)  # (n, 8, 7)
            dbin = dbin.mean(axis=1)  # mean over the chunk: (n, 7)
        arm = dbin[:, :6]
        changed = (arm > (0 if model == "openvla7b" else 0.5)).any(axis=1)
        line = (f"  {var:16s} any arm dim changed {changed.mean():6.1%} | mean |d| {arm.mean():5.2f} bins | "
                f"median of per-observation max {np.median(arm.max(axis=1)):5.1f} bins | "
                f"gripper |d| {dbin[:, 6].mean():5.2f}")
        if model == "openvla7b":
            line += f" | dims changed per obs {(arm > 0).sum(axis=1).mean():.2f}"
        print(line)
        flips = closed_loop_flips(model, var)
        if flips is not None and mode == "first":
            first = {(r["task_id"], r["initial_state"]): bool(c) for r, c in zip(rows, changed)}
            keys = [k for k in first if k in flips]
            f1 = np.array([flips[k] for k in keys]); c1 = np.array([first[k] for k in keys])
            if f1.any() and (~f1).any():
                print(f"      closed-loop flip rate: {f1[c1].mean() if c1.any() else float('nan'):.1%} where the first "
                      f"action changed (n={c1.sum()}), {f1[~c1].mean() if (~c1).any() else float('nan'):.1%} where "
                      f"it did not (n={(~c1).sum()})")
    if model == "openvla7b":
        m = np.array([r["pred"]["reference"]["margin"] for r in rows])[:, :6]
        any_change = np.zeros_like(m, dtype=bool)
        for var in VARS[1:]:
            any_change |= np.array([r["pred"][var]["tokens"] for r in rows])[:, :6] != \
                np.array([r["pred"]["reference"]["tokens"] for r in rows])[:, :6]
        print("  top-1 minus top-2 logit margin of the reference token, arm dims:")
        for lo, hi in [(0, 1), (1, 2), (2, 4), (4, 8), (8, 1e9)]:
            sel = (m >= lo) & (m < hi)
            if sel.any():
                print(f"      margin [{lo}, {hi if hi < 1e9 else 'inf'}): {sel.mean():5.1%} of dims, "
                      f"changed by some variant in {any_change[sel].mean():5.1%}")
    if mode == "traj":
        ep = os.path.join(D, f"episodes_{model}_{mode}.jsonl")
        if os.path.exists(ep) and RES:
            prefix = "openvla7b" if model == "openvla7b" else "oft"
            cell = "reference" if prefix == "openvla7b" else "rerun"
            cl = {(r["task_id"], r.get("initial_state", r["episode_idx"])): (int(r["success"]), r["env_steps"])
                  for r in map(json.loads, open(os.path.join(RES, f"{prefix}_spatial_{cell}", "episodes.jsonl")))}
            e = load(ep)
            same = sum((int(r["success"]), r["env_steps"]) == cl[(r["task_id"], r["initial_state"])] for r in e)
            print(f"  reference rollouts repeating the closed-loop {cell} cell (outcome and step): {same}/{len(e)}")
