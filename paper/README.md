# Paper source

LaTeX source of "Per-Step Effects of Evaluation Image Preprocessing on Two OpenVLA Policies in LIBERO-Spatial", in the official TMLR template (`tmlr.sty`, `tmlr.bst` and `fancyhdr.sty`, unchanged from github.com/JmlrOrg/tmlr-style-file).

## Build

```bash
cd paper
python3 scripts/make_assets.py .. .     # figures/*.pdf and generated/*.tex from the result files of this repository
python3 scripts/check_numbers.py .      # fails if the text holds a number that does not come from generated/numbers.tex
latexmk -pdf main.tex                   # anonymous submission build
latexmk -pdf preprint.tex               # preprint build (author named, from author_preprint.tex)
```

`make_assets.py` needs Python 3 with numpy, matplotlib and Pillow, and runs in a few seconds on a CPU.

## Where every number comes from

`generated/*.tex` and `figures/*.pdf` are written by `scripts/make_assets.py`; do not edit them by hand. Every number in the text is a macro of `generated/numbers.tex`, and `scripts/check_numbers.py` reports any digit left in the text.

Inputs:

- `../results/`: the twelve cells of 500 paired episodes, read directly and through `../scripts/paired_stats.py` and `../scripts/post_lock_checks.py` (the main table is parsed from the output of `paired_stats.py`, so the paper and the repository show the same numbers).
- `data/pilot_states_0-19/`: the pilot cells (initial states 0-19).
- `data/vla_eval_export/`: the per-episode results of OpenVLA on LIBERO-Spatial published by vla-eval (commit in `source_commit.txt`).
- `data/mujoco_versions/`: the reproduction runs under MuJoCo 3.3.7 and 3.13 cited in the introduction.
- `data/external_numbers.json`: numbers quoted from other work, each with its citation key and its place in the source.
- `data/open_loop/summary.json`: summary of the open-loop action check, written by `../scripts/summarize_open_loop.py`.
- `eda/frames.jsonl`: image-level measurements, written by `scripts/eda_frames.py` on CPU-rendered LIBERO frames.
- `example_frames/`: the frames of the pipeline figure, rendered on CPU by `scripts/render_example_frames.py`.
- `scripts/power.py`: exact McNemar power used by the decision rule.

A rerun of the OpenVLA-OFT crop-off cell on the host CPU of the other OpenVLA-OFT cells goes to `../results/oft_spatial_crop_off_cpu_control/` (`states_0-19/` and `states_20-49/`); `make_assets.py` then writes its macros (`CpuCtrl*`).

## Control cells (sham control, render-at-224 CPU control)

The cells of `../controls/PLAN.md` go to `../results/controls/`, and their pre-registered reading, by `../scripts/sham_control_analysis.py --json`, to `../results/controls/summary.json`. When that file exists, `make_assets.py` writes the control macros (`Sham*`, `CpuSevCtrl*`, `Stack*`), `generated/table_controls.tex` and, for CPU reading (b), `generated/table_results_cpub.tex`; until then the macros hold placeholders and the build is unchanged. If the folder holds cells but no `summary.json`, `make_assets.py` runs the analysis script itself.

`sections/hooks.tex` holds every sentence that the control results replace or add, as it stands before them. `sections/controls_results.tex` redefines those sentences with the text fixed in section 6 of the plan (fragility branch or step-specific branch, set by `\ShamBranch`) and section 7 (CPU readings (a) and (b), set by `\CpuSevCtrlReading`). It is switched on by uncommenting `\input{sections/controls_results}` in `main.tex`.
