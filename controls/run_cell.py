#!/usr/bin/env python3
"""Run the control cells of controls/cells.json on this pod (controls/RUN_GUIDE.md).

Before a cell starts: the host CPU and GPU must be the required ones, and the evaluation code in code_dir must be
byte-identical to controls/code_sha256.txt. Each cell runs its segments in order, one evaluation process at a time,
then writes OUT/episodes.jsonl (all segments, in order) and OUT/cell.json (what ran, exit codes, hardware). The
notification of a finished cell holds only its exit code and number of episodes. Successes are not shown anywhere
in this script, so that no result is read before every cell of the plan is done.

Usage (system python3 on the pod):
    python3 run_cell.py --pod <pod label> [--only <cell>]   run the cells of one pod in order (or one cell again,
                                                 as its next attempt); writes the pod's chain.log
    python3 run_cell.py --cell <name> [--attempt N] [--dry-run]
    python3 run_cell.py --image-check <pod label>  run check_image_variants.py for the models of the pod
    python3 run_cell.py --deadline-seconds <pod label>
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CFG = json.load(open(os.path.join(HERE, "cells.json")))
CELLS = {c["name"]: c for c in CFG["cells"]}
CLEARED = ("IMAGE_VARIANT", "NOISE_SEED", "JPEG_ROUNDTRIP", "INIT_OFFSET", "OUT_DIR", "CAMERA_TEXTURE_LOOKS")


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def cpu_model():
    with open("/proc/cpuinfo") as f:
        for line in f:
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    return "unknown"


def gpu_names():
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True,
                             text=True, check=False).stdout
    except FileNotFoundError:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def expected_sha256():
    """controls/code_sha256.txt: '<sha256>  <path in the repository>' per line."""
    out = {}
    with open(os.path.join(HERE, "code_sha256.txt")) as f:
        for line in f:
            if line.strip():
                digest, path = line.split()
                out[path] = digest
    return out


def code_problems():
    """Differences between the code that would run and controls/code_sha256.txt (empty list: identical)."""
    problems = []
    for path, digest in expected_sha256().items():
        if sha256(os.path.join(REPO, path)) != digest:
            problems.append(f"{path} in the repository differs from code_sha256.txt")
        if path.startswith("scripts/"):
            copy = os.path.join(CFG["code_dir"], os.path.basename(path))
            if not os.path.exists(copy) or sha256(copy) != digest:
                problems.append(f"{copy} is not the file of code_sha256.txt")
    return problems


def hardware_problems():
    problems = []
    if cpu_model() != CFG["required_cpu"]:
        problems.append(f"CPU is {cpu_model()!r}, the plan needs {CFG['required_cpu']!r}")
    gpus = gpu_names()
    if not gpus or any(g != CFG["required_gpu"] for g in gpus):
        problems.append(f"GPU is {gpus}, the plan needs {CFG['required_gpu']!r}")
    return problems


def notify(message):
    """ntfy message through the volume's notify.sh; never carries successes."""
    subprocess.run(["bash", "-c", 'source /workspace/notify.sh 2>/dev/null && notify "$1"', "_", message], check=False)


def cell_env(cell, segment, out_dir):
    env = {k: v for k, v in os.environ.items() if k not in CLEARED}
    env.update(CFG["env"])
    env.update(cell["env"])
    env.update(segment["env"])
    env["OUT_DIR"] = out_dir
    return env


def run_cell(name, attempt=1, dry_run=False, chain_log=None):
    cell = CELLS[name]
    out = os.path.join(CFG["out_root"], name if attempt == 1 else f"{name}__attempt{attempt}")
    problems = hardware_problems() + code_problems()
    if os.path.exists(out):
        problems.append(f"{out} exists; a new attempt needs --attempt {attempt + 1}")
    if problems and not dry_run:
        for p in problems:
            print("REFUSED:", p)
        notify(f"{name}: not started ({problems[0]})")
        return 2
    python = CFG["python"][cell["model"]]
    runner = os.path.join(CFG["code_dir"], CFG["runner"][cell["model"]])
    record = {"cell": name, "attempt": attempt, "out_dir": out, "config": cell, "cpu": cpu_model(), "gpu": gpu_names(),
              "pod_id": os.environ.get("RUNPOD_POD_ID"), "start": now(), "segments": [],
              "repo_commit": subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"], capture_output=True,
                                            text=True).stdout.strip(),
              "code_sha256": {p: sha256(os.path.join(REPO, p)) for p in expected_sha256()}}
    rc_all = 0
    for seg in cell["segments"]:
        seg_dir = out if seg["dir"] == "." else os.path.join(out, seg["dir"])
        argv = [python, runner] + [a.replace("{OUT}", seg_dir) for a in seg["argv"]]
        env = cell_env(cell, seg, seg_dir)
        shown = {k: env[k] for k in sorted(set(CFG["env"]) | set(cell["env"]) | set(seg["env"]) | {"OUT_DIR"})}
        if dry_run:
            print(f"[dry run] {name} / {seg['dir']}\n  env: {json.dumps(shown)}\n  cmd: {' '.join(argv)}")
            for p in problems:
                print("  would refuse:", p)
            continue
        os.makedirs(seg_dir, exist_ok=True)
        if chain_log:
            chain_log.write(f"{now()} start {name} {seg_dir}\n")
            chain_log.flush()
        t0 = now()
        with open(os.path.join(seg_dir, "run.log"), "w") as log:
            rc = subprocess.run(argv, env=env, cwd=seg_dir, stdout=log, stderr=subprocess.STDOUT).returncode
        record["segments"].append({"dir": seg["dir"], "argv": argv[1:], "env": shown, "rc": rc, "start": t0, "end": now()})
        rc_all = rc_all or rc
        if rc != 0:
            break
    if dry_run:
        return 0
    seg_files = [os.path.join(out if s["dir"] == "." else os.path.join(out, s["dir"]), "episodes.jsonl")
                 for s in cell["segments"]]
    if len(seg_files) > 1:  # OpenVLA-OFT: one file for the cell, segments in order, as for the October cells
        with open(os.path.join(out, "episodes.jsonl"), "w") as f:
            for p in seg_files:
                if os.path.exists(p):
                    f.write(open(p).read())
    n = sum(1 for _ in open(os.path.join(out, "episodes.jsonl"))) if os.path.exists(os.path.join(out, "episodes.jsonl")) else 0
    record.update(end=now(), rc=rc_all, episodes=n)
    with open(os.path.join(out, "cell.json"), "w") as f:
        json.dump(record, f, indent=2)
    if chain_log:
        chain_log.write(f"{now()} end {name} rc={rc_all} episodes={n}\n")
        chain_log.flush()
    notify(f"{name}: exit {rc_all}, {n} episodes")
    return 0 if (rc_all == 0 and n == 500) else 1


def pod_cells(label):
    return [c["name"] for c in CFG["cells"] if c["pod"] == label]


def run_pod(label, only=None):
    """Run the cells of a pod in order (or only one of them, as a new attempt); the watchdog reads chain.log."""
    log_dir = os.path.join(CFG["out_root"], "pods", label)
    os.makedirs(log_dir, exist_ok=True)
    names = [n for n in pod_cells(label) if only in (None, n)]
    assert names, f"no cell {only} on pod {label}"
    with open(os.path.join(log_dir, "chain.log"), "a") as chain_log:
        chain_log.write(f"{now()} chain start {label}: {' '.join(names)}\n")
        chain_log.flush()
        for name in names:
            attempt = 1
            while os.path.exists(os.path.join(CFG["out_root"], name if attempt == 1 else f"{name}__attempt{attempt}")):
                attempt += 1
            rc = run_cell(name, attempt, chain_log=chain_log)
            if rc == 2:  # refused: hardware or code is not the plan's; stop the chain, the watchdog removes the pod
                chain_log.write(f"{now()} refused {name}\n")
                break
        chain_log.write(f"{now()} chain finished\n")


def image_check(label):
    """check_image_variants.py for each model of the pod, with the cells' environment (no variant set)."""
    ok = True
    for model in sorted({CELLS[n]["model"] for n in pod_cells(label)}):
        env = {k: v for k, v in os.environ.items() if k not in CLEARED}
        env.update({k: CFG["env"][k] for k in ("PYTHONPATH", "LIBERO_CONFIG_PATH", "MUJOCO_GL",
                                               "TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "HF_HOME", "HF_HUB_ENABLE_HF_TRANSFER")})
        res = subprocess.run([CFG["python"][model], os.path.join(CFG["code_dir"], "check_image_variants.py"),
                              CFG["image_check"][model]], env=env, capture_output=True, text=True)
        print(res.stdout + res.stderr)
        ok = ok and res.returncode == 0 and "CHECK_OK" in res.stdout
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--pod")
    g.add_argument("--cell")
    g.add_argument("--image-check")
    g.add_argument("--deadline-seconds")
    ap.add_argument("--only", help="with --pod: run only this cell of the pod, as its next attempt")
    ap.add_argument("--attempt", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.pod:
        assert a.pod in CFG["pods"], f"unknown pod label {a.pod}"
        run_pod(a.pod, a.only)
    elif a.cell:
        sys.exit(run_cell(a.cell, a.attempt, a.dry_run))
    elif a.image_check:
        sys.exit(0 if image_check(a.image_check) else 1)
    else:
        print(int(CFG["pods"][a.deadline_seconds]["deadline_hours"] * 3600))
