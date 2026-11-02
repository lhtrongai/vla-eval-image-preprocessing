"""Compact JSON summary of the open-loop action check, for the paper tables.

Per model and mode: number of observations and episodes; per pipeline, the share of observations whose arm action
changes against the reference pipeline, the mean absolute change and the median per-observation maximum (in
OpenVLA-7B action bins; OFT: chunk mean, a change above half a bin counts); for OpenVLA-7B, how often a token is
changed by some variant depending on the reference top-1 minus top-2 logit margin; for first frames, the closed-loop
flip rate of episodes whose first action changed or did not; for trajectories, how many reference rollouts repeat the
closed-loop cell exactly.
Usage: python summarize_open_loop.py <open-loop out dir> <results dir> > summary.json
"""
import json
import os
import sys

import numpy as np

D, RES = sys.argv[1:3]
VARS = ["reference_again", "jpeg_off", "crop_off", "bilinear", "render224"]
KEYS = [(t, i) for t in range(10) for i in range(50)]


def cell(prefix, name):
    out = {}
    for r in map(json.loads, open(os.path.join(RES, f"{prefix}_spatial_{name}", "episodes.jsonl"))):
        out[(r["task_id"], r.get("initial_state", r["episode_idx"]))] = r
    return out


out = {}
for m in ("openvla7b", "oft"):
    ref_cell = "reference" if m == "openvla7b" else "rerun"  # the OFT rerun repeats the reference in all 500 pairs
    ref = cell(m, ref_cell)
    for mode in ("first", "traj"):
        f = os.path.join(D, f"actions_{m}_{mode}.jsonl")
        if not os.path.exists(f):
            continue
        rows = [json.loads(l) for l in open(f)]
        meta = json.load(open(os.path.join(D, f"meta_{m}_{mode}.json")))
        q01, q99 = np.array(meta["action_q01"]), np.array(meta["action_q99"])
        r_ = {"n": len(rows), "episodes": len({(r["task_id"], r["initial_state"]) for r in rows}),
              "same_fixtures": float(np.mean([r["same_fixtures_224"] for r in rows]))}
        changed = {}
        for v in VARS:
            if m == "openvla7b":
                a0 = np.array([r["pred"]["reference"]["tokens"] for r in rows])
                a1 = np.array([r["pred"][v]["tokens"] for r in rows])
                d = np.abs(a0 - a1).astype(float)
                ch = (d[:, :6] > 0).any(1)
            else:
                a0 = np.array([r["pred"]["reference"]["chunk"] for r in rows])
                a1 = np.array([r["pred"][v]["chunk"] for r in rows])
                d = (np.abs(a0 - a1) * (2.0 / (q99 - q01)) / (2.0 / 256)).mean(1)
                ch = (d[:, :6] > 0.5).any(1)
            changed[v] = ch
            r_[v] = {"changed": float(ch.mean()), "mean": float(d[:, :6].mean()),
                     "medmax": float(np.median(d[:, :6].max(1))), "gripper": float(d[:, 6].mean())}
        if m == "openvla7b":
            mg = np.array([r["pred"]["reference"]["margin"] for r in rows])[:, :6]
            tok0 = np.array([r["pred"]["reference"]["tokens"] for r in rows])[:, :6]
            anyc = np.zeros_like(mg, dtype=bool)
            for v in VARS[1:]:
                anyc |= np.array([r["pred"][v]["tokens"] for r in rows])[:, :6] != tok0
            r_["margin"] = {"low": float(anyc[mg < 2].mean()), "high": float(anyc[mg >= 8].mean()),
                            "low_share": float((mg < 2).mean()), "high_share": float((mg >= 8).mean())}
        if mode == "first":
            r_["flip_link"] = {}
            for v in VARS[1:]:
                var = cell(m, v)
                fv = np.array([int(ref[(r["task_id"], r["initial_state"])]["success"]) !=
                               int(var[(r["task_id"], r["initial_state"])]["success"]) for r in rows])
                c = changed[v]
                r_["flip_link"][v] = [float(fv[c].mean()) if c.any() else None,
                                      float(fv[~c].mean()) if (~c).any() else None, int(c.sum()), int((~c).sum())]
        if mode == "traj":
            ep = [json.loads(l) for l in open(os.path.join(D, f"episodes_{m}_{mode}.jsonl"))]
            same = sum((int(e["success"]), e["env_steps"]) == (int(ref[(e["task_id"], e["initial_state"])]["success"]),
                                                                ref[(e["task_id"], e["initial_state"])]["env_steps"])
                       for e in ep)
            r_["repro"] = [same, len(ep)]
        out[f"{m}/{mode}"] = r_
print(json.dumps(out, indent=1))
