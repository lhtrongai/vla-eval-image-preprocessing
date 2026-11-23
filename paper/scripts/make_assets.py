"""Build every figure, table and in-text number of the final paper from the released result files.

Usage:
    python3 scripts/make_assets.py <results_repo> <paper_dir>

<results_repo>  clone of github.com/lhtrongai/vla-eval-image-preprocessing (the 12 cells of 500 paired episodes,
                scripts/paired_stats.py, scripts/post_lock_checks.py)
<paper_dir>     this folder; reads data/ (pilot cells, vla-eval per-episode export, MuJoCo-version runs),
                eda/frames.jsonl (image-level EDA, scripts/eda_frames.py) and example_frames/ (Fig. 1)
Writes figures/*.pdf and generated/*.tex. Every number in the text comes from generated/numbers.tex.
"""
import glob
import json
import math
import os
import re
import subprocess
import sys
from math import comb
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from PIL import Image  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from power import power  # noqa: E402

repo, paper = map(Path, sys.argv[1:3])
RES = repo / "results"
DATA = paper / "data"
(paper / "figures").mkdir(exist_ok=True)
(paper / "generated").mkdir(exist_ok=True)

for f in glob.glob("/usr/share/fonts/truetype/liberation/LiberationSerif-*.ttf"):
    font_manager.fontManager.addfont(f)  # TrueType, metric-compatible with Times; embeds as Type 42
plt.rcParams.update({"font.family": "Liberation Serif", "font.size": 8, "pdf.fonttype": 42,
                     "mathtext.fontset": "custom", "mathtext.rm": "Liberation Serif",
                     "mathtext.it": "Liberation Serif:italic", "axes.linewidth": 0.6,
                     "xtick.major.width": 0.6, "ytick.major.width": 0.6, "axes.spines.top": False,
                     "axes.spines.right": False})
BLUE, ORANGE, VERM, GREY, INK = "#0072B2", "#E69F00", "#D55E00", "#666666", "#222222"
COLW, TEXTW = 3.45, 7.16
KEYS = [(t, i) for t in range(10) for i in range(50)]
VARS = ["jpeg_off", "crop_off", "bilinear", "render224"]
VNAME = {"rerun": "Rerun (A/A)", "jpeg_off": "JPEG off", "crop_off": "Crop step off", "bilinear": "Bilinear resize",
         "render224": "Render at 224"}
MAC = {"rerun": "Rerun", "jpeg_off": "Jpeg", "crop_off": "Crop", "bilinear": "Bil", "render224": "Rend"}
MODELS = {"openvla7b": "Sev", "oft": "Oft"}
Z = 1.959963984540054


# ---------------------------------------------------------------- statistics
def wilson(k, n, z=1.96):
    p, d = k / n, 1 + z * z / n
    c, h = (p + z * z / (2 * n)) / d, z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return 100 * (c - h), 100 * (c + h)


def mcnemar(b, c):
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


def band(f, n=500):
    """95% band of the score change (points) that f discordant pairs leave with no systematic effect."""
    return 100 * Z * math.sqrt(f) / n


# ---------------------------------------------------------------- load the 12 cells
def load_cell(cell):
    rows = {}
    for r in map(json.loads, open(RES / cell / "episodes.jsonl")):
        rows[(r["task_id"], r.get("initial_state", r["episode_idx"]))] = r
    assert set(rows) == set(KEYS), cell
    return rows


def load_oft_reference():
    out = {}
    for seg, start, per in (("states_0-19", 0, 20), ("states_20-49", 20, 30)):
        txt = open(glob.glob(str(RES / "oft_spatial_reference" / seg / "EVAL-*.txt"))[0]).read()
        succ = [s == "True" for s in re.findall(r"Success: (True|False)", txt)]
        assert len(succ) == 10 * per
        for k, s in enumerate(succ):
            out[(k // per, start + k % per)] = {"success": s, "env_steps": None}
    return out


rows, succ = {}, {}
for m in MODELS:
    for v in ["reference", "rerun"] + VARS:
        cell = f"{m}_spatial_{v}"
        rows[cell] = load_oft_reference() if cell == "oft_spatial_reference" else load_cell(cell)
        succ[cell] = np.array([int(rows[cell][k]["success"]) for k in KEYS])


def flips_of(a, b):
    lost = int(((a == 1) & (b == 0)).sum()); gained = int(((a == 0) & (b == 1)).sum())
    return lost, gained


# ---------------------------------------------------------------- the released analysis (exact numbers)
out = subprocess.run([sys.executable, str(repo / "scripts/paired_stats.py"), str(RES)], capture_output=True,
                     text=True, check=True).stdout
pat = re.compile(r"\| (\S+) \| (\d+)/500 = ([\d.]+)% \[([\d.]+), ([\d.]+)\] \| ([+-][\d.]+) \[([+-][\d.]+), "
                 r"([+-][\d.]+)\] \| (\d+) / (\d+) \| ([\d.e-]+) \| ([\d.e-]+|-) \| ([\d.]+) \|")
stat = {}
for mt in pat.finditer(out):
    c = mt.group(1)
    stat[c] = dict(k=int(mt.group(2)), wlo=float(mt.group(4)), whi=float(mt.group(5)), diff=float(mt.group(6)),
                   lo=float(mt.group(7)), hi=float(mt.group(8)), lost=int(mt.group(9)), gained=int(mt.group(10)),
                   p=float(mt.group(11)), holm=None if mt.group(12) == "-" else float(mt.group(12)),
                   ub=float(mt.group(13)))
stat.pop("oft_spatial_crop_off_cpu_control", None)  # the CPU control is reported separately (CpuCtrl* macros), not as a variant
assert len(stat) == 10, out
for m in MODELS:
    ref = succ[f"{m}_spatial_reference"]
    for v in ["rerun"] + VARS:
        c = f"{m}_spatial_{v}"
        lost, gained = flips_of(ref, succ[c])
        assert (lost, gained, int(succ[c].sum())) == (stat[c]["lost"], stat[c]["gained"], stat[c]["k"]), c
        assert abs(mcnemar(lost, gained) - stat[c]["p"]) < 5e-3 * max(stat[c]["p"], 1e-3) + 1e-9, c
        stat[c]["flips"] = lost + gained
        stat[c]["band"] = band(lost + gained)
        r = ref.reshape(10, 50); x = succ[c].reshape(10, 50)
        stat[c]["lost_task"] = [int(((r[t] == 1) & (x[t] == 0)).sum()) for t in range(10)]
        stat[c]["gained_task"] = [int(((r[t] == 0) & (x[t] == 1)).sum()) for t in range(10)]
refk = {m: int(succ[f"{m}_spatial_reference"].sum()) for m in MODELS}
assert refk == {"openvla7b": 425, "oft": 495}
post = subprocess.run([sys.executable, str(repo / "scripts/post_lock_checks.py"), str(RES)], capture_output=True,
                      text=True, check=True).stdout


def grab(rx, cast=float, text=post):
    mt = re.search(rx, text)
    assert mt, rx
    return [cast(g) for g in mt.groups()]


# ---------------------------------------------------------------- exploratory checks (recomputed, cross-checked)
expl = {}
for m in MODELS:
    M = np.vstack([succ[f"{m}_spatial_reference"]] + [succ[f"{m}_spatial_{v}"] for v in VARS])
    s = M.sum(0)
    expl[m] = {"always": int((s == 5).sum()), "never": int((s == 0).sum()), "change": int(((s > 0) & (s < 5)).sum()),
               "change_task": [int(((s > 0) & (s < 5)).reshape(10, 50)[t].sum()) for t in range(10)],
               "ref_fail_rescued": int(((M[0] == 0) & (M[1:].sum(0) > 0)).sum()), "ref_fail": int((M[0] == 0).sum())}
    a, n, c = grab(rf"{m}: reference \d+/500\n1\. Over the 5 pipelines: (\d+) episodes always succeed, (\d+) always "
                   r"fail, (\d+) change", int)
    assert (a, n, c) == (expl[m]["always"], expl[m]["never"], expl[m]["change"])
    ref = succ[f"{m}_spatial_reference"]
    fl = {v: ref != succ[f"{m}_spatial_{v}"] for v in VARS}
    ov = []
    for i, v in enumerate(VARS):
        for w in VARS[i + 1:]:
            ov.append((int((fl[v] & fl[w]).sum()), fl[v].sum() * fl[w].sum() / 500))
    expl[m]["overlap"] = ov
    pvv = []
    for i, v in enumerate(VARS):
        for w in VARS[i + 1:]:
            l, g = flips_of(succ[f"{m}_spatial_{v}"], succ[f"{m}_spatial_{w}"])
            pvv.append((l + g, mcnemar(l, g)))
    expl[m]["pvv"] = pvv
    expl[m]["split"] = {v: (int(succ[f"{m}_spatial_{v}"].reshape(10, 50)[:, :20].sum()),
                            int(succ[f"{m}_spatial_{v}"].reshape(10, 50)[:, 20:].sum())) for v in ["reference"] + VARS}

# step-budget and trajectory numbers for OpenVLA-7B (the OFT reference cell has no per-episode steps)
steps = {v: np.array([rows[f"openvla7b_spatial_{v}"][k]["env_steps"] for k in KEYS]) for v in ["reference", "rerun"] + VARS}
ref7 = succ["openvla7b_spatial_reference"]
budget = {}
for B in (120, 150, 180, 230):
    rb = (ref7 == 1) & (steps["reference"] <= B)
    budget[B] = {v: int((rb != ((succ[f"openvla7b_spatial_{v}"] == 1) & (steps[v] <= B))).sum()) for v in VARS}
    budget[B]["ref"] = int(rb.sum())
assert budget[230] == {**{v: stat[f"openvla7b_spatial_{v}"]["flips"] for v in VARS}, "ref": 425}
assert grab(r"budget cut at 120 env steps: reference (\d+) successes, flips jpeg_off (\d+)", int) == \
    [budget[120]["ref"], budget[120]["jpeg_off"]]
same_step = {}
for v in VARS:
    both = (ref7 == 1) & (succ[f"openvla7b_spatial_{v}"] == 1)
    d = np.abs(steps["reference"][both] - steps[v][both])
    same_step[v] = (float((d == 0).mean()), float(np.median(d)), int(both.sum()))
bothrr = (ref7 == 1) & (succ["openvla7b_spatial_rerun"] == 1)
rerun_same_step = int((steps["reference"][bothrr] == steps["rerun"][bothrr]).sum()), int(bothrr.sum())
assert rerun_same_step == tuple(grab(r"same success step in (\d+) of (\d+) episodes that succeed in both", int))
succ_steps = steps["reference"][ref7 == 1]
fail_steps = sorted(set(steps["reference"][ref7 == 0].tolist()))
assert fail_steps == [230]
oft_same = [float(x) for x in re.findall(r"among \d+ episodes that succeed in both, same success step in (\d+)%",
                                          post.split("========== oft")[1])]
oft_med = [float(x) for x in re.findall(r"step difference median (\d+)", post.split("========== oft")[1])]
# OFT crop off without task 5
r, x = succ["oft_spatial_reference"].reshape(10, 50), succ["oft_spatial_crop_off"].reshape(10, 50)
keep = [t for t in range(10) if t != 5]
l5, g5 = flips_of(r[keep].ravel(), x[keep].ravel())
assert (l5, g5) == (6, 2)
task5 = {v: int(succ[f"oft_spatial_{v}"].reshape(10, 50)[5].sum()) for v in ["reference", "rerun"] + VARS}
lb, gb = flips_of(succ["oft_spatial_bilinear"], succ["oft_spatial_crop_off"])

# ---------------------------------------------------------------- ablations of the analysis (new, documented here)
# exact bootstrap percentiles (no random draws), the same computation as scripts/paired_stats.py
sys.path.insert(0, str(repo / "scripts"))
import exact_bootstrap  # noqa: E402

paired_ci, unpaired_ci = exact_bootstrap.paired, exact_bootstrap.unpaired


abl = {}
jr, jx = succ["openvla7b_spatial_reference"], succ["openvla7b_spatial_jpeg_off"]
abl["paired"] = paired_ci(jr, jx)
assert abs(abl["paired"][0] - stat["openvla7b_spatial_jpeg_off"]["lo"]) < 0.05
assert abs(abl["paired"][1] - stat["openvla7b_spatial_jpeg_off"]["hi"]) < 0.05
abl["unpaired"] = unpaired_ci(jr, jx)
s20 = np.array([i < 20 for _, i in KEYS])
abl["first200"] = (100 * (jx[s20].mean() - jr[s20].mean()),) + paired_ci(jr[s20], jx[s20]) + flips_of(jr[s20], jx[s20])
loo = []
for t in range(10):
    k = np.array([tt != t for tt, _ in KEYS])
    loo.append(100 * (jx[k].mean() - jr[k].mean()))
abl["loo"] = (min(loo), max(loo))
# pilot (200 episodes, 12 October) against the 500-pair cells on states 0-19
pilot = {}
for pc, fc in [("openvla_reference", "openvla7b_spatial_reference"), ("openvla_rerun", "openvla7b_spatial_rerun"),
               ("openvla_jpeg_off", "openvla7b_spatial_jpeg_off"), ("openvla_crop_off", "openvla7b_spatial_crop_off"),
               ("oft_reference", "oft_spatial_reference"), ("oft_rerun", "oft_spatial_rerun"),
               ("oft_jpeg_off", "oft_spatial_jpeg_off")]:
    pr = {(r["task_id"], r["episode_idx"]): int(r["success"]) for r in map(json.loads, open(DATA / "pilot_states_0-19" / pc / "episodes.jsonl"))}
    pilot[pc] = {"k": sum(pr.values()), "diff_vs_final": sum(pr[(t, i)] != int(rows[fc][(t, i)]["success"])
                                                             for t in range(10) for i in range(20))}
pj = {(r["task_id"], r["episode_idx"]): int(r["success"]) for r in map(json.loads, open(DATA / "pilot_states_0-19/openvla_jpeg_off/episodes.jsonl"))}
prf = {(r["task_id"], r["episode_idx"]): int(r["success"]) for r in map(json.loads, open(DATA / "pilot_states_0-19/openvla_reference/episodes.jsonl"))}
pilot_lost = sum(prf[k] and not pj[k] for k in prf); pilot_gained = sum((not prf[k]) and pj[k] for k in prf)
assert (pilot_lost, pilot_gained) == (14, 21)
pilot_disc = (pilot_lost + pilot_gained) / 200

# ---------------------------------------------------------------- power and the chance band
pow_pilot = power(500, pilot_disc, 0.03)
n80 = next(n for n in range(500, 4000, 50) if power(n, pilot_disc, 0.03) >= 0.80)
thr = next(d / 10000 for d in range(700, 300, -5) if power(500, d / 10000, 0.03) >= 0.80)
final_disc = stat["openvla7b_spatial_jpeg_off"]["flips"] / 500
pow_final = power(500, final_disc, 0.03)
f_pilot = pilot_disc * 500

# ---------------------------------------------------------------- vla-eval per-episode export, same 500 states
ve = json.load(open(DATA / "vla_eval_export/libero_spatial.json"))
names = {rows["openvla7b_spatial_jpeg_off"][k]["task_description"]: k[0] for k in KEYS}
theirs = {}
for t in ve["tasks"]:
    for e in t["episodes"]:
        theirs[(names[t["task"]], int(e["episode_id"]))] = int(e["metrics"]["success"])
assert set(theirs) == set(KEYS)
vev = np.array([theirs[k] for k in KEYS])
ve_lost, ve_gained = flips_of(ref7, vev)  # lost: ours succeeds, vla-eval fails
ve_cells = {v: sum(flips_of(succ[f"openvla7b_spatial_{v}"], vev)) for v in ["reference", "rerun"] + VARS}
ve_commit = open(DATA / "vla_eval_export/source_commit.txt").read().split()[1]

# ---------------------------------------------------------------- MuJoCo version sensitivity (motivation)
m313 = json.load(open(DATA / "mujoco_versions/openvla7b_mujoco_3.13_states_0-19.json"))
m337 = json.load(open(DATA / "mujoco_versions/openvla7b_mujoco_3.3.7_states_0-19.json"))
oft313 = open(glob.glob(str(DATA / "mujoco_versions/EVAL-*.txt"))[0]).read()
oft313_k = int(re.search(r"Total successes: (\d+)", oft313).group(1))
oft313_n = int(re.findall(r"# episodes completed so far: (\d+)", oft313)[-1])
assert m337["success"] == int(ref7.reshape(10, 50)[:, :20].sum())

# ---------------------------------------------------------------- image-level EDA (CPU frames)
eda = [json.loads(l) for l in open(paper / "eda/frames.jsonl")]
EDAKEYS = ["bilinear", "jpeg_off", "render224", "crop_off", "grayscale"] + [f"imagenetc_jpeg_s{s}" for s in range(1, 6)]
edas = {k: {q: float(np.mean([r[k][q] for r in eda])) for q in ("mad", "p99", "changed")} for k in EDAKEYS}
for k in EDAKEYS:
    edas[k]["min"] = min(r[k]["mad"] for r in eda); edas[k]["max"] = max(r[k]["mad"] for r in eda)
gpu_mad = np.array([rows["openvla7b_spatial_jpeg_off"][k]["jpeg_input_mad"] for k in KEYS])
gpu_bil = np.array([rows["openvla7b_spatial_bilinear"][k]["variant_input_mad"] for k in KEYS])
cpu_pre = np.array([r["jpeg_off_precrop"]["mad"] for r in eda])
gpu_same = np.array([rows["openvla7b_spatial_jpeg_off"][(r["task"], r["state"])]["jpeg_input_mad"] for r in eda])
frame = json.load(open(paper / "example_frames/stats.json"))["task0_state0"]
_on = np.asarray(Image.open(paper / "example_frames/task0_state0_input_jpeg_on.png"), dtype=np.int16)
_off = np.asarray(Image.open(paper / "example_frames/task0_state0_input_jpeg_off.png"), dtype=np.int16)
heat_mean = float(np.abs(_on - _off).mean())
assert abs(heat_mean - frame["mean_abs_diff"]) < 1e-9

# ---------------------------------------------------------------- run log
def meta(cell):
    out = []
    for f in sorted(glob.glob(str(RES / cell / "**" / "run_meta.json"), recursive=True)):
        mm = json.load(open(f)); out.append(mm)
    return out


runlog = []
for m in MODELS:
    for v in ["reference", "rerun"] + VARS:
        cell = f"{m}_spatial_{v}"
        if cell == "oft_spatial_reference":
            dates = sorted(re.search(r"(\d{4})_(\d{2})_(\d{2})", os.path.basename(f)).groups()
                           for f in glob.glob(str(RES / cell / "*" / "EVAL-*.txt")))
            runlog.append((m, v, [f"{d[2]}/{d[1]}" for d in dates], None))
            continue
        ms = meta(cell)
        dates = sorted({mm["start_time"][8:10] + "/" + mm["start_time"][5:7] for mm in ms})
        hours = sum(r.get("wall_time_s", 0) for r in rows[cell].values()) / 3600
        cpus = sorted({mm.get("cpu") for mm in ms if mm.get("cpu")})
        runlog.append((m, v, dates, hours, cpus))
runlog = [r if len(r) == 5 else r + ([],) for r in runlog]


def short_cpu(c):
    return re.sub(r"\s+\d+-Core Processor", "", c).replace("AMD ", "")


cell_cpu = {(m, v): [short_cpu(c) for c in cp] for m, v, _, _, cp in runlog}
assert all(len(c) <= 1 for c in cell_cpu.values()), cell_cpu
oft_cpus = {v: cell_cpu[("oft", v)][0] for v in ["rerun"] + VARS}
assert [v for v in oft_cpus if oft_cpus[v] != oft_cpus["rerun"]] == ["crop_off"], oft_cpus
assert cell_cpu[("openvla7b", "reference")] == [] and cell_cpu[("oft", "reference")] == []

# ---------------------------------------------------------------- same scene in every pair (fixtures, first frames)
# The harness logs the placement of the cabinet and stove and a hash of the first frames of every episode. Across the
# harness cells of one model these must agree pair by pair (the render-at-224 frames differ by design).
scene = {}
for m in MODELS:
    hcells = [f"{m}_spatial_{v}" for v in ["rerun"] + VARS]
    base = rows[hcells[0]]
    fix_same = all(rows[c][k]["fixtures"] == base[k]["fixtures"] for c in hcells for k in KEYS)
    sha_cells = [c for c in hcells if not c.endswith("render224")]
    sha_same = all(rows[c][k]["frame_sha1"] == base[k]["frame_sha1"] for c in sha_cells for k in KEYS)
    rend_differs = all(rows[f"{m}_spatial_render224"][k]["frame_sha1"] != base[k]["frame_sha1"] for k in KEYS)
    scene[m] = dict(fix_same=fix_same, sha_same=sha_same, rend_differs=rend_differs, cells=len(hcells))
    assert fix_same and sha_same and rend_differs, (m, scene[m])
env_seeds = {rows[f"openvla7b_spatial_{v}"][k].get("env_seed") for v in ["rerun"] + VARS for k in KEYS}
assert len(env_seeds) == 1
oft_rend_mad = np.array([rows["oft_spatial_render224"][k]["jpeg_input_mad"]["full_image"] for k in KEYS])
assert oft_rend_mad.min() > 0  # the JPEG round trip is applied in the render-at-224 cell of OpenVLA-OFT
oft_rend_meta = [mm["image_pipeline"] for mm in meta("oft_spatial_render224")]
assert all(ip_["jpeg_roundtrip"] == "on" and ip_["render_resolution"] == 224 for ip_ in oft_rend_meta)

# ---------------------------------------------------------------- CPU control of the OpenVLA-OFT crop-off cell
# A rerun of the crop-off cell on the CPU type of the other OpenVLA-OFT cells goes to results/oft_spatial_crop_off_cpu_control
# (states_0-19 and states_20-49, as the other cells). Until it exists, CpuControlStatus is "pending".
CTRL = RES / "oft_spatial_crop_off_cpu_control"
cpu_ctrl = None
if CTRL.exists():
    rows["oft_spatial_crop_off_cpu_control"] = load_cell("oft_spatial_crop_off_cpu_control")
    cc = np.array([int(rows["oft_spatial_crop_off_cpu_control"][k]["success"]) for k in KEYS])
    l_c, g_c = flips_of(succ["oft_spatial_reference"], cc)
    cpu_ctrl = dict(k=int(cc.sum()), same=int((cc == succ["oft_spatial_crop_off"]).sum()), lost=l_c, gained=g_c,
                    p=mcnemar(l_c, g_c),
                    cpu=sorted({short_cpu(mm["cpu"]) for mm in meta("oft_spatial_crop_off_cpu_control")}))

# ---------------------------------------------------------------- checks added after the blind reviews (existing logs only)
# Primary comparison on the initial states outside the pilot (20-49): the pilot of 12 October already held the outcomes
# of states 0-19 of the primary cells, which the full cells repeat, so these 300 pairs are the part not seen before.
sB = ~s20
out_pilot = dict(diff=100 * (jx[sB].mean() - jr[sB].mean()), ci=paired_ci(jr[sB], jx[sB]), lg=flips_of(jr[sB], jx[sB]))
out_pilot["p"] = mcnemar(*out_pilot["lg"])
assert out_pilot["lg"][0] + abl["first200"][4] == stat["openvla7b_spatial_jpeg_off"]["lost"]
# Every OpenVLA-7B variant against the logged harness rerun (same harness, host CPU, fixtures and first frames
# checked) instead of the reference cell, which ran the original script and logs neither CPU nor fixtures.
rr7 = succ["openvla7b_spatial_rerun"]
vs_rerun = {}
for v in VARS:
    l_, g_ = flips_of(rr7, succ[f"openvla7b_spatial_{v}"])
    vs_rerun[v] = dict(lost=l_, gained=g_, flips=l_ + g_, diff=100 * (g_ - l_) / 500, p=mcnemar(l_, g_),
                       ci=paired_ci(rr7, succ[f"openvla7b_spatial_{v}"]))
# Chance overlap of flips, conditional on task and reference outcome: two variants can only lose among the same
# reference successes and gain among the same reference failures, so flips are expected to overlap within each
# (task, reference outcome) stratum even if they are otherwise independent.
for m in MODELS:
    ref = succ[f"{m}_spatial_reference"]
    fl = {v: ref != succ[f"{m}_spatial_{v}"] for v in VARS}
    strata = [(np.array([tt == t for tt, _ in KEYS]) & (ref == o)) for t in range(10) for o in (0, 1)]
    cond = []
    for i, v in enumerate(VARS):
        for w in VARS[i + 1:]:
            e = sum(fl[v][s].sum() * fl[w][s].sum() / s.sum() for s in strata if s.sum())
            cond.append((int((fl[v] & fl[w]).sum()), float(e)))
    expl[m]["overlap_cond"] = cond
assert [o for o, _ in expl["openvla7b"]["overlap_cond"]] == [o for o, _ in expl["openvla7b"]["overlap"]]


def cluster_boot(ref, x):
    """Exact bootstrap over the 10 tasks (clusters of 50 paired episodes): every composition of 10 draws over the
    10 tasks with its multinomial probability; returns (lo, hi, upper bound on the loss) in points."""
    d = [int(((ref.reshape(10, 50)[t] == 0) & (x.reshape(10, 50)[t] == 1)).sum()
             - ((ref.reshape(10, 50)[t] == 1) & (x.reshape(10, 50)[t] == 0)).sum()) for t in range(10)]
    acc = {}

    def rec(t, left, c):
        if t == 9:
            cc = c + [left]
            pr = math.factorial(10) / math.prod(math.factorial(k) for k in cc) / 10 ** 10
            val = sum(k * dd for k, dd in zip(cc, d))
            acc[val] = acc.get(val, 0.0) + pr
            return
        for k in range(left + 1):
            rec(t + 1, left - k, c + [k])
    rec(0, 10, [])
    vals = np.array(sorted(acc)); probs = np.array([acc[v] for v in vals])
    assert abs(probs.sum() - 1) < 1e-9
    return exact_bootstrap.summarize(vals, probs / probs.sum(), 500)


clus = {"sev_jpeg": cluster_boot(jr, jx), "oft_crop": cluster_boot(succ["oft_spatial_reference"], succ["oft_spatial_crop_off"])}
# Ceiling of OpenVLA-OFT: the variant can gain only among the reference failures, so G <= reference failures and the
# net change can be at most 2 x failures - f, whatever the variant does.
oft_ref_fail = int(500 - refk["oft"])


# First action and flip (open-loop check): difference of the two flip rates with the Newcombe hybrid score interval.
def wilson_p(k, n, z=1.96):
    p, d = k / n, 1 + z * z / n
    c, h = (p + z * z / (2 * n)) / d, z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def newcombe(k1, n1, k0, n0):
    p1, p0 = k1 / n1, k0 / n0
    l1, u1 = wilson_p(k1, n1); l0, u0 = wilson_p(k0, n0)
    d = p1 - p0
    return 100 * d, 100 * (d - math.sqrt((p1 - l1) ** 2 + (u0 - p0) ** 2)), 100 * (d + math.sqrt((u1 - p1) ** 2 + (p0 - l0) ** 2))


first_link = {}
_olsum = DATA / "open_loop" / "summary.json"
if _olsum.exists():
    _fl = json.load(open(_olsum))["openvla7b/first"]["flip_link"]
    for v in ("jpeg_off", "bilinear"):
        a_, b_, nc_, nn_ = _fl[v]
        k1, k0 = round(a_ * nc_), round(b_ * nn_)
        assert abs(k1 / nc_ - a_) < 1e-9 and abs(k0 / nn_ - b_) < 1e-9
        first_link[v] = newcombe(k1, nc_, k0, nn_)
# Unpaired range: two independent 500-episode cells at the rates of our reference and StableVLA (normal approximation)
_ps, _po = float(json.load(open(DATA / "external_numbers.json"))["StableClean"]["value"]) / 100, refk["openvla7b"] / 500
stable_unpaired = 100 * Z * math.sqrt(_ps * (1 - _ps) / 500 + _po * (1 - _po) / 500)

# ---------------------------------------------------------------- control cells of controls/PLAN.md (pending until run)
# The sham cells, the render-at-224 CPU control and the OpenVLA-OFT stack check go to results/controls/<cell>/, and
# their pre-registered reading, by scripts/sham_control_analysis.py, to results/controls/summary.json. Until that
# exists every control macro holds a placeholder and only sections/controls_results.tex (not included by main.tex
# until the results are in) uses them; generated/table_controls.tex is written only when the results exist.
CTRLD = RES / "controls"
ctrl = None
if (CTRLD / "summary.json").exists():
    ctrl = json.load(open(CTRLD / "summary.json"))
elif CTRLD.exists() and any(CTRLD.glob("*/episodes.jsonl")):
    _tmp = paper / "generated" / ".controls_reading.json"
    subprocess.run([sys.executable, str(repo / "scripts/sham_control_analysis.py"), "--results", str(RES),
                    "--json", str(_tmp)], capture_output=True, text=True)
    if _tmp.exists():
        ctrl = json.load(open(_tmp)); _tmp.unlink()
CONTROL_PLAN_COMMIT = "04fb502"  # commit that added controls/PLAN.md, pushed before any control cell ran
CONTROL_FIX_COMMIT = "e6ec1c2"  # the one correction before any cell started (GPU name check), PLAN.md "Changes after the plan commit"
try:
    _c = subprocess.run(["git", "-C", str(repo), "log", "--diff-filter=A", "--format=%h", "--", "controls/PLAN.md"],
                        capture_output=True, text=True).stdout.split()
    assert not _c or _c[-1][:7] == CONTROL_PLAN_COMMIT, _c
    _f = subprocess.run(["git", "-C", str(repo), "log", "--format=%h", "--", "controls/code_sha256.txt"],
                        capture_output=True, text=True).stdout.split()
    assert not _f or CONTROL_FIX_COMMIT in [h[:7] for h in _f], _f
except FileNotFoundError:
    pass

# ---------------------------------------------------------------- numbers quoted from other work
EXT = {k: v for k, v in json.load(open(DATA / "external_numbers.json")).items() if not k.startswith("_")}
m0 = meta("openvla7b_spatial_jpeg_off")[0]
mo = meta("oft_spatial_jpeg_off")[0]
pilot_meta = json.load(open(DATA / "pilot_states_0-19/openvla_reference/run_meta.json"))
gpu_hours = sum(r[3] for r in runlog if r[3])


# ---------------------------------------------------------------- numbers.tex
def f1(x):
    return f"{x:.1f}"


def sg(x, nd=1):
    s = f"{abs(x):.{nd}f}"
    if float(s) == 0:
        return "0" if nd == 0 else "0." + "0" * nd
    return ("+" if x > 0 else "$-$") + s


def pfmt(p):
    return f"{p:.3f}" if p < 0.1 else f"{p:.2f}"


N = {}
for m, mk in MODELS.items():
    k = refk[m]; lo, hi = wilson(k, 500)
    N[f"{mk}RefK"], N[f"{mk}RefPct"], N[f"{mk}RefLo"], N[f"{mk}RefHi"] = str(k), f1(k / 5), f1(lo), f1(hi)
    for v in ["rerun"] + VARS:
        s = stat[f"{m}_spatial_{v}"]; p = mk + MAC[v]
        N.update({p + "K": str(s["k"]), p + "Pct": f1(s["k"] / 5), p + "Diff": sg(s["diff"]), p + "Lo": sg(s["lo"]),
                  p + "Hi": sg(s["hi"]), p + "Lost": str(s["lost"]), p + "Gained": str(s["gained"]),
                  p + "Flips": str(s["flips"]), p + "P": pfmt(s["p"]), p + "UB": f1(s["ub"]),
                  p + "Band": f1(s["band"]), p + "FlipPct": f1(s["flips"] / 5)})
        if s["holm"] is not None:
            N[p + "Holm"] = pfmt(s["holm"])
sev_fl = [stat[f"openvla7b_spatial_{v}"]["flips"] for v in VARS]
oft_fl = [stat[f"oft_spatial_{v}"]["flips"] for v in VARS]
N.update({
    "SevFlipsMin": str(min(sev_fl)), "SevFlipsMax": str(max(sev_fl)), "OftFlipsMin": str(min(oft_fl)),
    "OftFlipsMax": str(max(oft_fl)), "SevBandMin": f1(band(min(sev_fl))), "SevBandMax": f1(band(max(sev_fl))),
    "OftBandMin": f1(band(min(oft_fl))), "OftBandMax": f1(band(max(oft_fl))),
    "SevFlipPctMin": f1(min(sev_fl) / 5), "SevFlipPctMax": f1(max(sev_fl) / 5),
    "SevVarMinPct": f1(min(stat[f"openvla7b_spatial_{v}"]["k"] for v in VARS) / 5),
    "SevVarMaxPct": f1(max(stat[f"openvla7b_spatial_{v}"]["k"] for v in VARS) / 5),
    "OftVarMinPct": f1(min(stat[f"oft_spatial_{v}"]["k"] for v in VARS) / 5),
    "OftVarMaxPct": f1(max(stat[f"oft_spatial_{v}"]["k"] for v in VARS) / 5),
    # pilot, rule and power
    "PilotLost": str(pilot_lost), "PilotGained": str(pilot_gained), "PilotFlips": str(pilot_lost + pilot_gained),
    "PilotDisc": f1(100 * pilot_disc), "PilotDiff": sg(100 * (pilot_gained - pilot_lost) / 200),
    "PowerPilot": str(round(100 * pow_pilot)), "PairsForEighty": f"{n80:,}", "DiscThreshold": f"{100 * thr:.2f}",
    "PowerFinal": str(round(100 * pow_final)), "FinalDisc": f1(100 * final_disc),
    "PilotF": f1(f_pilot), "PilotSD": f1(math.sqrt(f_pilot)), "PilotBandEp": f1(Z * math.sqrt(f_pilot)),
    "PilotTwoSD": f1(2 * math.sqrt(f_pilot)), "PilotBandPts": f1(band(f_pilot)),
    "FinalSD": f1(math.sqrt(stat["openvla7b_spatial_jpeg_off"]["flips"])),
    "FinalBandEp": f1(Z * math.sqrt(stat["openvla7b_spatial_jpeg_off"]["flips"])),
    "PilotMaxDiffVsFinal": str(max(p["diff_vs_final"] for p in pilot.values())),
    "PilotDate": pilot_meta["start_time"][8:10].lstrip("0") + " October",
    # exploratory
    "SevAlways": str(expl["openvla7b"]["always"]), "SevNever": str(expl["openvla7b"]["never"]),
    "SevChange": str(expl["openvla7b"]["change"]), "SevChangePct": str(round(expl["openvla7b"]["change"] / 5)),
    "SevRescued": str(expl["openvla7b"]["ref_fail_rescued"]), "SevRefFail": str(expl["openvla7b"]["ref_fail"]),
    "OftAlways": str(expl["oft"]["always"]), "OftNever": str(expl["oft"]["never"]), "OftChange": str(expl["oft"]["change"]),
    "OftChangeTaskFive": str(expl["oft"]["change_task"][5]),
    "SevOverlapMin": str(min(o for o, _ in expl["openvla7b"]["overlap"])),
    "SevOverlapMax": str(max(o for o, _ in expl["openvla7b"]["overlap"])),
    "SevChanceMin": f1(min(c for _, c in expl["openvla7b"]["overlap"])),
    "SevChanceMax": f1(max(c for _, c in expl["openvla7b"]["overlap"])),
    "SevOverlapRatioMin": f1(min(o / c for o, c in expl["openvla7b"]["overlap"])),
    "SevOverlapRatioMax": f1(max(o / c for o, c in expl["openvla7b"]["overlap"])),
    "SevVVpMin": f"{min(p for _, p in expl['openvla7b']['pvv']):.2f}",
    "SevVVfMin": str(min(f for f, _ in expl["openvla7b"]["pvv"])), "SevVVfMax": str(max(f for f, _ in expl["openvla7b"]["pvv"])),
    "SevSplitRefA": str(expl["openvla7b"]["split"]["reference"][0]), "SevSplitRefB": str(expl["openvla7b"]["split"]["reference"][1]),
    "SevSplitVarAMin": str(min(expl["openvla7b"]["split"][v][0] for v in VARS)),
    "SevSplitVarAMax": str(max(expl["openvla7b"]["split"][v][0] for v in VARS)),
    "SevSplitVarBMin": str(min(expl["openvla7b"]["split"][v][1] for v in VARS)),
    "SevSplitVarBMax": str(max(expl["openvla7b"]["split"][v][1] for v in VARS)),
    "SevSameStepMin": str(round(100 * min(s[0] for s in same_step.values()))),
    "SevSameStepMax": str(round(100 * max(s[0] for s in same_step.values()))),
    "SevStepDiffMin": f"{min(s[1] for s in same_step.values()):.0f}",
    "SevStepDiffMax": f"{max(s[1] for s in same_step.values()):.0f}",
    "OftSameStepMin": str(int(min(oft_same))), "OftSameStepMax": str(int(max(oft_same))),
    "OftStepDiffMin": str(int(min(oft_med))), "OftStepDiffMax": str(int(max(oft_med))),
    "RerunSameStep": str(rerun_same_step[0]), "RerunBoth": str(rerun_same_step[1]),
    "SuccStepMedian": str(int(np.median(succ_steps))), "SuccStepQone": str(int(np.percentile(succ_steps, 25))),
    "SuccStepQthree": str(int(np.percentile(succ_steps, 75))),
    "BudgetOneTwenty": str(budget[120]["jpeg_off"]), "BudgetOneFifty": str(budget[150]["jpeg_off"]),
    "BudgetOneEighty": str(budget[180]["jpeg_off"]),
    "BudgetRefOneTwenty": str(budget[120]["ref"]), "BudgetRefOneFifty": str(budget[150]["ref"]),
    "BudgetRefOneEighty": str(budget[180]["ref"]),
    "OftCropNoFiveLost": str(l5), "OftCropNoFiveGained": str(g5), "OftCropNoFiveP": f"{mcnemar(l5, g5):.2f}",
    "OftCropTaskFiveLost": str(stat["oft_spatial_crop_off"]["lost_task"][5]),
    "OftTaskFiveCrop": str(task5["crop_off"]),
    "OftTaskFiveOthersMin": str(min(task5[v] for v in ["reference", "rerun", "jpeg_off", "bilinear", "render224"])),
    "OftTaskFiveOthersMax": str(max(task5[v] for v in ["reference", "rerun", "jpeg_off", "bilinear", "render224"])),
    "OftCropVsBilLost": str(lb), "OftCropVsBilGained": str(gb), "OftCropVsBilP": pfmt(mcnemar(lb, gb)),
    # ablations
    "AblPairedLo": sg(abl["paired"][0]), "AblPairedHi": sg(abl["paired"][1]), "AblPairedUB": f1(abl["paired"][2]),
    "AblUnpairedLo": sg(abl["unpaired"][0]), "AblUnpairedHi": sg(abl["unpaired"][1]), "AblUnpairedUB": f1(abl["unpaired"][2]),
    "AblPairedW": f1(abl["paired"][1] - abl["paired"][0]), "AblUnpairedW": f1(abl["unpaired"][1] - abl["unpaired"][0]),
    "AblFirstDiff": sg(abl["first200"][0]), "AblFirstLo": sg(abl["first200"][1]), "AblFirstHi": sg(abl["first200"][2]),
    "AblFirstUB": f1(abl["first200"][3]), "AblFirstLost": str(abl["first200"][4]), "AblFirstGained": str(abl["first200"][5]),
    "AblFirstW": f1(abl["first200"][2] - abl["first200"][1]),
    "AblLooMin": sg(abl["loo"][0]), "AblLooMax": sg(abl["loo"][1]),
    # vla-eval
    "VeK": str(int(vev.sum())), "VePct": f1(vev.sum() / 5), "VeOnlyTheirs": str(ve_gained), "VeOnlyOurs": str(ve_lost),
    "VeFlips": str(ve_lost + ve_gained), "VeP": f"{mcnemar(ve_lost, ve_gained):.2f}", "VeBand": f1(band(ve_lost + ve_gained)),
    "VeGap": f1((vev.sum() - ref7.sum()) / 5), "VeCommit": ve_commit[:7],
    "VeCellsMin": str(min(ve_cells.values())), "VeCellsMax": str(max(ve_cells.values())),
    "VeFirstFlips": str(sum(theirs[(t, i)] != ref7.reshape(10, 50)[t, i] for t in range(10) for i in range(20))),
    # MuJoCo versions
    "MujocoOldK": str(m337["success"]), "MujocoNewK": str(m313["success"]),
    "MujocoOldTaskFive": str(m337["per_task_success"]["5"]), "MujocoNewTaskFive": str(m313["per_task_success"]["5"]),
    "OftNewTaskFive": f"{oft313_k}/{oft313_n}", "OftOldTaskFive": f"{int(succ['oft_spatial_reference'].reshape(10, 50)[5, :20].sum())}/20",
    # EDA
    "GpuMadMean": f"{gpu_mad.mean():.2f}", "GpuMadMin": f"{gpu_mad.min():.2f}", "GpuMadMax": f"{gpu_mad.max():.2f}",
    "GpuBilMean": f"{gpu_bil.mean():.2f}", "CpuPreMean": f"{cpu_pre.mean():.2f}", "GpuSameMean": f"{gpu_same.mean():.2f}",
    "EdaFrames": str(len(eda)), "EdaStates": str(len({r['state'] for r in eda})),
    "EdaJpeg": f"{edas['jpeg_off']['mad']:.2f}", "EdaBil": f"{edas['bilinear']['mad']:.2f}",
    "EdaRend": f"{edas['render224']['mad']:.2f}", "EdaCrop": f"{edas['crop_off']['mad']:.2f}",
    "EdaGray": f"{edas['grayscale']['mad']:.2f}", "EdaGrayRatio": f1(edas["grayscale"]["mad"] / edas["jpeg_off"]["mad"]),
    "EdaCthree": f"{edas['imagenetc_jpeg_s3']['mad']:.2f}", "EdaCone": f"{edas['imagenetc_jpeg_s1']['mad']:.2f}",
    "EdaCfive": f"{edas['imagenetc_jpeg_s5']['mad']:.2f}",
    "EdaCthreeRatio": f1(edas["imagenetc_jpeg_s3"]["mad"] / edas["jpeg_off"]["mad"]),
    "EdaJpegChanged": str(round(100 * edas["jpeg_off"]["changed"])),
    # setup and run log
    "GpuHours": str(round(gpu_hours)), "Episodes": f"{12 * 500:,}",
    "SideCrop": f"{math.sqrt(0.9):.3f}", "Zoom": f1(100 * (1 - math.sqrt(0.9))),
    "Border": f1((224 - 224 * math.sqrt(0.9)) / 2),
})
if frame:
    N["FramePixelsChanged"] = str(round(100 * frame["share_pixels_changed"])); N["FrameMaxDiff"] = str(frame["max_abs_diff"])
    N["FrameMeanDiff"] = f"{heat_mean:.2f}"

# ---------------------------------------------------------------- open-loop action check (data/open_loop)
OLV = ["reference_again", "jpeg_off", "crop_off", "bilinear", "render224"]
OLNAME = {"reference_again": "Same input again", "jpeg_off": "JPEG off", "crop_off": "Crop step off",
          "bilinear": "Bilinear resize", "render224": "Render at 224"}
ol = {}
_olf = DATA / "open_loop" / "summary.json"  # written by summarize_open_loop.py of the results repository
if _olf.exists():
    for k, v in json.load(open(_olf)).items():
        m_, mode_ = k.split("/")
        ol[(m_, mode_)] = v


def olmac(m, mode, v, q):
    return ("OlSev" if m == "openvla7b" else "OlOft") + ("First" if mode == "first" else "Traj") + MAC.get(v, "Again") + q


for (m, mode), r_ in ol.items():
    N[olmac(m, mode, "", "N").replace("Again", "")] = str(r_["n"])
    N[olmac(m, mode, "", "Episodes").replace("Again", "")] = str(r_["episodes"])
    for v in OLV:
        N[olmac(m, mode, v, "Changed")] = str(round(100 * r_[v]["changed"]))
        N[olmac(m, mode, v, "Mean")] = f"{r_[v]['mean']:.1f}"
        N[olmac(m, mode, v, "Medmax")] = f"{r_[v]['medmax']:.0f}" if m == "openvla7b" else f"{r_[v]['medmax']:.1f}"
    if "margin" in r_:
        pre = olmac(m, mode, "", "").replace("Again", "")
        N[pre + "MarginLow"] = str(round(100 * r_["margin"]["low"])); N[pre + "MarginHigh"] = str(round(100 * r_["margin"]["high"]))
        N[pre + "MarginLowShare"] = str(round(100 * r_["margin"]["low_share"])); N[pre + "MarginHighShare"] = str(round(100 * r_["margin"]["high_share"]))
    if "repro" in r_:
        pre = olmac(m, mode, "", "").replace("Again", "")
        N[pre + "Repro"] = str(r_["repro"][0]); N[pre + "ReproN"] = str(r_["repro"][1])
    if "flip_link" in r_:
        for v, (a, b, nc, nn) in r_["flip_link"].items():
            pre = olmac(m, mode, v, "")
            N[pre + "FlipIfChanged"] = "-" if a is None else str(round(100 * a)); N[pre + "FlipIfSame"] = "-" if b is None else str(round(100 * b))
            N[pre + "NChanged"] = str(nc)

if ol:
    def olrow(v):
        cells = []
        for m in MODELS:
            for mode in ("first", "traj"):
                r_ = ol.get((m, mode))
                cells.append("-" if r_ is None else f"{100 * r_[v]['changed']:.0f}\\% / {r_[v]['mean']:.1f}")
        return f"{OLNAME[v]} & " + " & ".join(cells) + r" \\"
    hdr = " & ".join(f"{ol[(m, mo)]['n'] if (m, mo) in ol else '-'}" for m in MODELS for mo in ("first", "traj"))
    ol_tab = r"""% Generated by scripts/make_assets.py from data/open_loop (scripts/open_loop_actions.py).
\begin{table}[t]
\caption{Open-loop action check: the same observation is given to the policy through each pipeline and the predicted action is compared with that of the reference pipeline. Each cell: share of observations whose arm action changes / mean absolute change of the six arm dimensions over all observations, in bins. OpenVLA-7B: difference in token index (a token spans 1/255 of the range between the 1st and 99th percentile of the training actions); any changed arm token counts. OpenVLA-OFT: absolute change averaged over the 8 actions of the chunk, in units of 1/256 of that range; a change above half a unit in any arm dimension counts. The two models' summaries are not directly comparable. First: the first observation of every initial state; along: observations along the reference rollout.}
\label{tab:openloop}
\centering
\footnotesize
\setlength{\tabcolsep}{2.5pt}
\begin{tabular}{@{}lcccc@{}}
\toprule
 & \multicolumn{2}{c}{OpenVLA-7B} & \multicolumn{2}{c}{OpenVLA-OFT} \\
\cmidrule(lr){2-3}\cmidrule(l){4-5}
Pipeline & First & Along & First & Along \\
Observations & """ + hdr + r""" \\
\midrule
""" + "\n".join(olrow(v) for v in OLV) + r"""
\bottomrule
\end{tabular}
\end{table}
"""
    (paper / "generated/table_openloop.tex").write_text(ol_tab)

# ---------------------------------------------------------------- design constants, dates, scene check, other work
# Constants fixed by the benchmark, the released code or the analysis plan. They are written as macros so that the
# text holds no hand-typed number (scripts/check_numbers.py enforces this).
from datetime import date  # noqa: E402

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]


def day_month(d):
    return f"{d.day} {MONTHS[d.month - 1]}"


def start_date(cell):
    st = sorted(mm["start_time"][:10] for mm in meta(cell))[0]
    return date.fromisoformat(st)


ref7_date, rerun7_date = start_date("openvla7b_spatial_reference"), start_date("openvla7b_spatial_rerun")
oft_ref_dates = sorted(date(*map(int, re.search(r"(\d{4})_(\d{2})_(\d{2})", os.path.basename(f)).groups()))
                       for f in glob.glob(str(RES / "oft_spatial_reference" / "*" / "EVAL-*.txt")))
all_dates = [start_date(f"{m}_spatial_{v}") for m in MODELS for v in ["rerun"] + VARS] + [ref7_date] + oft_ref_dates
oft_rerun_date = start_date("oft_spatial_rerun")
ol_dates = sorted({date.fromisoformat(x) for x in re.findall(r"(\d{4}-\d{2}-\d{2})", open(RES / "open_loop/chain.log").read())})
fail_limit = fail_steps[0]
settle = int(m0["argv"][m0["argv"].index("--num_steps_wait") + 1]) if "--num_steps_wait" in m0["argv"] else 10
DESIGN = {
    "NTasks": 10, "NStates": 50, "NPairs": len(KEYS), "NCells": 12, "NVariants": len(VARS), "NSecondary": 7,
    "RenderRes": 256, "InputRes": 224, "CropAreaPct": 90, "JpegQuality": 95, "DctBlock": 8,
    "SettleSteps": settle, "MaxSteps": fail_limit, "PolicySteps": fail_limit - settle,
    "Bins": 256, "TokenSpan": 255, "ShamJpegQuality": 94, "Chunk": 8, "SharedCells": "Four", "SharedEpisodes": "2,000", "ThresholdPts": 3, "ThresholdEp": 15, "Zval": "1.96",
    "AlphaPct": 95, "PowerTarget": 80, "PctLo": "1st", "PctHi": "99th", "MarginLow": 2, "MarginHigh": 8,
    "OlStride": "fourth", "OlSevStates": 5, "OlOftStates": 10, "PilotStates": 20, "PilotPairs": 200,
    "SplitA": "0-19", "SplitB": "20-49", "BudgetA": 180, "BudgetB": 150, "BudgetC": 120, "Seed": m0["seed"],
    "EnvSeed": env_seeds.pop(), "TaskFive": 5, "TaskFour": 4, "TaskNine": 9, "RotationDeg": 180,
    "MujocoNewVersion": "3.13.0", "MujocoVersion": m0["versions"]["mujoco"], "TotalEpisodes": f"{12 * 500:,}",
    "RuleDate": "6 October", "Year": 2026, "SevTokenDims": 6, "VarCompare": 6, "LooAnalyses": 10,
    "TaskMinSev": int(succ["openvla7b_spatial_reference"].reshape(10, 50).sum(1).min()),
    "TaskMaxSev": int(succ["openvla7b_spatial_reference"].reshape(10, 50).sum(1).max()),
    "TaskMinOft": int(succ["oft_spatial_reference"].reshape(10, 50).sum(1).min()),
    "TaskMaxOft": int(succ["oft_spatial_reference"].reshape(10, 50).sum(1).max()),
}
N.update({k: str(v) for k, v in DESIGN.items()})
N.update({
    "FirstRunDate": day_month(min(all_dates)), "LastRunDate": day_month(max(all_dates)),
    "SevRefDate": day_month(ref7_date), "SevRerunDate": day_month(rerun7_date),
    "RerunGapDays": str((rerun7_date - ref7_date).days), "OftRerunDate": day_month(oft_rerun_date),
    "OftRefDates": " and ".join(str(d.day) for d in oft_ref_dates) + " " + MONTHS[oft_ref_dates[0].month - 1],
    "OlDates": " and ".join(str(d.day) for d in ol_dates) + " " + MONTHS[ol_dates[0].month - 1],
    "OftRefVsPub": f1(refk["oft"] / 5 - float(EXT["OftSpatial"]["value"])),
    "SevRerunSame": str(500 - stat["openvla7b_spatial_rerun"]["flips"]),
    "OftRerunSame": str(500 - stat["oft_spatial_rerun"]["flips"]),
    "OftRendMadMin": f"{oft_rend_mad.min():.2f}", "OftRendMadMax": f"{oft_rend_mad.max():.2f}",
    "SceneCells": str(scene["openvla7b"]["cells"] + scene["oft"]["cells"]),
    "GpuName": m0["gpu"], "CpuMain": oft_cpus["rerun"], "CpuOftCrop": oft_cpus["crop_off"], "CpuSevRend": cell_cpu[("openvla7b", "render224")][0],
    "StableGapPts": f1(refk["openvla7b"] / 5 - float(EXT["StableClean"]["value"])),
    "CpuControlStatus": "pending" if cpu_ctrl is None else "done",
    "PilotCells": ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"][len(pilot)],
})
if cpu_ctrl is not None:
    N.update({"CpuCtrlK": str(cpu_ctrl["k"]), "CpuCtrlSame": str(cpu_ctrl["same"]),
              "CpuCtrlDiffer": str(500 - cpu_ctrl["same"]), "CpuCtrlLost": str(cpu_ctrl["lost"]),
              "CpuCtrlGained": str(cpu_ctrl["gained"]), "CpuCtrlP": pfmt(cpu_ctrl["p"]),
              "CpuCtrlCpu": ", ".join(cpu_ctrl["cpu"])})
# checks added after the blind reviews
_cs = [c for _, c in expl["openvla7b"]["overlap_cond"]]
_cr = [o / c for o, c in expl["openvla7b"]["overlap_cond"]]
N.update({
    "OutLost": str(out_pilot["lg"][0]), "OutGained": str(out_pilot["lg"][1]), "OutDiff": sg(out_pilot["diff"]),
    "OutLo": sg(out_pilot["ci"][0]), "OutHi": sg(out_pilot["ci"][1]), "OutUB": f1(out_pilot["ci"][2]),
    "OutP": pfmt(out_pilot["p"]), "OutPairs": str(int(sB.sum())),
    "VrJpegDiff": sg(vs_rerun["jpeg_off"]["diff"]), "VrJpegLo": sg(vs_rerun["jpeg_off"]["ci"][0]),
    "VrJpegHi": sg(vs_rerun["jpeg_off"]["ci"][1]), "VrJpegUB": f1(vs_rerun["jpeg_off"]["ci"][2]),
    "VrJpegLost": str(vs_rerun["jpeg_off"]["lost"]), "VrJpegGained": str(vs_rerun["jpeg_off"]["gained"]),
    "VrFlipsMin": str(min(r_["flips"] for r_ in vs_rerun.values())), "VrFlipsMax": str(max(r_["flips"] for r_ in vs_rerun.values())),
    "VrDiffMin": sg(min(r_["diff"] for r_ in vs_rerun.values())), "VrDiffMax": sg(max(r_["diff"] for r_ in vs_rerun.values())),
    "VrPMin": pfmt(min(r_["p"] for r_ in vs_rerun.values())),
    "SevCondChanceMin": f1(min(_cs)), "SevCondChanceMax": f1(max(_cs)),
    "SevCondRatioMin": f1(min(_cr)), "SevCondRatioMax": f1(max(_cr)),
    "ClusJpegLo": sg(clus["sev_jpeg"][0]), "ClusJpegHi": sg(clus["sev_jpeg"][1]), "ClusJpegUB": f1(clus["sev_jpeg"][2]),
    "ClusOftCropLo": sg(clus["oft_crop"][0]), "ClusOftCropHi": sg(clus["oft_crop"][1]),
    "OftRefFail": str(oft_ref_fail), "OftCropMaxD": sg(2 * oft_ref_fail - stat["oft_spatial_crop_off"]["flips"], 0),
    "OftRefFailTwice": str(2 * oft_ref_fail),
    "StableUnpaired": f1(stable_unpaired),
    "VariantFirstDate": day_month(min(start_date(f"{m}_spatial_{v}") for m in MODELS for v in ["rerun"] + VARS)),
    "VariantLastDate": day_month(max(start_date(f"{m}_spatial_{v}") for m in MODELS for v in ["rerun"] + VARS)),
    "VariantDates": (lambda ds: day_month(ds[0]) if len(ds) == 1 else f"{ds[0].day} and {day_month(ds[-1])}" if ds[0].month == ds[-1].month else f"{day_month(ds[0])} and {day_month(ds[-1])}")(
        sorted({start_date(f"{m}_spatial_{v}") for m in MODELS for v in ["rerun"] + VARS})),
    "RefDates": (lambda ds: ", ".join(ds[:-1]) + " and " + ds[-1])([str(d.day) for d in sorted(set(oft_ref_dates + [ref7_date]))]) + " " + MONTHS[ref7_date.month - 1],
    "MainEpisodes": f"{12 * 500:,}", "PilotEpisodes": f"{len(pilot) * 200:,}",
    "MujocoOldPct": f1(m337["sr"] * 100), "MujocoNewPct": f1(m313["sr"] * 100),
    "MujocoNewHours": f1(m313["hours"]), "ControlPlanCommit": CONTROL_PLAN_COMMIT, "ControlFixCommit": CONTROL_FIX_COMMIT,
})
if cpu_ctrl is not None:
    _cd = sorted({start_date("oft_spatial_crop_off_cpu_control")} | {date.fromisoformat(mm["start_time"][:10]) for mm in meta("oft_spatial_crop_off_cpu_control")})
    N["CpuCtrlDates"] = "-".join(str(d.day) for d in _cd) + " " + MONTHS[_cd[-1].month - 1]
for v, (d_, lo_, hi_) in first_link.items():
    p_ = "OlLink" + MAC[v]
    N.update({p_ + "Diff": sg(d_, 0), p_ + "Lo": sg(lo_, 0), p_ + "Hi": sg(hi_, 0)})


# control cells (sham, render-at-224 CPU control, OpenVLA-OFT stack check): placeholders until results/controls exists
def words_list(xs):
    xs = [str(x) for x in xs]
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


YN = lambda b: "Y" if b else "N"  # noqa: E731
SHAM = ["sham_noise_seed1", "sham_noise_seed2", "sham_jpeg_q94"]
SHAMMAC = {"sham_noise_seed1": "NoiseA", "sham_noise_seed2": "NoiseB", "sham_jpeg_q94": "Qnf"}
PH = "--"
N["ControlsStatus"] = "pending" if ctrl is None else "done"
N["ShamBranch"] = "X"
for m, mk in MODELS.items():
    pre = "Sham" + mk
    for key in ("FlipsList", "FlipsMin", "FlipsMax", "FlipPctMin", "FlipPctMax", "RatioPct", "RatioLo", "RatioHi",
                "Total", "Need", "PoolPct", "NoisePair", "Missing"):
        N[pre + key] = PH
    for key in ("Many", "Read", "Close", "OverOne", "BandOK", "SamePool", "Fallback"):
        N[pre + key] = "N"
    for s, sm in SHAMMAC.items():
        for key in ("K", "Lost", "Gained", "Flips", "Diff", "Lo", "Hi", "P", "Band"):
            N[pre + sm + key] = PH
N["ShamOftAgrees"] = "N"
for key in ("Differ", "K", "Lost", "Gained", "Flips", "P", "StepsDiffer", "FlipsMin", "FlipsMax"):
    N["CpuSevCtrl" + key] = PH
N["CpuSevCtrlReading"] = "x"
N["CpuSevCtrlAllSame"] = "N"; N["CpuSevCtrlStepsSame"] = "N"
N["CpuSevCtrlDriver"] = PH
N["StackReading"] = "x"; N["StackDiffer"] = PH; N["StackSameStep"] = PH
N["CpuSevOldDriver"] = meta("openvla7b_spatial_render224")[0]["gpu_driver"]
ctrl_cells = {}
if ctrl is not None:
    R_ = ctrl["readings"]
    for m, mk in MODELS.items():
        pre, rd = "Sham" + mk, R_.get(m, {})
        if not rd.get("read"):
            N[pre + "Missing"] = ", ".join(rd.get("missing_or_invalid", [])).replace("_", r"\_")
            continue
        cells_ = rd["cells"]
        fl_ = [ctrl["cells"][c]["flips"] for c in cells_]
        N.update({pre + "Read": "Y", pre + "Many": YN(rd["reading"] == "many"), pre + "FlipsList": words_list(fl_),
                  pre + "FlipsMin": str(min(fl_)), pre + "FlipsMax": str(max(fl_)),
                  pre + "FlipPctMin": f1(min(fl_) / 5), pre + "FlipPctMax": f1(max(fl_) / 5),
                  pre + "RatioPct": str(round(100 * rd["ratio"])), pre + "RatioLo": str(round(100 * rd["ratio_ci"][0])),
                  pre + "RatioHi": str(round(100 * rd["ratio_ci"][1])), pre + "Close": YN(rd["close_to_cutoff"]),
                  pre + "OverOne": YN(rd["ratio"] >= 1), pre + "BandOK": YN(rd["band_supported"]),
                  pre + "Total": str(rd["total_flips"]), pre + "Need": str(rd["total_needed"]),
                  pre + "PoolPct": str(round(100 * rd["share_in_pool"])), pre + "SamePool": YN(rd["same_pool"]),
                  pre + "NoisePair": PH if rd.get("noise1_vs_noise2_flips") is None else str(rd["noise1_vs_noise2_flips"]),
                  pre + "Fallback": YN(rd.get("fallback"))})
        if rd.get("fallback"):
            N[pre + "Missing"] = ", ".join(c for c in [f"{m}_spatial_{s}" for s in SHAM] if c not in cells_).replace("_", r"\_")
        for c in cells_:
            s_ = ctrl["cells"][c]; sm = SHAMMAC[c.split("_spatial_")[1]]
            ctrl_cells[c] = s_
            N.update({pre + sm + "K": str(s_["k"]), pre + sm + "Lost": str(s_["lost"]), pre + sm + "Gained": str(s_["gained"]),
                      pre + sm + "Flips": str(s_["flips"]), pre + sm + "Diff": sg(s_["diff"]), pre + sm + "Lo": sg(s_["lo"]),
                      pre + sm + "Hi": sg(s_["hi"]), pre + sm + "P": pfmt(s_["p"]), pre + sm + "Band": f1(s_["band"])})
    if "writing_branch" in R_:
        N["ShamBranch"] = "F" if R_["writing_branch"] == "fragility" else "S"  # F: fragility, S: step-specific
        N["ShamOftAgrees"] = YN(R_.get("oft_agrees"))
    cc_ = R_.get("cpu_control")
    if cc_:
        new_ = cc_["new"]
        both_ = [stat[f"openvla7b_spatial_{v}"]["flips"] for v in VARS] + [new_["flips"]]
        N.update({"CpuSevCtrlReading": cc_["reading"], "CpuSevCtrlDiffer": str(cc_["differ"]), "CpuSevCtrlK": str(new_["k"]),
                  "CpuSevCtrlLost": str(new_["lost"]), "CpuSevCtrlGained": str(new_["gained"]),
                  "CpuSevCtrlFlips": str(new_["flips"]), "CpuSevCtrlP": pfmt(new_["p"]),
                  "CpuSevCtrlStepsDiffer": str(cc_["env_steps_differ"]),
                  "CpuSevCtrlFlipsMin": str(min(both_)), "CpuSevCtrlFlipsMax": str(max(both_)),
                  "CpuSevCtrlAllSame": YN(cc_["differ"] == 0), "CpuSevCtrlStepsSame": YN(cc_["env_steps_differ"] == 0)})
        notes_ = " ".join(ctrl["cells"].get("openvla7b_spatial_render224_cpu_control", {}).get("notes", []))
        mt_ = re.search(r"GPU driver ([\d.]+(?:, [\d.]+)*)", notes_)
        if mt_:
            N["CpuSevCtrlDriver"] = mt_.group(1)
    sc_ = R_.get("stack_check")
    if sc_:
        N.update({"StackReading": sc_["reading"], "StackDiffer": str(sc_["differ_reference"]),
                  "StackSameStep": str(sc_["same_step_as_october_rerun"])})
for k, e in EXT.items():
    assert re.fullmatch(r"[A-Za-z]+", k), k
    N["Ext" + k] = e["value"]

with open(paper / "generated/numbers.tex", "w") as fh:
    fh.write("% Generated by scripts/make_assets.py from the released result files. Do not edit by hand.\n")
    for k, v in N.items():
        assert re.fullmatch(r"[A-Za-z]+", k), k
        fh.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")


# ---------------------------------------------------------------- Table: cells and run log
def dates_str(d):
    mon = {"09": "Sep", "10": "Oct", "11": "Nov"}
    return ", ".join(f"{int(x.split('/')[0])} {mon[x.split('/')[1]]}" for x in d)


lines = []
for m, v, d, h, cp in runlog:
    mname = "OpenVLA-7B" if m == "openvla7b" else "OpenVLA-OFT"
    what = {"reference": "original evaluation script, unchanged", "rerun": "reference repeated unchanged",
            "jpeg_off": "no JPEG round trip before the resize", "crop_off": "no center crop (script flag)",
            "bilinear": "bilinear instead of Lanczos3 resize", "render224": "cameras rendered at 224, not 256"}[v]
    lines.append(f"{mname if v == 'reference' else ''} & {VNAME.get(v, 'Reference')} & {what} & {dates_str(d)} & "
                 f"{'-' if h is None else f'{h:.1f}'} & {short_cpu(cp[0]) if cp else 'not logged'} \\\\")
    if m == "openvla7b" and v == "render224":
        lines.append(r"\midrule")
if cpu_ctrl is not None:
    _cm = meta("oft_spatial_crop_off_cpu_control")
    _ch = sum(r.get("wall_time_s", 0) for r in rows["oft_spatial_crop_off_cpu_control"].values()) / 3600
    lines.append(f" & CPU control & crop-off cell repeated on another host & {dates_str(sorted({mm['start_time'][8:10] + '/' + mm['start_time'][5:7] for mm in _cm}))} & "
                 f"{_ch:.1f} & {', '.join(cpu_ctrl['cpu'])} \\\\")
tab = r"""% Generated by scripts/make_assets.py from run_meta.json and the episode records of every cell.
\begin{table}[t]
\caption{The twelve cells of the study, the CPU control of the OpenVLA-OFT crop-off cell (Appendix~\ref{app:cpucontrol}) and their run log. Each cell runs the 500 (task, initial state) pairs of LIBERO-Spatial. Date: day of 2026 on which the cell started; hours: summed episode time on one GPU (not logged by the original OpenVLA-OFT script); host CPU as recorded in the run metadata (the two reference cells ran the original scripts, which do not record it). Every cell ran on one NVIDIA RTX PRO 4500 Blackwell GPU.}
\label{tab:cells}
\centering
\scriptsize
\setlength{\tabcolsep}{3pt}
\begin{tabular}{@{}llL{0.36\columnwidth}lrl@{}}
\toprule
Model & Cell & What changes & Date & Hours & Host CPU \\
\midrule
""" + "\n".join(lines) + r"""
\bottomrule
\end{tabular}
\end{table}
"""
(paper / "generated/table_cells.tex").write_text(tab)

# pilot cells (initial states 0-19), the run that preceded the full cells
PILOT_ROWS = [("OpenVLA-7B", "openvla_reference", "reference"), ("", "openvla_rerun", "rerun"),
              ("", "openvla_jpeg_off", "jpeg_off"), ("", "openvla_crop_off", "crop_off"),
              ("OpenVLA-OFT", "oft_reference", "reference"), ("", "oft_rerun", "rerun"), ("", "oft_jpeg_off", "jpeg_off")]
assert sorted(c for _, c, _ in PILOT_ROWS) == sorted(pilot)
plines = []
for mname, pc, v in PILOT_ROWS:
    pm = json.load(open(DATA / "pilot_states_0-19" / pc / "run_meta.json"))
    ip = pm["image_pipeline"]
    assert (ip["jpeg_roundtrip"] == "off") == (v == "jpeg_off") and (ip["center_crop"] == "False") == (v == "crop_off"), pc
    st = pm["start_time"]
    plines.append(f"{mname} & {VNAME.get(v, 'Reference')} & {int(st[8:10])} Oct {st[11:16]} & {pilot[pc]['k']} & "
                  f"{pilot[pc]['diff_vs_final']} & {short_cpu(pm['cpu'])} \\\\")
ptab = r"""% Generated by scripts/make_assets.py from data/pilot_states_0-19/*/run_meta.json and episodes.jsonl.
\begin{table}[t]
\caption{The pilot cells, run before the full variant cells on initial states 0-19 of every task (200 episodes per cell). Start: day and time (clock of the cloud instance) at which the cell started, from its run metadata. Successes: of 200. Differ: outcomes that differ from the full cell of the same pipeline on the same 200 pairs. The pilot included two variant steps; it fixed the share of flips used by the decision rule and is not pooled with the full cells.}
\label{tab:pilot}
\centering
\footnotesize
\begin{tabular}{@{}llllrl@{}}
\toprule
Model & Cell & Start & Successes & Differ & Host CPU \\
\midrule
""" + "\n".join(plines) + r"""
\bottomrule
\end{tabular}
\end{table}
"""
(paper / "generated/table_pilot.tex").write_text(ptab)

v = m0["versions"]
setup = rf"""% Generated by scripts/make_assets.py from run_meta.json of the cells.
\begin{{table}}[t]
\caption{{Evaluation setup, read from the run metadata that every cell records.}}
\label{{tab:setup}}
\centering
\footnotesize
\begin{{tabular}}{{@{{}}L{{0.22\columnwidth}}L{{0.71\columnwidth}}@{{}}}}
\toprule
Item & Value \\
\midrule
Checkpoints & \path{{{m0['checkpoint']}}}; \path{{{mo['checkpoint']}}} \\
Episodes & LIBERO-Spatial, 10 tasks $\times$ 50 stored initial states = 500 per cell; 10 settle steps + at most 220 policy steps \\
Simulator & MuJoCo {v['mujoco']}, robosuite {v['robosuite']}, headless offscreen rendering ({m0['mujoco_gl'].upper()}) \\
Libraries & PyTorch {v['torch'].split('+')[0]}, Transformers {v['transformers']}, TensorFlow {v['tensorflow']}, NumPy {v['numpy']} \\
Model settings & seed {m0['seed']}, environment seed {N['EnvSeed']}, scaled dot-product attention (SDPA), greedy decoding (OpenVLA-7B); chunks of 8 actions (OpenVLA-OFT) \\
Code & OpenVLA commit \texttt{{{m0['openvla_commit'][:7]}}}, OpenVLA-OFT commit \texttt{{{mo['oft_commit'][:7]}}}, LIBERO commit \texttt{{8f1084e}} \\
Hardware & one {m0['gpu']} (32 GB) per cell; host CPU per cell in Table~\ref{{tab:cells}} ({N['CpuMain']} for every harness cell except OpenVLA-OFT with the crop step off, {N['CpuOftCrop']}, and OpenVLA-7B rendered at 224, {N['CpuSevRend']}) \\
Compute & {N['GpuHours']} GPU hours for the 5,500 timed episodes of Table~\ref{{tab:cells}} (the original OpenVLA-OFT script does not log time) \\
\bottomrule
\end{{tabular}}
\end{{table}}
"""
(paper / "generated/table_setup.tex").write_text(setup)


# ---------------------------------------------------------------- Table: main results
def resrow(m, v):
    s = stat[f"{m}_spatial_{v}"]
    holm = "-" if s["holm"] is None else pfmt(s["holm"])
    return (f" & {VNAME[v]} & {s['k']} & {s['k'] / 5:.1f} [{s['wlo']:.1f}, {s['whi']:.1f}] & {sg(s['diff'])} & "
            f"[{sg(s['lo'])}, {sg(s['hi'])}] & {s['lost']} & {s['gained']} & {pfmt(s['p'])} & {holm} & "
            f"{s['ub']:.1f} & $\\pm${s['band']:.1f} \\\\")


body = []
for m, name in (("openvla7b", "OpenVLA-7B"), ("oft", "OpenVLA-OFT")):
    k = refk[m]; lo, hi = wilson(k, 500)
    body.append(f"{name} & Reference & {k} & {k / 5:.1f} [{lo:.1f}, {hi:.1f}] & \\multicolumn{{8}}{{c}}{{reference cell}} \\\\")
    for vv in ["rerun"] + VARS:
        body.append(resrow(m, vv))
    if m == "openvla7b":
        body.append(r"\midrule")
res = r"""% Generated by scripts/make_assets.py from the output of scripts/paired_stats.py of the results repository.
\begin{table*}[t]
\caption{Results on LIBERO-Spatial, 500 paired episodes per cell. Change: variant minus reference, in percentage points, with a 95\% percentile bootstrap interval over the paired episodes, computed exactly (no random draws). Lost: episodes that succeed under the reference and fail under the variant; gained: the reverse. $p$: exact two-sided McNemar test; Holm: adjusted over the seven secondary comparisons (the primary comparison, JPEG off for OpenVLA-7B, is not adjusted). Bound: one-sided 95\% upper bound on the loss, in points. Band: $\pm 1.96\sqrt{f}/500$, the acceptance region of the McNemar test given the $f$ flips (Section~\ref{sec:band}; near its ceiling OpenVLA-OFT cannot reach most of it).}
\label{tab:results}
\centering
\footnotesize
\setlength{\tabcolsep}{2.6pt}
\resizebox{\textwidth}{!}{\begin{tabular}{@{}llrccrrrrrrr@{}}
\toprule
Model & Cell & Successes & Rate (\%) [Wilson 95\%] & Change & Paired 95\% interval & Lost & Gained & $p$ & Holm & Bound & Band \\
\midrule
""" + "\n".join(body) + r"""
\bottomrule
\end{tabular}}
\end{table*}
"""
(paper / "generated/table_results.tex").write_text(res)
# Results table with the render-at-224 CPU control of OpenVLA-7B below its October cell, used only when that control
# reads (b) (controls/PLAN.md, section 7): both runs are reported.
_cpub = paper / "generated/table_results_cpub.tex"
if ctrl is not None and (ctrl["readings"].get("cpu_control") or {}).get("reading") == "b":
    n_ = ctrl["readings"]["cpu_control"]["new"]; lo_, hi_ = wilson(n_["k"], 500)
    row_ = (f" & Render at 224, rerun ({N['CpuMain']}) & {n_['k']} & {n_['k'] / 5:.1f} [{lo_:.1f}, {hi_:.1f}] & {sg(n_['diff'])} & "
            f"[{sg(n_['lo'])}, {sg(n_['hi'])}] & {n_['lost']} & {n_['gained']} & {pfmt(n_['p'])} & - & {n_['ub_loss']:.1f} & $\\pm${n_['band']:.1f} \\\\")
    anchor = resrow("openvla7b", "render224")
    assert anchor in res
    _cpub.write_text(res.replace(anchor, anchor + "\n" + row_).replace(r"\label{tab:results}", r"\label{tab:results}%"))
elif _cpub.exists():
    _cpub.unlink()

# ---------------------------------------------------------------- Table: control cells (only once their results exist)
if ctrl is not None:
    CNAME = {"sham_noise_seed1": "Noise of one level, draw 1", "sham_noise_seed2": "Noise of one level, draw 2",
             "sham_jpeg_q94": "JPEG quality 94"}
    crow = []
    for m, name in (("openvla7b", "OpenVLA-7B"), ("oft", "OpenVLA-OFT")):
        first = True
        for s_ in SHAM:
            c = f"{m}_spatial_{s_}"
            if c not in ctrl_cells:
                continue
            x_ = ctrl_cells[c]
            crow.append(f"{name if first else ''} & {CNAME[s_]} & {x_['k']} & {sg(x_['diff'])} & [{sg(x_['lo'])}, {sg(x_['hi'])}] & "
                        f"{x_['lost']} & {x_['gained']} & {x_['flips']} & {pfmt(x_['p'])} & $\\pm${x_['band']:.1f} \\\\")
            first = False
        if m == "openvla7b" and ctrl["readings"].get("cpu_control"):
            n_ = ctrl["readings"]["cpu_control"]["new"]
            crow.append(f" & Render at 224, rerun on {N['CpuMain']} & {n_['k']} & {sg(n_['diff'])} & [{sg(n_['lo'])}, {sg(n_['hi'])}] & "
                        f"{n_['lost']} & {n_['gained']} & {n_['flips']} & {pfmt(n_['p'])} & $\\pm${n_['band']:.1f} \\\\")
        if m == "openvla7b":
            crow.append(r"\midrule")
    ctab = r"""% Generated by scripts/make_assets.py from results/controls/summary.json (scripts/sham_control_analysis.py).
\begin{table}[t]
\caption{Control cells, run after the plan of the controls was committed (\PlanRef), each paired with the reference cell of its model as in Table~\ref{tab:results}. The sham changes belong to no evaluation pipeline: every value of every policy input moves by one intensity level up or down, or the JPEG round trip encodes at quality 94 instead of 95. McNemar $p$ is outside the Holm family of the paper. Band: $\pm 1.96\sqrt{f}/500$.}
\label{tab:controls}
\centering
\footnotesize
\setlength{\tabcolsep}{3pt}
\resizebox{\linewidth}{!}{\begin{tabular}{@{}llrrcrrrrr@{}}
\toprule
Model & Cell & Successes & Change & Paired 95\% interval & Lost & Gained & Flips & $p$ & Band \\
\midrule
""" + "\n".join(crow) + r"""
\bottomrule
\end{tabular}}
\end{table}
"""
    (paper / "generated/table_controls.tex").write_text(ctab)
elif (paper / "generated/table_controls.tex").exists():
    (paper / "generated/table_controls.tex").unlink()

# ---------------------------------------------------------------- Table: image-level EDA
def edarow(label, key):
    e = edas[key]
    return f"{label} & {e['mad']:.2f} & {e['min']:.2f}-{e['max']:.2f} & {e['p99']:.0f} & {100 * e['changed']:.0f} \\\\"


eda_tab = r"""% Generated by scripts/make_assets.py from eda/frames.jsonl (scripts/eda_frames.py).
\begin{table}[t]
\caption{How far each change moves the $224 \times 224$ RGB policy input of OpenVLA-7B, against the input of the official pipeline. Mean: mean absolute difference over all pixels and the three color channels, in intensity levels (0-255), averaged over """ + N["EdaFrames"] + r""" first frames (initial states 0-""" + str(int(N["EdaStates"]) - 1) + r""" of every task, rendered on CPU); range over frames; p99: 99th percentile of the per-value change; changed: share of pixels with any change. The four steps of this study are on top; the grayscale input and the ImageNet-C JPEG corruption are not part of any evaluation pipeline and are listed for scale.}
\label{tab:eda}
\centering
\footnotesize
\setlength{\tabcolsep}{3.5pt}
\begin{tabular}{@{}lrcrr@{}}
\toprule
Change & Mean & Range & p99 & Changed (\%) \\
\midrule
""" + "\n".join([
    edarow("Bilinear resize", "bilinear"),
    edarow("JPEG off", "jpeg_off"),
    edarow("Render at 224", "render224"),
    edarow("Crop step off (rescales)", "crop_off"),
    r"\midrule",
    edarow("Grayscale (luminance only)", "grayscale"),
    edarow("ImageNet-C JPEG, sev.~1 (q.~25)", "imagenetc_jpeg_s1"),
    edarow("ImageNet-C JPEG, sev.~3 (q.~15)", "imagenetc_jpeg_s3"),
    edarow("ImageNet-C JPEG, sev.~5 (q.~7)", "imagenetc_jpeg_s5"),
]) + r"""
\bottomrule
\end{tabular}
\end{table}
"""
(paper / "generated/table_eda.tex").write_text(eda_tab)

# ---------------------------------------------------------------- Table: ablations of the analysis
ab = r"""% Generated by scripts/make_assets.py.
\begin{table}[t]
\caption{Ablation of the analysis choices on the primary comparison (JPEG off, OpenVLA-7B), and checks of the reading of the secondary results. Change and 95\% bootstrap interval in points; bound: one-sided 95\% upper bound on the loss.}
\label{tab:ablation}
\centering
\footnotesize
\setlength{\tabcolsep}{3pt}
\begin{tabular}{@{}L{0.45\columnwidth}L{0.49\columnwidth}@{}}
\toprule
Choice removed or changed & Result \\
\midrule
Paired bootstrap (as reported) & """ + f"{N['SevJpegDiff']} [{N['AblPairedLo']}, {N['AblPairedHi']}], width {N['AblPairedW']}, bound {N['AblPairedUB']}" + r""" \\
Pairing removed (cells treated as independent samples) & """ + f"{N['SevJpegDiff']} [{N['AblUnpairedLo']}, {N['AblUnpairedHi']}], width {N['AblUnpairedW']}, bound {N['AblUnpairedUB']}" + r""" \\
200 initial states (0-19) instead of 500 & """ + f"{N['AblFirstDiff']} [{N['AblFirstLo']}, {N['AblFirstHi']}], width {N['AblFirstW']}; {N['AblFirstLost']} lost, {N['AblFirstGained']} gained" + r""" \\
One task left out (10 analyses) & """ + f"change between {N['AblLooMin']} and {N['AblLooMax']}" + r""" \\
Step budget cut from 230 to 180 / 150 / 120 env steps & """ + f"flips {N['BudgetOneEighty']} / {N['BudgetOneFifty']} / {N['BudgetOneTwenty']} (against {N['SevJpegFlips']})" + r""" \\
Initial states 20-49 only (outside the pilot) & """ + f"{N['OutDiff']} [{N['OutLo']}, {N['OutHi']}], bound {N['OutUB']}; {N['OutLost']} lost, {N['OutGained']} gained, $p = {N['OutP']}$" + r""" \\
Tasks resampled instead of episodes & """ + f"[{N['ClusJpegLo']}, {N['ClusJpegHi']}], bound {N['ClusJpegUB']} (OpenVLA-OFT crop off: [{N['ClusOftCropLo']}, {N['ClusOftCropHi']}])" + r""" \\
Logged rerun as the reference instead of the reference cell & """ + f"{N['VrJpegDiff']} [{N['VrJpegLo']}, {N['VrJpegHi']}], bound {N['VrJpegUB']}; four variants: {N['VrFlipsMin']}-{N['VrFlipsMax']} flips, every $p \\geq {N['VrPMin']}$" + r""" \\
\midrule
OpenVLA-OFT crop off without task 5 & """ + f"{N['OftCropNoFiveLost']} lost, {N['OftCropNoFiveGained']} gained, $p = {N['OftCropNoFiveP']}$ (with task 5: {N['OftCropLost']} lost, {N['OftCropGained']} gained)" + r""" \\
Variant against variant instead of against the reference (OpenVLA-7B, 6 pairs) & """ + f"{N['SevVVfMin']}-{N['SevVVfMax']} flips, every $p \\geq {N['SevVVpMin']}$" + r""" \\
Reference cell split by initial state (OpenVLA-7B) & """ + f"states 0-19: {N['SevSplitRefA']} vs {N['SevSplitVarAMin']}-{N['SevSplitVarAMax']}; states 20-49: {N['SevSplitRefB']} vs {N['SevSplitVarBMin']}-{N['SevSplitVarBMax']}" + r""" \\
\bottomrule
\end{tabular}
\end{table}
"""
(paper / "generated/table_ablation.tex").write_text(ab)

# ---------------------------------------------------------------- Table: comparison with other evaluations
E = {k: e["value"] for k, e in EXT.items()}
cmp_tab = r"""% Generated by scripts/make_assets.py; numbers of other studies come from data/external_numbers.json.
\begin{table}[t]
\caption{LIBERO-Spatial success of the same released checkpoints in other evaluations (numbers as reported) and in this study. OpenVLA: mean and standard error over three seeds of 500 episodes. vla-eval: its published per-episode results, which we pair with ours (Section~\ref{sec:compare}); its image steps and environment loop are its own. StableVLA: 500 episodes per suite; checkpoint revisions and evaluation script not stated.}
\label{tab:compare}
\centering
\small
\begin{tabular}{@{}lcc@{}}
\toprule
Evaluation & OpenVLA-7B (\%) & OpenVLA-OFT (\%) \\
\midrule
OpenVLA paper, official code~\citep{openvla} & """ + f"{E['OpenvlaSpatial']} $\\pm$ {E['OpenvlaSpatialSe']}" + r""" & - \\
OpenVLA-OFT paper, official code~\citep{oft} & - & """ + E["OftSpatial"] + r""" \\
vla-eval harness~\citep{vlaevalrepo} & """ + E["VeSpatial"] + r""" & - \\
StableVLA, clean images~\citep{stablevla} & """ + E["StableClean"] + r""" & """ + E["StableOftClean"] + r""" \\
\midrule
This study, reference cell & """ + f"{N['SevRefPct']} [{N['SevRefLo']}, {N['SevRefHi']}]" + r""" & """ + f"{N['OftRefPct']} [{N['OftRefLo']}, {N['OftRefHi']}]" + r""" \\
This study, four single-step variants & """ + f"{N['SevVarMinPct']}-{N['SevVarMaxPct']}" + r""" & """ + f"{N['OftVarMinPct']}-{N['OftVarMaxPct']}" + r""" \\
\bottomrule
\end{tabular}
\end{table}
"""
(paper / "generated/table_compare.tex").write_text(cmp_tab)

# ---------------------------------------------------------------- Figure 1: pipeline with real frames
ex = paper / "example_frames"
img_render = Image.open(ex / "task0_state0_render256.png")
img_jpeg = Image.open(ex / "task0_state0_input_jpeg_on.png")
img_crop = Image.open(ex / "task0_state0_input_jpeg_on_cropped.png")
on = np.asarray(img_jpeg, dtype=np.int16); off = np.asarray(Image.open(ex / "task0_state0_input_jpeg_off.png"), dtype=np.int16)
heat = np.abs(on - off).mean(axis=2)  # per-pixel mean over R, G, B: its image mean is the reported change
W, H = TEXTW, 1.95
fig = plt.figure(figsize=(W, H))
side = 1.24
xs = [0.02, 1.90, 3.78, 5.36]
titles = ["(a) Render, 256 $\\times$ 256, RGB", "(b) After steps 1 and 2", "(c) Policy input, 224, RGB",
          "(d) Where step 1 changes (b)"]
axes_ = []
for i, (x, t) in enumerate(zip(xs, titles)):
    ax = fig.add_axes([x / W, 0.2, side / W, side / H]); axes_.append(ax)
    if i < 3:
        ax.imshow([img_render, img_jpeg, img_crop][i], interpolation="nearest")
    else:
        hm = ax.imshow(heat, cmap="Reds", vmin=0, vmax=6, interpolation="nearest")
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(True); s.set_linewidth(0.5)
    ax.set_title(t, fontsize=7.3, pad=3)
cax = fig.add_axes([(xs[3] + side + 0.06) / W, 0.2, 0.07 / W, side / H])
cb = fig.colorbar(hm, cax=cax, ticks=[0, 2, 4, 6])
cb.ax.set_yticklabels(["0", "2", "4", "$\\geq$6"]); cb.ax.tick_params(labelsize=6, length=2, pad=1); cb.outline.set_linewidth(0.4)
cb.set_label("intensity levels", fontsize=6, labelpad=1)
arrows = [("1: JPEG round\ntrip, quality 95", "2: Lanczos3,\nantialiased, 224", 1.29, 1.86),
          ("3: center crop,\n90% of area", "bilinear back\nto 224", 3.17, 3.74)]
for above, below, x0, x1 in arrows:
    fig.patches.append(matplotlib.patches.FancyArrowPatch((x0 / W, 0.54), (x1 / W, 0.54), transform=fig.transFigure,
                                                          arrowstyle="-|>", mutation_scale=8, lw=0.8, color=GREY))
    fig.text((x0 + x1) / 2 / W, 0.59, above, ha="center", va="bottom", fontsize=6, color=INK)
    fig.text((x0 + x1) / 2 / W, 0.49, below, ha="center", va="top", fontsize=6, color=INK)
fig.add_artist(matplotlib.lines.Line2D([5.15 / W, 5.15 / W], [0.12, 0.95], transform=fig.transFigure, lw=0.6,
                                       ls=(0, (2, 2)), color=GREY))
fig.text(0.02 / W, 0.04, "Task 0, initial state 0, rendered on CPU with the official image code. "
         "Panel (d) is a visualization of the difference, not an input: the policy always receives RGB images.",
         fontsize=6.2, color=GREY)
fig.savefig(paper / "figures/pipeline.pdf", metadata={"CreationDate": None})
plt.close(fig)

# ---------------------------------------------------------------- Figure 2: data overview
pt7 = succ["openvla7b_spatial_reference"].reshape(10, 50).sum(1)
ptO = succ["oft_spatial_reference"].reshape(10, 50).sum(1)
fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(TEXTW, 1.6), gridspec_kw={"width_ratios": [1.5, 1, 1]})
x = np.arange(10)
a1.bar(x - 0.21, pt7, 0.38, color=BLUE, label="OpenVLA-7B")
a1.bar(x + 0.21, ptO, 0.38, color=ORANGE, label="OpenVLA-OFT")
a1.set_xticks(x); a1.set_xlabel("Task", labelpad=1); a1.set_ylabel("Successes of 50", labelpad=1)
a1.set_ylim(0, 62); a1.set_yticks([0, 10, 20, 30, 40, 50])
a1.set_title("(a) Reference success per task", fontsize=7.5, pad=3)
a1.legend(fontsize=6, frameon=False, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.04), handlelength=1)
a2.hist(succ_steps, bins=np.arange(60, 235, 10), color=BLUE)
a2.axvline(230, color=VERM, lw=0.8, ls=(0, (2, 1.5)))
a2.text(228, a2.get_ylim()[1] * 0.92, "failures\nend at 230", ha="right", va="top", fontsize=5.8, color=INK)
a2.set_xlabel("Env steps at success", labelpad=1); a2.set_ylabel("Episodes", labelpad=1)
a2.set_title("(b) OpenVLA-7B episode length", fontsize=7.5, pad=3)
a3.hist(gpu_mad, bins=np.arange(1.26, 1.385, 0.01), color=GREY)
a3.set_xlabel("Intensity levels (of 255)", labelpad=1); a3.set_ylabel("Episodes", labelpad=1)
a3.set_title("(c) JPEG change, first input", fontsize=7.5, pad=3)
for a in (a1, a2, a3):
    a.tick_params(labelsize=6.5, length=2, pad=1)
fig.tight_layout(pad=0.3, w_pad=1.0)
fig.savefig(paper / "figures/data.pdf", metadata={"CreationDate": None})
plt.close(fig)

# ---------------------------------------------------------------- Figure 3: flips per task, every variant
fig, axes = plt.subplots(2, 4, figsize=(TEXTW, 3.0), sharey=True)
for r_, (m, mname, lim) in enumerate((("openvla7b", "OpenVLA-7B", 10), ("oft", "OpenVLA-OFT", 10))):
    for c_, vv in enumerate(VARS):
        ax = axes[r_, c_]; s = stat[f"{m}_spatial_{vv}"]
        y = np.arange(10)
        ax.barh(y, -np.array(s["lost_task"]), color=VERM, height=0.72, label="lost")
        ax.barh(y, np.array(s["gained_task"]), color=BLUE, height=0.72, label="gained")
        ax.axvline(0, color=INK, lw=0.6)
        ax.set_xlim(-lim, lim); ax.set_xticks([-10, -5, 0, 5, 10]); ax.set_xticklabels(["10", "5", "0", "5", "10"])
        ax.set_title(f"{mname}, {VNAME[vv] if vv == 'jpeg_off' else VNAME[vv].lower()}\n{s['lost']} lost, {s['gained']} gained", fontsize=6.8, pad=2)
        ax.tick_params(labelsize=6.2, length=2, pad=1)
        ax.grid(axis="x", color="#dddddd", lw=0.4); ax.set_axisbelow(True)
    axes[r_, 0].set_yticks(np.arange(10)); axes[r_, 0].set_yticklabels([f"Task {t}" for t in range(10)])
axes[0, 0].invert_yaxis()
axes[1, 3].legend(fontsize=6.5, frameon=False, loc="lower right", handlelength=1)
fig.text(0.5, 0.005, "Episodes per task (lost to the left, gained to the right; 50 paired episodes per task)",
         ha="center", va="bottom", fontsize=6.8)
fig.tight_layout(pad=0.3, w_pad=0.5, h_pad=0.6, rect=(0, 0.03, 1, 1))
fig.savefig(paper / "figures/flips.pdf", metadata={"CreationDate": None})
plt.close(fig)

# ---------------------------------------------------------------- Figure 4: net change against flips, chance band
fig, ax = plt.subplots(figsize=(COLW, 2.75))
f = np.linspace(0, 100, 400)
ax.fill_between(f, -Z * np.sqrt(f), Z * np.sqrt(f), color="#e8e8e8", lw=0)
ax.plot(f, Z * np.sqrt(f), color=GREY, lw=0.7); ax.plot(f, -Z * np.sqrt(f), color=GREY, lw=0.7)
ax.axhline(0, color=INK, lw=0.5)
ax.axhline(-15, color=VERM, lw=0.7, ls=(0, (3, 2)))
ax.text(2, -16.0, "net loss of 3 points (15 episodes)", fontsize=5.8, color=INK, va="top", ha="left")
mk = {"jpeg_off": "o", "crop_off": "s", "bilinear": "D", "render224": "^"}
for m, col, mn in (("openvla7b", BLUE, "OpenVLA-7B"), ("oft", ORANGE, "OpenVLA-OFT")):
    for vv in VARS:
        s = stat[f"{m}_spatial_{vv}"]
        ax.scatter(s["flips"], s["gained"] - s["lost"], marker=mk[vv], s=22, color=col, edgecolor="white", lw=0.6, zorder=3)
    s = stat[f"{m}_spatial_rerun"]
    ax.scatter(s["flips"], s["gained"] - s["lost"], marker="x", s=22, color=col, lw=1.0, zorder=3)
ax.scatter(ve_lost + ve_gained, ve_gained - ve_lost, marker="*", s=45, color=INK, zorder=3)
ax.text(ve_lost + ve_gained - 3, ve_gained - ve_lost, "vla-eval vs.\nreference", fontsize=5.8, ha="right", va="center", color=INK)
ax.text(30, Z * np.sqrt(30) + 1.5, "95% band, ±1.96√f", fontsize=5.8, ha="center", va="bottom", color=INK)
# OpenVLA-OFT can gain only among its reference failures: G <= failures, so G - L <= 2 x failures - f
fc = np.linspace(0, 2 * oft_ref_fail + 26, 50)
ax.plot(fc, 2 * oft_ref_fail - fc, color=ORANGE, lw=0.8, ls=(0, (3, 1.5)))
ax.text(19, -6.5, f"OpenVLA-OFT ceiling: $G - L \\leq {2 * oft_ref_fail} - f$", fontsize=5.6, ha="left", va="center", color=INK)
from matplotlib.lines import Line2D  # noqa: E402
hand = [Line2D([], [], marker=mk[vv], ls="", color=GREY, ms=4, label=VNAME[vv]) for vv in VARS]
hand += [Line2D([], [], marker="x", ls="", color=GREY, ms=4, label="rerun (A/A)"),
         Line2D([], [], marker="*", ls="", color=INK, ms=5, label="vla-eval vs. reference"),
         Line2D([], [], marker="s", ls="", color=BLUE, ms=4, label="OpenVLA-7B"),
         Line2D([], [], marker="s", ls="", color=ORANGE, ms=4, label="OpenVLA-OFT")]
ax.legend(handles=hand, fontsize=5.8, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3, handletextpad=0.3, columnspacing=0.9)
ax.set_xlim(0, 100); ax.set_ylim(-26, 26)
ax.set_xlabel("Episodes that change outcome, $f$ (of 500)", labelpad=1)
ax.set_ylabel("Gained $-$ lost (episodes)", labelpad=1)
ax.tick_params(labelsize=6.5, length=2, pad=1)
fig.tight_layout(pad=0.3)
fig.savefig(paper / "figures/band.pdf", metadata={"CreationDate": None})
plt.close(fig)

json.dump({"numbers": N, "stat": stat, "expl": expl, "budget": budget, "same_step": same_step, "abl": abl,
           "pilot": pilot, "ve_cells": ve_cells, "edas": edas, "runlog": runlog},
          open(paper / "generated/all_numbers.json", "w"), indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
for k, val in N.items():
    print(f"{k} = {val}")
