"""Independent recomputation of the numbers of the paper from the per-episode result files.

Written separately from scripts/paired_stats.py, scripts/post_lock_checks.py and paper/scripts/make_assets.py and
does not import or call them. It parses the result files with its own code, recomputes every closed-loop number,
checks the open-loop summary against the closed-loop flips, and compares each value with the macro of the same name
in paper/generated/numbers.tex.

Bootstrap intervals are recomputed two ways:
  - exact: the limit of the paired bootstrap as the number of draws grows. A paired episode contributes -1, 0 or +1,
    so the resampled sum is G - L with (L, G) multinomial over the 500 pairs; its distribution is computed exactly,
    with no random numbers.
  - Monte Carlo: 20,000 draws, as in the paper, repeated over 200 seeds to show how much the last digit can move.
An interval end is marked "edge" when the exact cumulative probability at the neighbouring value lies so close to
the target quantile (2.5%, 97.5% or 95%) that 20,000 draws resolve it to one decimal only by the choice of seed.

Usage: python -I audit/independent_recheck.py [repo_root]  (writes audit/recheck_report.md and audit/recheck.json)
"""
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1])
RES = ROOT / "results"
PAPER = ROOT / "paper"
N_TASKS, N_STATES = 10, 50
KEYS = [(t, s) for t in range(N_TASKS) for s in range(N_STATES)]
VARIANTS = ["jpeg_off", "crop_off", "bilinear", "render224"]
MAC = {"openvla7b": "Sev", "oft": "Oft"}
VMAC = {"rerun": "Rerun", "jpeg_off": "Jpeg", "crop_off": "Crop", "bilinear": "Bil", "render224": "Rend"}
Z = 1.959963984540054
problems = []


def note(msg):
    problems.append(msg)


# ------------------------------------------------------------------ loading
def read_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def load_openvla7b(cell):
    out = {}
    for r in read_jsonl(RES / cell / "episodes.jsonl"):
        key = (int(r["task_id"]), int(r["episode_idx"]))
        if "initial_state" in r and int(r["initial_state"]) != key[1]:
            note(f"{cell}: initial_state field differs from episode_idx at {key}")
        if key in out:
            note(f"{cell}: duplicate episode {key}")
        out[key] = r
    return out


def load_oft_segments(cell):
    """Read the two segments directly (offset 0 and 20) and check the merged file against them."""
    out = {}
    for seg, offset, per_task in (("states_0-19", 0, 20), ("states_20-49", 20, 30)):
        recs = read_jsonl(RES / cell / seg / "episodes.jsonl")
        if len(recs) != N_TASKS * per_task:
            note(f"{cell}/{seg}: {len(recs)} records, expected {N_TASKS * per_task}")
        for r in recs:
            if int(r.get("init_offset", -1)) != offset:
                note(f"{cell}/{seg}: init_offset {r.get('init_offset')} != {offset}")
            key = (int(r["task_id"]), offset + int(r["episode_idx"]))
            if int(r["initial_state"]) != key[1]:
                note(f"{cell}/{seg}: initial_state {r['initial_state']} != {key[1]}")
            if key in out:
                note(f"{cell}: duplicate episode {key}")
            out[key] = r
    merged = {(int(r["task_id"]), int(r["initial_state"])): int(bool(r["success"]))
              for r in read_jsonl(RES / cell / "episodes.jsonl")}
    if merged != {k: int(bool(v["success"])) for k, v in out.items()}:
        note(f"{cell}: merged episodes.jsonl differs from its two segments")
    return out


def load_oft_reference_logs(task_names):
    """Parse the original OpenVLA-OFT script logs line by line: Task, Starting episode k, Success."""
    out = {}
    for seg, offset in (("states_0-19", 0), ("states_20-49", 20)):
        logs = sorted((RES / "oft_spatial_reference" / seg).glob("EVAL-*.txt"))
        assert len(logs) == 1, (seg, logs)
        task, ep = None, None
        for line in logs[0].read_text().splitlines():
            if line.startswith("Task: "):
                task = task_names[line[len("Task: "):].strip()]
            elif line.startswith("Starting episode "):
                ep = int(line[len("Starting episode "):].rstrip(".").strip())
            elif line.startswith("Success: "):
                key = (task, offset + ep - 1)
                if key in out:
                    note(f"oft reference: duplicate {key}")
                out[key] = {"success": line.split()[1] == "True", "env_steps": None}
                task, ep = task, None
    return out


cells = {}
for v in ["reference", "rerun"] + VARIANTS:
    cells[f"openvla7b_spatial_{v}"] = load_openvla7b(f"openvla7b_spatial_{v}")
names = {r["task_description"]: k[0] for k, r in cells["openvla7b_spatial_reference"].items()}
assert len(names) == N_TASKS
cells["oft_spatial_reference"] = load_oft_reference_logs(names)
for v in ["rerun"] + VARIANTS + ["crop_off_cpu_control"]:
    cells[f"oft_spatial_{v}"] = load_oft_segments(f"oft_spatial_{v}")
for c, d in cells.items():
    if set(d) != set(KEYS):
        note(f"{c}: holds {len(d)} pairs, missing {len(set(KEYS) - set(d))}")

# initial-state hashes: every logged hash against the OpenVLA-7B reference (same LIBERO init file)
ref_hash = {k: r["init_state_sha1"] for k, r in cells["openvla7b_spatial_reference"].items()}
hash_match = {}
for c, d in cells.items():
    hs = [(k, r.get("init_state_sha1")) for k, r in d.items()]
    if all(h is None for _, h in hs):
        hash_match[c] = "no hashes logged"
        continue
    n = sum(h == ref_hash[k] for k, h in hs)
    hash_match[c] = f"{n}/500"
    if n != 500:
        note(f"{c}: {500 - n} initial-state hashes differ from the reference")

S = {c: np.array([int(bool(d[k]["success"])) for k in KEYS]) for c, d in cells.items()}
STEPS = {c: np.array([d[k]["env_steps"] if d[k].get("env_steps") is not None else -1 for k in KEYS]) for c, d in cells.items()}


# ------------------------------------------------------------------ statistics, own implementations
def wilson(k, n):
    p = k / n
    den = 1 + Z * Z / n
    centre = (p + Z * Z / (2 * n)) / den
    half = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / den
    return 100 * (centre - half), 100 * (centre + half)


def mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return 1.0
    p_own = min(1.0, 2 * stats.binom.cdf(min(b, c), n, 0.5))
    p_scipy = stats.binomtest(min(b, c), n, 0.5).pvalue
    assert abs(p_own - p_scipy) < 1e-12, (b, c)
    return p_own


def holm(pvals):
    order = sorted(pvals, key=pvals.get)
    out, run, m = {}, 0.0, len(order)
    for i, c in enumerate(order):
        run = max(run, min(1.0, (m - i) * pvals[c]))
        out[c] = run
    return out


def exact_boot(lost, gained, n=500):
    """Exact distribution of the bootstrap net change G - L (in episodes) over n resampled pairs."""
    pl, pg = lost / n, gained / n
    pmf = {}
    ls = np.arange(n + 1)
    p_l = stats.binom.pmf(ls, n, pl) if pl > 0 else (ls == 0).astype(float)
    for l in ls:
        if p_l[l] < 1e-300:
            continue
        rest = n - l
        q = pg / (1 - pl) if pl < 1 else 0.0
        gs = np.arange(rest + 1)
        p_g = stats.binom.pmf(gs, rest, q) if q > 0 else (gs == 0).astype(float)
        for g in gs[p_g > 1e-300]:
            pmf[g - l] = pmf.get(g - l, 0.0) + p_l[l] * p_g[g]
    vals = np.array(sorted(pmf))
    probs = np.array([pmf[v] for v in vals])
    return vals, np.cumsum(probs)


def exact_quantile(vals, cdf, q):
    """Smallest value whose cumulative probability reaches q, and the gap |CDF(previous) - q| to the next value down."""
    i = int(np.searchsorted(cdf, q - 1e-15))
    gap_below = abs(cdf[i - 1] - q) if i > 0 else 1.0
    gap_here = abs(cdf[i] - q)
    return vals[i], min(gap_below, gap_here)


def mc_boot(d, seed, draws=20000):
    rng = np.random.default_rng(seed)
    m = d[rng.integers(0, len(d), (draws, len(d)))].mean(1) * 100
    return np.percentile(m, 2.5), np.percentile(m, 97.5), np.percentile(-m, 95)


def half_up(x):
    return int(math.floor(x + 0.5))


def r1(x):
    """Round half away from zero to one decimal; no negative zero."""
    y = math.floor(abs(x) * 10 + 0.5 + 1e-9) / 10
    y = math.copysign(y, x)
    return 0.0 if y == 0 else y


EDGE = 0.004  # 3.6 standard errors of an empirical quantile at 2.5% with 20,000 draws
rows = {}
for model in ["openvla7b", "oft"]:
    ref = S[f"{model}_spatial_reference"]
    for v in ["rerun"] + VARIANTS + (["crop_off_cpu_control"] if model == "oft" else []):
        c = f"{model}_spatial_{v}"
        x = S[c]
        lost = int(((ref == 1) & (x == 0)).sum())
        gained = int(((ref == 0) & (x == 1)).sum())
        d = x - ref
        vals, cdf = exact_boot(lost, gained)
        lo, glo = exact_quantile(vals, cdf, 0.025)
        hi, ghi = exact_quantile(vals, cdf, 0.975)
        # upper bound on the loss = 95th percentile of the loss = -(5th percentile of the net change)
        q5, gub = exact_quantile(vals, cdf, 0.05)
        mc = np.array([mc_boot(d, s) for s in range(100)])
        rows[c] = dict(
            k=int(x.sum()), pct=x.mean() * 100, wilson=wilson(int(x.sum()), 500), diff=100 * d.mean(),
            lost=lost, gained=gained, flips=lost + gained, p=mcnemar_exact(lost, gained),
            band=100 * Z * math.sqrt(lost + gained) / 500,
            ex_lo=lo / 5, ex_hi=hi / 5, ex_ub=-q5 / 5, edge_lo=glo < EDGE, edge_hi=ghi < EDGE, edge_ub=gub < EDGE,
            mc_lo=sorted({r1(a) for a in mc[:, 0]}), mc_hi=sorted({r1(a) for a in mc[:, 1]}),
            mc_ub=sorted({r1(a) for a in mc[:, 2]}),
            flips_task=[int((ref.reshape(10, 50)[t] != x.reshape(10, 50)[t]).sum()) for t in range(10)],
            same=int((ref == x).sum()))
secondary = [f"openvla7b_spatial_{v}" for v in ["crop_off", "bilinear", "render224"]] + \
            [f"oft_spatial_{v}" for v in VARIANTS]
for c, hp in holm({c: rows[c]["p"] for c in secondary}).items():
    rows[c]["holm"] = hp

# ------------------------------------------------------------------ further closed-loop numbers
X = {}
r7, x7 = S["openvla7b_spatial_reference"], S["openvla7b_spatial_rerun"]
both = (r7 == 1) & (x7 == 1)
X["SevRerunSame"] = int((r7 == x7).sum())
X["RerunBoth"] = int(both.sum())
X["RerunSameStep"] = int((both & (STEPS["openvla7b_spatial_reference"] == STEPS["openvla7b_spatial_rerun"])).sum())
X["OftRerunSame"] = rows["oft_spatial_rerun"]["same"]
cc = rows["oft_spatial_crop_off_cpu_control"]
X["CpuCtrlK"] = cc["k"]
X["CpuCtrlSame"] = int((S["oft_spatial_crop_off_cpu_control"] == S["oft_spatial_crop_off"]).sum())
X["CpuCtrlDiffer"] = 500 - X["CpuCtrlSame"]
X["CpuCtrlLost"], X["CpuCtrlGained"] = cc["lost"], cc["gained"]

# fragile episodes over the five OpenVLA-7B pipelines (reference and four variants)
five = np.stack([S["openvla7b_spatial_reference"]] + [S[f"openvla7b_spatial_{v}"] for v in VARIANTS])
X["SevAlways"] = int((five.sum(0) == 5).sum())
X["SevNever"] = int((five.sum(0) == 0).sum())
X["SevChange"] = 500 - X["SevAlways"] - X["SevNever"]
X["SevRefFail"] = int((r7 == 0).sum())
X["SevRescued"] = int(((r7 == 0) & (five[1:].max(0) == 1)).sum())
fiveo = np.stack([S["oft_spatial_reference"]] + [S[f"oft_spatial_{v}"] for v in VARIANTS])
X["OftAlways"] = int((fiveo.sum(0) == 5).sum())
X["OftNever"] = int((fiveo.sum(0) == 0).sum())
X["OftChange"] = 500 - X["OftAlways"] - X["OftNever"]
changing_o = (fiveo.sum(0) > 0) & (fiveo.sum(0) < 5)
X["OftChangeTaskFive"] = int(changing_o.reshape(10, 50)[5].sum())

# overlap of flips between variants (OpenVLA-7B), against chance
flipsets = {v: (S[f"openvla7b_spatial_{v}"] != r7) for v in VARIANTS}
ov, ch = [], []
for i, a in enumerate(VARIANTS):
    for b in VARIANTS[i + 1:]:
        ov.append(int((flipsets[a] & flipsets[b]).sum()))
        ch.append(flipsets[a].sum() * flipsets[b].sum() / 500)
X["SevOverlapMin"], X["SevOverlapMax"] = min(ov), max(ov)
X["SevChanceMin"], X["SevChanceMax"] = r1(min(ch)), r1(max(ch))
ratios = [o / e for o, e in zip(ov, ch)]
X["SevOverlapRatioMin"], X["SevOverlapRatioMax"] = r1(min(ratios)), r1(max(ratios))
vv = []
for i, a in enumerate(VARIANTS):
    for b in VARIANTS[i + 1:]:
        xa, xb = S[f"openvla7b_spatial_{a}"], S[f"openvla7b_spatial_{b}"]
        la, lb = int(((xa == 1) & (xb == 0)).sum()), int(((xa == 0) & (xb == 1)).sum())
        vv.append((la + lb, mcnemar_exact(la, lb)))
X["SevVVfMin"], X["SevVVfMax"] = min(f for f, _ in vv), max(f for f, _ in vv)
X["SevVVpMin"] = min(p for _, p in vv)

# split by initial state
first = np.array([s < 20 for _, s in KEYS])
X["SevSplitRefA"], X["SevSplitRefB"] = int(r7[first].sum()), int(r7[~first].sum())
va = [int(S[f"openvla7b_spatial_{v}"][first].sum()) for v in VARIANTS]
vb = [int(S[f"openvla7b_spatial_{v}"][~first].sum()) for v in VARIANTS]
X["SevSplitVarAMin"], X["SevSplitVarAMax"] = min(va), max(va)
X["SevSplitVarBMin"], X["SevSplitVarBMax"] = min(vb), max(vb)

# same success step among episodes that succeed in both
for model, pre in (("openvla7b", "Sev"), ("oft", "Oft")):
    refc = "openvla7b_spatial_reference" if model == "openvla7b" else "oft_spatial_rerun"  # OFT reference logs no steps
    same, med = [], []
    for v in VARIANTS:
        xs = S[f"{model}_spatial_{v}"]
        bb = (S[refc] == 1) & (xs == 1)
        st_r, st_x = STEPS[refc][bb], STEPS[f"{model}_spatial_{v}"][bb]
        same.append(100 * (st_r == st_x).mean())
        med.append(float(np.median(np.abs(st_r - st_x))))
    X[f"{pre}SameStepMin"], X[f"{pre}SameStepMax"] = half_up(min(same)), half_up(max(same))
    X[f"{pre}StepDiffMin"], X[f"{pre}StepDiffMax"] = half_up(min(med)), half_up(max(med))

# OpenVLA-OFT crop off: task 5 and the comparison with bilinear
ro, xo = S["oft_spatial_reference"].reshape(10, 50), S["oft_spatial_crop_off"].reshape(10, 50)
keep = np.arange(10) != 5
l5, g5 = int(((ro[keep] == 1) & (xo[keep] == 0)).sum()), int(((ro[keep] == 0) & (xo[keep] == 1)).sum())
X["OftCropNoFiveLost"], X["OftCropNoFiveGained"], X["OftCropNoFiveP"] = l5, g5, mcnemar_exact(l5, g5)
X["OftCropTaskFiveLost"] = int(((ro[5] == 1) & (xo[5] == 0)).sum())
X["OftTaskFiveCrop"] = int(xo[5].sum())
others = [int(S[f"oft_spatial_{v}"].reshape(10, 50)[5].sum()) for v in ["reference", "rerun", "jpeg_off", "bilinear", "render224"]]
X["OftTaskFiveOthersMin"], X["OftTaskFiveOthersMax"] = min(others), max(others)
xb_, xc_ = S["oft_spatial_bilinear"], S["oft_spatial_crop_off"]
lb_, gb_ = int(((xb_ == 1) & (xc_ == 0)).sum()), int(((xb_ == 0) & (xc_ == 1)).sum())
X["OftCropVsBilLost"], X["OftCropVsBilGained"] = lb_, gb_
X["OftCropVsBilP"] = mcnemar_exact(lb_, gb_)

# ablations of the analysis for the primary comparison: unpaired, and paired on initial states 0-19 only
def exact_unpaired(kr, kx, n=500):
    pr_, px_ = stats.binom.pmf(np.arange(n + 1), n, kr / n), stats.binom.pmf(np.arange(n + 1), n, kx / n)
    pmf = np.convolve(px_, pr_[::-1])            # index i <-> kx' - kr' = i - n
    return np.arange(-n, n + 1), np.cumsum(pmf)


rj, xj = S["openvla7b_spatial_reference"], S["openvla7b_spatial_jpeg_off"]
vals, cdf = exact_unpaired(int(rj.sum()), int(xj.sum()))
X["AblUnpairedLo"] = exact_quantile(vals, cdf, 0.025)[0] / 5
X["AblUnpairedHi"] = exact_quantile(vals, cdf, 0.975)[0] / 5
X["AblUnpairedUB"] = -exact_quantile(vals, cdf, 0.05)[0] / 5
X["AblPairedLo"], X["AblPairedHi"] = rows["openvla7b_spatial_jpeg_off"]["ex_lo"], rows["openvla7b_spatial_jpeg_off"]["ex_hi"]
X["AblPairedUB"] = rows["openvla7b_spatial_jpeg_off"]["ex_ub"]
f20 = np.array([s_ < 20 for _, s_ in KEYS])
l20, g20 = int(((rj == 1) & (xj == 0) & f20).sum()), int(((rj == 0) & (xj == 1) & f20).sum())
vals, cdf = exact_boot(l20, g20, n=200)
X["AblFirstLost"], X["AblFirstGained"] = l20, g20
X["AblFirstDiff"] = 100 * (g20 - l20) / 200
X["AblFirstLo"] = exact_quantile(vals, cdf, 0.025)[0] / 2
X["AblFirstHi"] = exact_quantile(vals, cdf, 0.975)[0] / 2
X["AblFirstUB"] = -exact_quantile(vals, cdf, 0.05)[0] / 2
loo = [100 * (xj[np.array([t_ != t for t_, _ in KEYS])].mean() - rj[np.array([t_ != t for t_, _ in KEYS])].mean()) for t in range(10)]
X["AblLooMin"], X["AblLooMax"] = min(loo), max(loo)

# pilot (initial states 0-19, 12 October)
PIL = PAPER / "data" / "pilot_states_0-19"
pil = {c.name: {(int(r["task_id"]), int(r["episode_idx"])): int(bool(r["success"])) for r in read_jsonl(c / "episodes.jsonl")}
       for c in sorted(PIL.iterdir()) if (c / "episodes.jsonl").exists()}
pr, pj = pil["openvla_reference"], pil["openvla_jpeg_off"]
X["PilotLost"] = sum(pr[k] == 1 and pj[k] == 0 for k in pr)
X["PilotGained"] = sum(pr[k] == 0 and pj[k] == 1 for k in pr)
X["PilotFlips"] = X["PilotLost"] + X["PilotGained"]
X["PilotDisc"] = 100 * X["PilotFlips"] / 200
X["PilotDiff"] = 100 * (X["PilotGained"] - X["PilotLost"]) / 200
X["PilotF"] = X["PilotFlips"] / 200 * 500
X["PilotSD"] = math.sqrt(X["PilotF"])
X["PilotBandEp"] = Z * X["PilotSD"]
X["PilotBandPts"] = X["PilotBandEp"] / 5
X["FinalSD"] = math.sqrt(rows["openvla7b_spatial_jpeg_off"]["flips"])
X["FinalBandEp"] = Z * X["FinalSD"]
pmap = {"openvla_reference": "openvla7b_spatial_reference", "openvla_rerun": "openvla7b_spatial_rerun",
        "openvla_jpeg_off": "openvla7b_spatial_jpeg_off", "openvla_crop_off": "openvla7b_spatial_crop_off",
        "oft_reference": "oft_spatial_reference", "oft_rerun": "oft_spatial_rerun", "oft_jpeg_off": "oft_spatial_jpeg_off"}
pdiff = {}
for pc, fc in pmap.items():
    pdiff[pc] = sum(pil[pc][(t, s)] != S[fc][t * 50 + s] for t in range(10) for s in range(20))
X["PilotMaxDiffVsFinal"] = max(pdiff.values())
X["PilotCellsN"] = len(pil)
pilot_meta = {c.name: json.load(open(c / "run_meta.json")) for c in sorted(PIL.iterdir()) if (c / "run_meta.json").exists()}

# ------------------------------------------------------------------ open-loop summary against the closed loop
OL = json.load(open(RES / "open_loop" / "summary.json"))
if OL != json.load(open(PAPER / "data" / "open_loop" / "summary.json")):
    note("open-loop summary.json differs between results/ and paper/data/")
olchk = []
for model, pre in (("openvla7b", "Sev"), ("oft", "Oft")):
    for mode, mm in (("first", "First"), ("traj", "Traj")):
        s = OL[f"{model}/{mode}"]
        X[f"Ol{pre}{mm}N"], X[f"Ol{pre}{mm}Episodes"] = s["n"], s["episodes"]
        for v, vm in (("reference_again", "Again"), ("jpeg_off", "Jpeg"), ("crop_off", "Crop"), ("bilinear", "Bil"),
                      ("render224", "Rend")):
            X[f"Ol{pre}{mm}{vm}Changed"] = round(100 * s[v]["changed"])
            X[f"Ol{pre}{mm}{vm}Mean"] = r1(s[v]["mean"])
            cnt = s[v]["changed"] * s["n"]
            if abs(cnt - round(cnt)) > 1e-6:
                note(f"open loop {model}/{mode}/{v}: changed share x n is not a whole number ({cnt:.4f})")
        if "repro" in s:
            X[f"Ol{pre}{mm}Repro"], X[f"Ol{pre}{mm}ReproN"] = s["repro"]
        if mode == "first" and "flip_link" in s:
            for v, vm in (("jpeg_off", "Jpeg"), ("crop_off", "Crop"), ("bilinear", "Bil"), ("render224", "Rend")):
                pc_, ps_, nch = s["flip_link"][v][:3]
                flips_from_ol = pc_ * nch + (0 if ps_ is None else ps_ * (500 - nch))
                closed = rows[f"{model}_spatial_{v}"]["flips"]
                olchk.append((f"{model} {v}", nch, round(flips_from_ol, 6), closed))
                if abs(flips_from_ol - closed) > 1e-6:
                    note(f"open loop {model} {v}: flips implied by flip_link {flips_from_ol:.3f} != closed loop {closed}")

# ------------------------------------------------------------------ compare with numbers.tex
TEX = {}
for m in re.finditer(r"\\newcommand\{\\(\w+)\}\{(.*)\}\s*$", (PAPER / "generated" / "numbers.tex").read_text(), re.M):
    TEX[m.group(1)] = m.group(2).replace("$-$", "-").replace(",", "")


def fmt(x, nd=1, sign=False):
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    y = round(float(x), nd) if nd != 1 else r1(float(x))
    if y == 0:
        y = 0.0
    s = f"{y:+.{nd}f}" if sign else f"{y:.{nd}f}"
    return "0.0" if sign and y == 0 and nd == 1 else s


def pfmt(p):
    if p >= 0.995:
        return "1.00"
    if p < 0.01:
        return f"{p:.3f}" if p >= 0.001 else f"{p:.1e}"
    return f"{p:.2f}" if p >= 0.1 else f"{p:.3f}"


table = []


def cmp(name, ours, extra=""):
    theirs = TEX.get(name)
    ok = theirs is not None and theirs == ours
    if not ok and theirs is not None:
        try:
            ok = abs(float(theirs) - float(ours)) < 1e-9
        except ValueError:
            pass
    table.append((name, theirs, ours, "match" if ok else ("absent" if theirs is None else "DIFFERS"), extra))


for model in ["openvla7b", "oft"]:
    pre = MAC[model]
    k = int(S[f"{model}_spatial_reference"].sum())
    cmp(f"{pre}RefK", str(k))
    cmp(f"{pre}RefPct", fmt(k / 5))
    lo_, hi_ = wilson(k, 500)
    cmp(f"{pre}RefLo", fmt(lo_)); cmp(f"{pre}RefHi", fmt(hi_))
    for v in ["rerun"] + VARIANTS:
        c, vm = f"{model}_spatial_{v}", VMAC[v]
        R = rows[c]
        b = f"{pre}{vm}"
        cmp(b + "K", str(R["k"])); cmp(b + "Pct", fmt(R["pct"]))
        cmp(b + "Diff", fmt(R["diff"], sign=True) if R["diff"] != 0 else "0.0")
        for key, ex, edge, mc in (("Lo", R["ex_lo"], R["edge_lo"], R["mc_lo"]), ("Hi", R["ex_hi"], R["edge_hi"], R["mc_hi"])):
            ours = fmt(ex, sign=True) if ex != 0 else "0.0"
            cmp(b + key, ours, ("edge; 20,000 draws give " + " or ".join(f"{m:+.1f}" for m in mc)) if edge or len(mc) > 1 else "")
        cmp(b + "UB", fmt(R["ex_ub"]), ("edge; 20,000 draws give " + " or ".join(f"{m:.1f}" for m in R["mc_ub"])) if R["edge_ub"] or len(R["mc_ub"]) > 1 else "")
        cmp(b + "Lost", str(R["lost"])); cmp(b + "Gained", str(R["gained"])); cmp(b + "Flips", str(R["flips"]))
        cmp(b + "P", pfmt(R["p"])); cmp(b + "Band", fmt(R["band"])); cmp(b + "FlipPct", fmt(R["flips"] / 5))
        if "holm" in R:
            cmp(b + "Holm", pfmt(R["holm"]))
    vs = [rows[f"{model}_spatial_{v}"] for v in VARIANTS]
    cmp(f"{pre}FlipsMin", str(min(r["flips"] for r in vs))); cmp(f"{pre}FlipsMax", str(max(r["flips"] for r in vs)))
    cmp(f"{pre}BandMin", fmt(min(r["band"] for r in vs))); cmp(f"{pre}BandMax", fmt(max(r["band"] for r in vs)))
    cmp(f"{pre}VarMinPct", fmt(min(r["pct"] for r in vs))); cmp(f"{pre}VarMaxPct", fmt(max(r["pct"] for r in vs)))
cmp("CpuCtrlP", pfmt(cc["p"]))
SIGNED = {"PilotDiff", "AblUnpairedLo", "AblUnpairedHi", "AblPairedLo", "AblPairedHi", "AblFirstDiff", "AblFirstLo",
          "AblFirstHi", "AblLooMin", "AblLooMax"}
for name, val in X.items():
    if name in SIGNED:
        cmp(name, fmt(val, sign=True))
        continue
    if name == "PilotCellsN" or name.startswith("OftCropVsBilP"):
        continue
    if name in ("OftCropNoFiveP", "SevVVpMin"):
        cmp(name, pfmt(val))
        continue
    if isinstance(val, float) and not float(val).is_integer() or name in ("PilotDisc", "PilotDiff", "PilotF", "PilotSD", "PilotBandEp", "PilotBandPts", "FinalSD", "FinalBandEp"):
        ours = fmt(val, sign=(name in SIGNED))
    else:
        ours = str(int(val)) if float(val).is_integer() else fmt(val)
    cmp(name, ours)
cmp("OftCropVsBilP", pfmt(X["OftCropVsBilP"]))
cmp("AblPairedW", fmt(X["AblPairedHi"] - X["AblPairedLo"]))
cmp("AblUnpairedW", fmt(X["AblUnpairedHi"] - X["AblUnpairedLo"]))
cmp("AblFirstW", fmt(X["AblFirstHi"] - X["AblFirstLo"]))
cmp("PilotCells", {7: "seven"}.get(X["PilotCellsN"], str(X["PilotCellsN"])))

# ------------------------------------------------------------------ report
lines = ["# Independent recheck of the paper numbers", "",
         f"numpy {np.__version__}, scipy {__import__('scipy').__version__}, Python {sys.version.split()[0]}", ""]
lines += ["## Data checks", ""]
lines += [f"- Initial-state hashes against the OpenVLA-7B reference cell: " +
          ", ".join(f"{c} {h}" for c, h in hash_match.items())]
lines += ["- OpenVLA-OFT reference: the original script logs carry no hash; its pairs are keyed by task line and episode "
          "counter (states 20-49: counter + 20). The rerun repeats all 500 outcomes of it, including the "
          f"{500 - int(S['oft_spatial_reference'].sum())} failures."]
lines += [f"- Problems found by the loaders: {len(problems)}"] + [f"  - {p}" for p in problems]
lines += ["", "## Closed loop against the reference cell", "",
          "| Cell | Success | Wilson 95% | Diff | Exact boot 95% | MC boot 95% (100 seeds) | UB loss | Lost/gained | McNemar p | Holm p | Band |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
for c, R in rows.items():
    lines.append(f"| {c} | {R['k']}/500 | [{R['wilson'][0]:.1f}, {R['wilson'][1]:.1f}] | {R['diff']:+.1f} | "
                 f"[{R['ex_lo']:+.1f}{'*' if R['edge_lo'] else ''}, {R['ex_hi']:+.1f}{'*' if R['edge_hi'] else ''}] | "
                 f"lo {'/'.join(f'{m:+.1f}' for m in R['mc_lo'])}, hi {'/'.join(f'{m:+.1f}' for m in R['mc_hi'])} | "
                 f"{R['ex_ub']:.1f}{'*' if R['edge_ub'] else ''} ({'/'.join(f'{m:.1f}' for m in R['mc_ub'])}) | "
                 f"{R['lost']}/{R['gained']} | {R['p']:.4g} | {R.get('holm', float('nan')):.4g} | {R['band']:.2f} |")
lines += ["", "`*`: edge, the exact cumulative probability is within 0.004 of the target quantile, so the Monte Carlo value"
          " depends on the seed.", "", "## Open loop: flips implied by the summary against the closed-loop cells", "",
          "| Model, step | First actions changed | Flips implied | Closed-loop flips |", "|---|---|---|---|"]
lines += [f"| {a} | {b} | {c:g} | {d} |" for a, b, c, d in olchk]
lines += ["", "## Pilot", "", "| Pilot cell | Started | JPEG | Center crop | Differs from the full cell on states 0-19 |",
          "|---|---|---|---|---|"]
for c, m in pilot_meta.items():
    ip = m.get("image_pipeline", {})
    lines.append(f"| {c} | {m.get('start_time')} | {ip.get('jpeg_roundtrip')} | {ip.get('center_crop')} | {pdiff.get(c)} |")
lines += ["", "## Every macro compared", "", "| Macro | numbers.tex | Recomputed | Result | Note |", "|---|---|---|---|---|"]
lines += [f"| {a} | {b} | {c} | {d} | {e} |" for a, b, c, d, e in table]
n_ok = sum(t[3] == "match" for t in table)
n_bad = [t for t in table if t[3] != "match"]
lines += ["", f"{n_ok} of {len(table)} macros match; {len(n_bad)} differ or are absent."]
(ROOT / "audit" / "recheck_report.md").write_text("\n".join(lines) + "\n")
json.dump({"rows": rows, "extra": X, "compare": table, "problems": problems, "hashes": hash_match},
          open(ROOT / "audit" / "recheck.json", "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print(f"{n_ok} of {len(table)} macros match; {len(n_bad)} differ or are absent; {len(problems)} data problems")
for t in n_bad:
    print("  ", t)
for t in table:
    if t[4]:
        print("  edge:", t[0], t[1], t[2], t[4])
