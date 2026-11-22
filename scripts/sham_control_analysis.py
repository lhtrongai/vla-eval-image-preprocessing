"""Reading of the sham controls, the render-at-224 CPU control and the OpenVLA-OFT stack check (controls/PLAN.md).

This script is part of the plan and was committed with it, before any of these cells ran. It loads the cells of
October (results/<cell>/) and the control cells (results/controls/<cell>/), checks that every control cell is valid,
then prints the numbers and the readings that the plan fixes. The readings use no random draws; the bootstrap
interval of the ratio is descriptive only (fixed seed).

Usage: python scripts/sham_control_analysis.py [--results DIR] [--json OUT.json] [--budget-spent]
  --budget-spent  the GPU budget of the plan is used up: read each model with the valid sham cells it has (at least
                  two) instead of stopping when one is missing or invalid.
Exit code: 0 read; 1 a part could not be read (missing or invalid cells, listed); 2 the October numbers differ from
the plan (nothing is read).
"""
import argparse
import glob
import json
import math
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exact_bootstrap  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(REPO, "controls", "cells.json")))
KEYS = [(t, i) for t in range(10) for i in range(50)]
N = len(KEYS)
Z = 1.96
CUTOFF = 0.5                                   # share of the steps' flips above the rerun floor (PLAN.md, section 4)
PLAN_TOTALS = {"openvla7b": 123, "oft": 13}    # smallest total of the three sham cells' flips read as "many"
PLAN_STEPS = {"openvla7b": 78.5, "oft": 8.5}   # mean flips of the comparator steps (JPEG off, bilinear)
PLAN_FLOOR = {"openvla7b": 3, "oft": 0}        # flips of the identical rerun of October
COMPARATOR = ["jpeg_off", "bilinear"]
OCTOBER_VARIANTS = ["jpeg_off", "crop_off", "bilinear", "render224"]
SHAM_KINDS = ["sham_noise_seed1", "sham_noise_seed2", "sham_jpeg_q94"]
VERSIONS = {"torch": "2.8.0+cu128", "mujoco": "3.3.7", "robosuite": "1.4.1", "numpy": "1.26.4",
            "transformers": "4.40.1", "tensorflow": "2.16.2"}
MODELS = ("openvla7b", "oft")
NAME = {"openvla7b": "OpenVLA-7B", "oft": "OpenVLA-OFT"}
BOOT_SEED, BOOT_DRAWS = 20261122, 20000


# ------------------------------------------------------------------ loading
def load_rows(path):
    rows = {}
    for line in open(path):
        r = json.loads(line)
        rows[(r["task_id"], r.get("initial_state", r["episode_idx"]))] = r
    return rows


def load_oft_reference(folder):
    out = {}
    for seg, start, per_task in (("states_0-19", 0, 20), ("states_20-49", 20, 30)):
        txt = open(glob.glob(os.path.join(folder, seg, "EVAL-*.txt"))[0]).read()
        succ = [s == "True" for s in re.findall(r"Success: (True|False)", txt)]
        assert len(succ) == 10 * per_task, (seg, len(succ))
        for k, s in enumerate(succ):
            out[(k // per_task, start + k % per_task)] = {"success": s}
    return out


def success(rows):
    return np.array([int(rows[k]["success"]) for k in KEYS])


def steps(rows):
    return np.array([rows[k].get("env_steps") or -1 for k in KEYS])


def plan_sha256():
    out = {}
    for line in open(os.path.join(REPO, "controls", "code_sha256.txt")):
        if line.strip():
            digest, path = line.split()
            out[os.path.basename(path)] = digest
    return out


# ------------------------------------------------------------------ statistics
def mcnemar(b, c):
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


def compare(ref, x):
    lost, gained = int(((ref == 1) & (x == 0)).sum()), int(((ref == 0) & (x == 1)).sum())
    lo, hi, ub = exact_bootstrap.paired(ref, x)
    f = lost + gained
    band = 100 * Z * math.sqrt(f) / N
    diff = 100 * (gained - lost) / N
    return dict(k=int(x.sum()), lost=lost, gained=gained, flips=f, diff=diff, lo=lo, hi=hi, ub_loss=ub,
                p=mcnemar(lost, gained), band=band, inside_band=abs(diff) <= band + 1e-9,
                flips_per_task=[int((ref[t * 50:(t + 1) * 50] != x[t * 50:(t + 1) * 50]).sum()) for t in range(10)])


def ratio(sham_flips, steps_flips, floor):
    return (np.mean(sham_flips) - floor) / (np.mean(steps_flips) - floor)


def total_needed(k, steps_mean, floor):
    """Smallest total flips of k sham cells whose mean reaches CUTOFF of the steps' flips above the floor."""
    return math.ceil(k * (floor + CUTOFF * (steps_mean - floor)) - 1e-9)


def boot_ratio(ref, shams, steps_cells, rerun):
    """Percentile interval of the ratio over bootstrap resamples of the 500 paired episodes (descriptive)."""
    F = np.array([(x != ref) for x in shams + steps_cells + [rerun]], dtype=np.int32)
    rng = np.random.default_rng(BOOT_SEED)
    idx = rng.integers(0, N, size=(BOOT_DRAWS, N))
    counts = F[:, idx].sum(axis=2)                       # cells x draws
    s, st, fl = counts[:len(shams)].mean(0), counts[len(shams):-1].mean(0), counts[-1]
    den = st - fl
    r = np.where(den > 0, (s - fl) / np.where(den > 0, den, 1), np.nan)
    return float(np.nanpercentile(r, 2.5)), float(np.nanpercentile(r, 97.5)), int(np.isnan(r).sum())


# ------------------------------------------------------------------ validity of one control cell
POLICY_CAMERAS = {"openvla7b": ("agentview_image",), "oft": ("agentview_image", "robot0_eye_in_hand_image")}
MAX_FRAME_DIFFER = 5   # pairs whose first frame (cameras the policy uses) may differ from the October rerun


def frames_differ(rows, other, cams):
    return sum(any(rows[k]["frame_sha1"].get(c) != other[k]["frame_sha1"].get(c) for c in cams) for k in KEYS)


def expected_argv(seg, seg_dir):
    return [a.replace("{OUT}", seg_dir) for a in seg["argv"]]


def validate(cell, folder, october):
    """Problems that make a control cell invalid (empty list: valid), and notes that do not."""
    problems, notes = [], []
    path = os.path.join(folder, "episodes.jsonl")
    if not os.path.exists(path):
        return ["episodes.jsonl missing"], notes
    rows = load_rows(path)
    if set(rows) != set(KEYS):
        return [f"{len(rows)} pairs instead of the 500 (task, initial state) pairs"], notes
    model, variant = cell["model"], cell["env"].get("IMAGE_VARIANT", "")
    ref7 = october["openvla7b"]["reference_rows"]
    rerun = october[model]["rows"]["rerun"]
    if any(rows[k]["init_state_sha1"] != ref7[k]["init_state_sha1"] for k in KEYS):
        problems.append("initial-state hash differs from the LIBERO init file in some pairs")
    if any(rows[k]["fixtures"] != rerun[k]["fixtures"] for k in KEYS):
        problems.append("fixture placement differs from the October rerun in some pairs")
    cams = POLICY_CAMERAS[model]
    if cell["kind"] == "cpu_control":
        old = october[model]["rows"]["render224"]
        if any(rows[k]["fixtures"] != old[k]["fixtures"] for k in KEYS):
            problems.append("fixture placement differs from the repeated cell in some pairs")
        notes.append(f"first frame differs from the repeated cell in {frames_differ(rows, old, cams)} of 500 pairs")
    else:
        d = frames_differ(rows, rerun, cams)
        if d > MAX_FRAME_DIFFER:
            problems.append(f"first frame of the policy cameras differs from the October rerun in {d} pairs "
                            f"(at most {MAX_FRAME_DIFFER}): the stack renders differently, stop and compare the stacks")
        else:
            notes.append(f"first frame differs from the October rerun in {d} of 500 pairs")
    drivers = sorted({str(json.load(open(p)).get("gpu_driver")) for p in glob.glob(os.path.join(folder, "**", "run_meta.json"), recursive=True)})
    notes.append(f"GPU driver {', '.join(drivers)}")
    if model == "openvla7b" and any(rows[k].get("env_seed") != 0 for k in KEYS):
        problems.append("env_seed is not 0 in some episodes")
    # run metadata, one file per segment
    want_sha = plan_sha256()
    for seg in cell["segments"]:
        seg_dir = folder if seg["dir"] == "." else os.path.join(folder, seg["dir"])
        where = "run" if seg["dir"] == "." else seg["dir"]
        mp = os.path.join(seg_dir, "run_meta.json")
        if not os.path.exists(mp):
            problems.append(f"{where}: run_meta.json missing")
            continue
        m = json.load(open(mp))
        ipl = m.get("image_pipeline", {})
        if m.get("cpu") != CFG["required_cpu"]:
            problems.append(f"{where}: host CPU {m.get('cpu')!r}")
        if m.get("gpu") != CFG["required_gpu"]:
            problems.append(f"{where}: GPU {m.get('gpu')!r}")
        for k, v in VERSIONS.items():
            if (m.get("versions") or {}).get(k) != v:
                problems.append(f"{where}: {k} {(m.get('versions') or {}).get(k)} instead of {v}")
        want = {"image_variant": variant or "none", "jpeg_roundtrip": "on", "center_crop": "True",
                "jpeg_quality": 94 if variant == "jpeg_q94" else 95, "render_resolution": 224 if variant == "render224" else 256}
        if variant == "noise":
            want["noise_seed"] = int(cell["env"]["NOISE_SEED"])
        for k, v in want.items():
            if ipl.get(k) != v:
                problems.append(f"{where}: image_pipeline {k} = {ipl.get(k)!r}, the plan has {v!r}")
        argv, exp = m.get("argv", []), expected_argv(seg, "{OUT}")
        same = len(argv) == len(exp) and all(a == e or e == "{OUT}" for a, e in zip(argv, exp))
        if not same:
            problems.append(f"{where}: command {argv} is not the plan's {exp}")
        if model == "oft" and m.get("init_offset") != int(seg["env"]["INIT_OFFSET"]):
            problems.append(f"{where}: init_offset {m.get('init_offset')}")
        sha = m.get("code_sha256", {})
        for f in ("image_pipeline.py", CFG["runner"][model]):
            if sha.get(f) != want_sha.get(f):
                problems.append(f"{where}: {f} that ran is not the file of controls/code_sha256.txt")
        logs = glob.glob(os.path.join(seg_dir, "EVAL-*.txt")) + glob.glob(os.path.join(seg_dir, "experiments", "logs", "EVAL-*.txt"))
        if len(logs) != 1:
            problems.append(f"{where}: {len(logs)} evaluation logs instead of 1")
        else:
            txt = open(logs[0]).read()
            errors = len(re.findall(r"Caught exception|Episode error", txt))
            ends = len(re.findall(r"Success: (?:True|False)", txt))
            want_n = 500 if seg["dir"] == "." else 10 * int(seg["argv"][seg["argv"].index("--num_trials_per_task") + 1])
            if errors:
                problems.append(f"{where}: {errors} episodes ended with an exception in the evaluation log")
            if ends != want_n:
                problems.append(f"{where}: {ends} finished episodes in the evaluation log instead of {want_n}")
    if len(cell["segments"]) > 1:
        parts = []
        for seg in cell["segments"]:
            p = os.path.join(folder, seg["dir"], "episodes.jsonl")
            parts.append(open(p).read() if os.path.exists(p) else "")
        if open(path).read() != "".join(parts):
            problems.append("episodes.jsonl is not the segments in order")
    cj = os.path.join(folder, "cell.json")
    if not os.path.exists(cj):
        problems.append("cell.json missing")
    else:
        c = json.load(open(cj))
        if c.get("rc") != 0 or any(s.get("rc") != 0 for s in c.get("segments", [])):
            problems.append(f"exit code {c.get('rc')}")
    # the control itself was applied
    if variant == "noise":
        bad = 0
        for k in KEYS:
            r = rows[k]
            q = r["env_steps"] - 10
            want_calls = q if model == "openvla7b" else 2 * math.ceil(q / 8)
            first = r.get("noise_first_mad")
            first_ok = first == 1.0 if model == "openvla7b" else first == {"full_image": 1.0, "wrist_image": 1.0}
            bad += (r.get("noise_calls") != want_calls) or not first_ok
        if bad:
            problems.append(f"noise not applied to every processor input in {bad} episodes")
    if variant == "jpeg_q94":
        def changed(v):
            return v > 0 if isinstance(v, float) else (isinstance(v, dict) and len(v) == 2 and all(x > 0 for x in v.values()))
        bad = sum(not changed(rows[k].get("variant_input_mad") or 0.0) for k in KEYS)
        if bad:
            problems.append(f"JPEG quality 94 did not change the first input in {bad} episodes")
    return problems, notes


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=os.path.join(REPO, "results"))
    ap.add_argument("--json")
    ap.add_argument("--budget-spent", action="store_true")
    a = ap.parse_args()
    res = a.results
    out = {"cells": {}, "readings": {}}
    lines = []
    say = lines.append

    # October cells
    october = {}
    for m in MODELS:
        rows = {v: load_rows(os.path.join(res, f"{m}_spatial_{v}", "episodes.jsonl")) for v in ["rerun"] + OCTOBER_VARIANTS}
        ref_rows = (load_oft_reference(os.path.join(res, "oft_spatial_reference")) if m == "oft"
                    else load_rows(os.path.join(res, "openvla7b_spatial_reference", "episodes.jsonl")))
        october[m] = dict(rows=rows, ref=success(ref_rows), succ={v: success(r) for v, r in rows.items()})
        if m == "openvla7b":
            october[m]["reference_rows"] = ref_rows
    for m in MODELS:
        o = october[m]
        o["floor"] = int((o["succ"]["rerun"] != o["ref"]).sum())
        o["steps_flips"] = [int((o["succ"][v] != o["ref"]).sum()) for v in COMPARATOR]
        o["steps_mean"] = float(np.mean(o["steps_flips"]))
        M = np.vstack([o["ref"]] + [o["succ"][v] for v in OCTOBER_VARIANTS])
        o["pool"] = (M.min(0) != M.max(0))
        if (o["floor"], o["steps_mean"], total_needed(3, o["steps_mean"], o["floor"])) != \
                (PLAN_FLOOR[m], PLAN_STEPS[m], PLAN_TOTALS[m]):
            print(f"STOP: the October numbers of {m} differ from controls/PLAN.md "
                  f"(floor {o['floor']}, steps {o['steps_mean']}, total {total_needed(3, o['steps_mean'], o['floor'])})")
            return 2
    # fragile pool and step reference for the trajectory check (OFT: the rerun, whose outcomes equal the reference)
    step_ref = {"openvla7b": steps(october["openvla7b"]["reference_rows"]), "oft": steps(october["oft"]["rows"]["rerun"])}
    step_ref_succ = {"openvla7b": october["openvla7b"]["ref"], "oft": october["oft"]["succ"]["rerun"]}

    # control cells
    valid, succ, rows_of = {}, {}, {}
    say("# Sham controls, render-at-224 CPU control and OpenVLA-OFT stack check\n")
    say("Produced by `python scripts/sham_control_analysis.py` (pre-registered in `controls/PLAN.md`).\n")
    say("## Validity of every control cell\n")
    for cell in CFG["cells"]:
        folder = os.path.join(res, "controls", cell["name"])
        problems, notes = validate(cell, folder, october)
        valid[cell["name"]] = not problems
        out["cells"][cell["name"]] = {"valid": not problems, "problems": problems, "notes": notes}
        say(f"- `{cell['name']}`: {'valid' if not problems else 'INVALID'}" +
            ("" if not problems else ": " + "; ".join(problems)) + ("" if not notes else " (" + "; ".join(notes) + ")"))
        if not problems:
            rows_of[cell["name"]] = load_rows(os.path.join(folder, "episodes.jsonl"))
            succ[cell["name"]] = success(rows_of[cell["name"]])
    say("")
    rc = 0

    # sham reading
    say("## Sham control\n")
    say("Flips: pairs whose outcome differs from the model's October reference cell. Ratio: (mean flips of the sham "
        "cells - flips of the identical rerun) / (mean flips of JPEG off and bilinear - flips of the identical rerun). "
        f"Read as many flips when the ratio is at least {CUTOFF}.\n")
    for m in MODELS:
        o = october[m]
        names = [f"{m}_spatial_{s}" for s in SHAM_KINDS]
        have = [n for n in names if valid.get(n)]
        say(f"### {NAME[m]}\n")
        if len(have) < len(names) and not (a.budget_spent and len(have) >= 2):
            out["readings"][m] = {"read": False, "missing_or_invalid": [n for n in names if n not in have]}
            say(f"Not read: missing or invalid {', '.join(n for n in names if n not in have)}.\n")
            rc = 1
            continue
        say("| Cell | Success | Lost / gained | Flips | Difference, points (95% CI) | McNemar p | Band, points | Inside band | Flips vs October rerun | Flips in the fragile pool |")
        say("|---|---|---|---|---|---|---|---|---|---|")
        stats = {}
        for n in have:
            x = succ[n]
            s = compare(o["ref"], x)
            s["flips_vs_rerun"] = int((x != o["succ"]["rerun"]).sum())
            fl = (x != o["ref"])
            s["in_pool"] = int((fl & o["pool"]).sum())
            both = (step_ref_succ[m] == 1) & (x == 1)
            st = steps(rows_of[n])
            s["same_step_share"] = float((st[both] == step_ref[m][both]).mean()) if both.any() else float("nan")
            s["median_step_diff"] = float(np.median(np.abs(st[both] - step_ref[m][both]))) if both.any() else float("nan")
            stats[n] = s
            out["cells"][n].update(s)
            say(f"| `{n}` | {s['k']}/500 | {s['lost']} / {s['gained']} | {s['flips']} | {s['diff']:+.1f} "
                f"[{s['lo']:+.1f}, {s['hi']:+.1f}] | {s['p']:.3g} | ±{s['band']:.1f} | {'yes' if s['inside_band'] else 'no'} | "
                f"{s['flips_vs_rerun']} | {s['in_pool']} of {s['flips']} |")
        flips_list = [stats[n]["flips"] for n in have]
        total = sum(flips_list)
        need = total_needed(len(have), o["steps_mean"], o["floor"])
        r = ratio(flips_list, o["steps_flips"], o["floor"])
        lo, hi, undefined = boot_ratio(o["ref"], [succ[n] for n in have], [o["succ"][v] for v in COMPARATOR], o["succ"]["rerun"])
        reading = "many" if r >= CUTOFF else "few"
        # sensitivity rows (do not change the reading)
        r_with_render = ratio(flips_list, o["steps_flips"] + [int((o["succ"]["render224"] != o["ref"]).sum())], o["floor"])
        rr = o["succ"]["rerun"]
        r_vs_rerun = ratio([int((succ[n] != rr).sum()) for n in have],
                           [int((o["succ"][v] != rr).sum()) for v in COMPARATOR], o["floor"])
        pool_share = sum(stats[n]["in_pool"] for n in have) / max(total, 1)
        chance = float(o["pool"].mean())
        noise_pair = None
        if all(f"{m}_spatial_sham_noise_seed{k}" in have for k in (1, 2)):
            noise_pair = int((succ[f"{m}_spatial_sham_noise_seed1"] != succ[f"{m}_spatial_sham_noise_seed2"]).sum())
        out["readings"][m] = dict(
            read=True, cells=have, total_flips=total, total_needed=need, sham_mean=float(np.mean(flips_list)),
            steps_mean=o["steps_mean"], floor=o["floor"], ratio=float(r), ratio_ci=[lo, hi], ratio_undefined_draws=undefined,
            reading=reading, close_to_cutoff=bool(lo <= CUTOFF <= hi), ratio_with_render224=float(r_with_render),
            ratio_vs_october_rerun=float(r_vs_rerun), share_in_pool=pool_share, pool_share_of_episodes=chance,
            same_pool=bool(pool_share >= 2 * chance), band_supported=all(stats[n]["inside_band"] for n in have),
            noise1_vs_noise2_flips=noise_pair, fallback=len(have) < len(names))
        R = out["readings"][m]
        say(f"\nSham flips {', '.join(map(str, flips_list))} (total {total}; many from {need}); "
            f"steps {o['steps_flips']} (JPEG off, bilinear), rerun floor {o['floor']}. Ratio {r:.2f} "
            f"(bootstrap 95% interval {lo:.2f} to {hi:.2f}, descriptive): **{reading} flips**"
            + (" (close to the cutoff: the interval contains it)" if R["close_to_cutoff"] else "") + ". "
            f"With render-at-224 in the comparator {r_with_render:.2f}; against the October rerun as reference "
            f"{r_vs_rerun:.2f}. Sham flips in the fragile pool of October: {100 * pool_share:.0f}% "
            f"(the pool holds {100 * chance:.0f}% of the episodes; same pool: {'yes' if R['same_pool'] else 'no'}). "
            f"Every sham cell inside its band: {'yes' if R['band_supported'] else 'no'}."
            + ("" if noise_pair is None else f" Noise draw 1 against draw 2: {noise_pair} flips.")
            + (" Read with the valid cells only (budget spent)." if R["fallback"] else ""))
        say("\nSame success step as the step reference among episodes that succeed in both: " + ", ".join(
            f"{n.split('_spatial_')[1]} {100 * stats[n]['same_step_share']:.0f}% (median difference "
            f"{stats[n]['median_step_diff']:.0f})" for n in have))
        say("\nFlips per task: " + "; ".join(f"{n.split('_spatial_')[1]} {stats[n]['flips_per_task']}" for n in have))
        say("")
    r7, ro = out["readings"].get("openvla7b", {}), out["readings"].get("oft", {})
    if r7.get("read"):
        branch = "fragility" if r7["reading"] == "many" else "step-specific"
        out["readings"]["writing_branch"] = branch
        agree = ro.get("read") and ro["reading"] == r7["reading"]
        out["readings"]["oft_agrees"] = bool(agree) if ro.get("read") else None
        say(f"\n**Writing branch (set by OpenVLA-7B): {branch}.** OpenVLA-OFT reading: "
            f"{ro['reading'] + ' flips, ' + ('the same' if agree else 'different') if ro.get('read') else 'not read'}.")

    # CPU control
    say("\n## Render-at-224 CPU control (OpenVLA-7B)\n")
    n = "openvla7b_spatial_render224_cpu_control"
    if valid.get(n):
        o, x, old = october["openvla7b"], succ[n], october["openvla7b"]["succ"]["render224"]
        d = int((x != old).sum())
        reading = "a" if d <= o["floor"] else "b"
        s = compare(o["ref"], x)
        so = compare(o["ref"], old)
        st_new, st_old = steps(rows_of[n]), steps(o["rows"]["render224"])
        out["readings"]["cpu_control"] = dict(differ=d, floor=o["floor"], reading=reading, new=s, old=so,
                                              env_steps_differ=int((st_new != st_old).sum()))
        say(f"Outcomes differ from the cell of 29 October (EPYC 7443) in {d} of 500 pairs (rule: at most the "
            f"OpenVLA-7B rerun floor, {o['floor']}). **Reading ({reading})**: "
            + ("keep the October cell; report this run as a CPU check; drop the CPU caveat of this cell."
               if reading == "a" else "report both runs; the OpenVLA-7B render-at-224 result depends on the host "
                                      "(CPU type, and GPU driver where it differs).")
            + f" Against the reference: this run {s['k']}/500, lost {s['lost']}, gained {s['gained']}, {s['flips']} flips "
            f"(October cell {so['k']}/500, {so['lost']} / {so['gained']}, {so['flips']} flips). Success step differs in "
            f"{out['readings']['cpu_control']['env_steps_differ']} of 500 pairs.")
    else:
        say("Not read: the cell is missing or invalid.")
        rc = 1

    # OFT stack check
    say("\n## OpenVLA-OFT stack check\n")
    n = "oft_spatial_rerun_stack_check"
    if valid.get(n):
        o, x = october["oft"], succ[n]
        d_ref, d_rerun = int((x != o["ref"]).sum()), int((x != o["succ"]["rerun"]).sum())
        st = steps(rows_of[n])
        same_steps = int((st == steps(o["rows"]["rerun"])).sum())
        reading = "a" if d_ref == 0 else "b"
        out["readings"]["stack_check"] = dict(differ_reference=d_ref, differ_rerun=d_rerun, reading=reading,
                                              same_step_as_october_rerun=same_steps)
        say(f"Outcomes differ from the October reference in {d_ref} and from the October rerun in {d_rerun} of 500 "
            f"pairs; the success step equals the October rerun in {same_steps} of 500. **Reading ({reading})**: "
            + ("the cells of this run and of October share one stack." if reading == "a" else
               "the stack of this run differs from October; the OpenVLA-OFT sham flips are also reported against this cell."))
        if reading == "b" and out["readings"].get("oft", {}).get("read"):
            alt = [int((succ[c] != x).sum()) for c in out["readings"]["oft"]["cells"]]
            out["readings"]["oft"]["flips_vs_stack_check"] = alt
            say(f"OpenVLA-OFT sham flips against the stack check cell: {alt}.")
    else:
        say("Not read: the cell is missing or invalid.")
        rc = 1

    print("\n".join(lines))
    if a.json:
        with open(a.json, "w") as f:
            json.dump(out, f, indent=2, default=float)
    return rc


if __name__ == "__main__":
    sys.exit(main())
