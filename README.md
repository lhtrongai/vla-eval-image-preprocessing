# Does each evaluation image step change OpenVLA and OpenVLA-OFT success on LIBERO-Spatial?

Before a vision-language-action (VLA) policy sees a camera frame, the evaluation code processes it with steps copied from how the training data were built. In the official OpenVLA and OpenVLA-OFT LIBERO evaluations these are a JPEG round trip (encode, decode), a Lanczos resize with antialiasing and a center crop of 90% of the image area, on cameras rendered at 256x256. Every new evaluation harness re-implements these steps, and a step that is dropped or changed raises no error, it only gives a different number.

This repository changes one step at a time and measures the effect on closed-loop success, on paired episodes that start from the same LIBERO initial states.

## Setup

- **Models:** OpenVLA-7B ([`openvla/openvla-7b-finetuned-libero-spatial`](https://huggingface.co/openvla/openvla-7b-finetuned-libero-spatial), sdpa attention) and OpenVLA-OFT ([`moojink/openvla-7b-oft-finetuned-libero-spatial`](https://huggingface.co/moojink/openvla-7b-oft-finetuned-libero-spatial)). Both were fine-tuned with random crops of 90% of the image area, and both evaluation scripts take the matching center crop.
- **Episodes:** LIBERO-Spatial, 10 tasks x the 50 stored initial states, 500 episodes per cell. Every cell is paired with its model's reference cell by (task, initial state). In every harness cell the logged initial-state hash matches the LIBERO init file in all 500 pairs; the OpenVLA-OFT reference cell ran with the original script, which logs no hash.
- **Cells** (one step changed per cell):

| Cell | What changes |
|---|---|
| `reference` | The original evaluation script, unchanged. |
| `jpeg_off` | The JPEG round trip is skipped; the resize is otherwise identical. |
| `crop_off` | The center crop is skipped (the evaluation script's own `--center_crop False`). |
| `bilinear` | The Lanczos resize is replaced by bilinear (JPEG round trip and antialiasing kept). |
| `render224` | The cameras render at 224x224 instead of 256x256. |
| `rerun` | The reference repeated unchanged, to measure the run-to-run noise floor. |

- **Analysis written down before the full variant cells:** the primary comparison is the JPEG round trip off on OpenVLA-7B, with 3 points as the smallest loss that matters. A pilot on initial states 0-19 (12 October 2026, seven cells of 200 episodes, among them JPEG off for both models and crop off for OpenVLA-7B; records in `paper/data/pilot_states_0-19/`) found 17.5% of episodes changing outcome, so the rule reports the one-sided 95% upper bound on the loss at 500 pairs. Because the pilot already ran two variant steps, the plan precedes the 500-episode cells, not every variant run; it was not committed to a public repository at the time. The other seven variant comparisons are secondary, Holm-adjusted.
- **Stack:** MuJoCo 3.3.7, robosuite 1.4.1, torch 2.8.0+cu128, one NVIDIA RTX PRO 4500 (32 GB) per cell, 220 policy steps plus 10 settle steps per episode.

## Results

Difference to the model's reference cell, in points, with a 95% paired bootstrap interval over episodes (percentiles computed exactly, no random draws; see `scripts/exact_bootstrap.py`):

| Cell | OpenVLA-7B | OpenVLA-OFT |
|---|---|---|
| reference success | 425/500 = 85.0% | 495/500 = 99.0% |
| `jpeg_off` | -0.8 [-4.2, +2.6] (primary) | -0.8 [-2.0, +0.4] |
| `crop_off` | -1.0 [-4.6, +2.6] | -2.4 [-4.2, -0.8], Holm p = 0.053 |
| `bilinear` | -2.2 [-5.8, +1.4] | +0.2 [-0.8, +1.2] |
| `render224` | +0.4 [-3.4, +4.2] | -0.8 [-2.0, +0.4] |
| `rerun` | -0.2 (3 of 500 episodes change) | 0.0 (no episode changes) |

- **Primary result.** Turning the JPEG round trip off changes OpenVLA-7B by -0.8 points, with a one-sided 95% upper bound of 3.6 points on the loss. The bound is above the 3 points fixed beforehand, so a 3-point loss is not ruled out: the result does not show that the JPEG step can be skipped.
- **No secondary comparison passes 0.05 after Holm correction.** The closest, the center crop on OpenVLA-OFT, rests mostly on one task: 9 of its 15 lost episodes are in task 5 (black bowl on the ramekin); without task 5 it loses 6 and gains 2 (McNemar p = 0.29).
- **Small net effects, many flips.** Every OpenVLA-7B variant changes the outcome of 74-92 of 500 episodes, in both directions, while the identical rerun changes 3. Different variants flip overlapping sets of fragile episodes (1.2 to 1.5 times the overlap expected by chance given each episode's task and reference outcome), so the flips do not belong to one image step. For OpenVLA-7B, almost every trajectory changes under any variant: among episodes that succeed in both, only 3-5% succeed at the same step.
- **Consequence for comparing scores.** Given its number of flips, a pipeline change with no systematic effect still moves a 500-episode LIBERO-Spatial score within about ±3.4 to ±3.8 points (95%) for OpenVLA-7B and ±1.0 to ±1.7 for OpenVLA-OFT. Score gaps of that size between two evaluation pipelines are not evidence that the pipelines differ.
- The center-crop cost on OpenVLA-7B (-1.0 points, upper bound 4.0 on the loss) is consistent with the about 3 points reported by the [vla-evaluation-harness](https://github.com/allenai/vla-evaluation-harness) over four suites, but not distinguishable from zero here.

Full table (Wilson intervals, lost and gained episodes, McNemar and Holm p-values, flips per task) and the reading: [`results/summary.md`](results/summary.md). The exploratory checks made after the results were fixed (fragile episodes, overlap of flips, step budget, trajectory divergence) are at the end of that file.

**Scope.** One suite, in simulation; two released checkpoints; one GPU type. The intervals cover these 500 (task, initial state) pairs, not other tasks or suites.

## Reproduce the analysis (CPU, a few seconds)

Requires Python 3 and numpy. Checked with Python 3.13.18 and numpy 2.5.3, and with numpy 2.1.3 (same output). The paper assets (`paper/scripts/make_assets.py`) also need matplotlib (checked with 3.11.2) and Pillow (12.3.0); the independent recheck needs scipy (1.18.1).

```bash
python scripts/paired_stats.py      # the table in results/summary.md
python scripts/post_lock_checks.py  # every number in the exploratory section
python -I audit/independent_recheck.py   # recompute every number from the per-episode files and compare with paper/generated/numbers.tex
```

The bootstrap intervals and upper bounds are computed exactly from the multinomial distribution of resampled lost and gained pairs (`scripts/exact_bootstrap.py`), not from random draws. An earlier version drew 20,000 resamples per cell from one shared random stream, in the order the cell folders sort; adding a cell folder (the CPU control) shifted the draws of every later cell and moved interval ends that lie close to a percentile boundary by one episode (0.2 points). The exact computation gives the same numbers on every machine and with every numpy version. `audit/independent_recheck.py` is written separately from the analysis scripts and checks every closed-loop number, the pilot and the open-loop summary against `paper/generated/numbers.tex` (report: `audit/recheck_report.md`).

## Rerun the evaluation (GPU)

The evaluation runs on top of [libero-vla-eval](https://github.com/lhtrongai/libero-vla-eval), which holds the environment (exact package versions, setup scripts, the OpenVLA and OpenVLA-OFT commits) and the per-episode logging shared by these runs. Set up as described in its README (section on the original OpenVLA and OpenVLA-OFT scripts), then:

1. Copy `libero-vla-eval/scripts/` to a working folder and copy this repository's `scripts/*.py` over it. `image_pipeline.py` and the two runners here are the libero-vla-eval files with the `IMAGE_VARIANT` switch (`bilinear`, `render224`, and the sham controls `jpeg_q94` and `noise`) added, and the OpenVLA-OFT runner also takes `INIT_OFFSET` (start at a later stored initial state); `check_image_variants.py` is new. The runners import `episode_logging.py` and `per_camera_textures.py` from libero-vla-eval.
2. Check the image code on the machine before any variant cell: `python check_image_variants.py openvla` (or `oft`) must print `CHECK_OK` (the rewritten resize must reproduce the official step pixel for pixel).
3. Run a cell. For example, OpenVLA-7B with the JPEG round trip off, and OpenVLA-OFT with the bilinear resize:

```bash
OUT_DIR=runs/openvla7b_spatial_jpeg_off JPEG_ROUNDTRIP=off \
python run_openvla_libero_logged.py --model_family openvla \
  --pretrained_checkpoint openvla/openvla-7b-finetuned-libero-spatial \
  --task_suite_name libero_spatial --center_crop True --num_trials_per_task 50 --seed 7

# OpenVLA-OFT runs as two segments, initial states 0-19 and 20-49, like its reference cell
IMAGE_VARIANT=bilinear OUT_DIR=runs/oft_spatial_bilinear/states_0-19 \
python run_oft_libero_logged.py --pretrained_checkpoint moojink/openvla-7b-oft-finetuned-libero-spatial \
  --task_suite_name libero_spatial --center_crop True --num_trials_per_task 20 --env_img_res 256 \
  --local_log_dir runs/oft_spatial_bilinear/states_0-19
IMAGE_VARIANT=bilinear INIT_OFFSET=20 OUT_DIR=runs/oft_spatial_bilinear/states_20-49 \
python run_oft_libero_logged.py --pretrained_checkpoint moojink/openvla-7b-oft-finetuned-libero-spatial \
  --task_suite_name libero_spatial --center_crop True --num_trials_per_task 30 --env_img_res 256 \
  --local_log_dir runs/oft_spatial_bilinear/states_20-49
```

`--center_crop False` gives `crop_off`; `IMAGE_VARIANT=render224` needs `--env_img_res 224` for OpenVLA-OFT. Keep the OFT 0-19 / 20-49 split to reproduce the same scenes: LIBERO redraws the cabinet and stove placement at every reset, and on some tasks that placement depends on how many resets the environment has done. The exact command of every cell is in its `run_meta.json` (`argv`).

`scripts/run/` holds the scripts that ran one cell per cloud GPU instance (setup, run, watchdog). They assume the folder layout of that machine (`/workspace/...`) and are kept as a record of how the cells were run, not as a general launcher.

## Open-loop action check (exploratory)

Closed-loop success flips once trajectories diverge, so it cannot show what a step does to the policy itself. `scripts/open_loop_actions.py` gives each policy identical observations through every pipeline (reference, the same input again, `jpeg_off`, `crop_off`, `bilinear`, `render224`) and records the predicted actions; only the reference action is executed. Observations: the first frame of all 500 initial states, and frames along the reference rollouts (OpenVLA-7B: every fourth query of initial states 0-4; OpenVLA-OFT: every query of initial states 0-9). The 224 frame comes from a second environment that gets the same actions and the same random draw for the fixture placement. Run on 1-2 November 2026 on one RTX PRO 4500; the run log is `results/open_loop/chain.log`.

Both models are measured in OpenVLA-7B action bins (each dimension scaled to [-1, 1] by the 1st and 99th percentiles of the training actions, 256 bins; OpenVLA-OFT: mean over its chunk of 8 actions). Arm dimensions only. Share of observations whose arm action changes / mean change in bins (`results/open_loop/summary.json`, written by `scripts/summarize_open_loop.py`):

| Pipeline | OpenVLA-7B, first frames (500) | OpenVLA-7B, along rollouts (1713) | OpenVLA-OFT, first frames (500) | OpenVLA-OFT, along rollouts (1326) |
|---|---|---|---|---|
| same input again | 0% / 0.0 | 0% / 0.0 | 0% / 0.0 | 0% / 0.0 |
| `jpeg_off` | 29% / 3.3 | 35% / 4.1 | 99% / 0.9 | 84% / 0.5 |
| `crop_off` | 95% / 14.4 | 91% / 14.0 | 100% / 10.1 | 100% / 5.6 |
| `bilinear` | 54% / 6.9 | 55% / 7.0 | 100% / 2.4 | 97% / 0.9 |
| `render224` | 78% / 11.8 | 66% / 8.6 | 100% / 1.3 | 97% / 0.8 |

For OpenVLA-OFT a change above half a bin counts. The reference rollouts repeat the closed-loop cells (outcome and final step) in 50 of 50 OpenVLA-7B and 99 of 100 OpenVLA-OFT episodes.

- Every step changes the output. OpenVLA-7B switches between distant action bins; OpenVLA-OFT shifts by about one bin or less under the three mild steps, and by about ten bins without the crop, the one step with a candidate closed-loop effect on it.
- Near-tied OpenVLA-7B tokens (top-1 minus top-2 logit below 2) are changed by at least one variant in 93% of first frames, confident ones (8 or more) in 65%.
- A changed first action does not predict a flip: with JPEG off, 14% of the episodes whose first OpenVLA-7B action changed flip in the closed loop, against 15% of the others.

The per-observation records (`actions_*.jsonl`) stay on the run volume; `python scripts/analyze_open_loop.py <dir> results` and `python scripts/summarize_open_loop.py <dir> results` recompute the tables from them.

## Sham and CPU controls (plan fixed before the runs)

The identical rerun shows that the variants cause the flips, not that the flips are specific to the image steps. `controls/PLAN.md` adds sham cells: meaningless changes as large, in intensity levels, as the two mildest steps (noise of exactly one intensity level on every policy input, two draws; the JPEG round trip at quality 94 instead of 95), three per model, plus a rerun of the OpenVLA-7B render-at-224 cell on the host CPU of the other OpenVLA-7B cells and an OpenVLA-OFT stack check. The plan fixes the question, the comparison, the reading rule in numbers, the validity checks and the text of the paper for each outcome, and it was committed with the code and the analysis script (`scripts/sham_control_analysis.py`) before any of these cells ran. How to run them: `controls/RUN_GUIDE.md`; timeline of the plan and the runs: `PROVENANCE.md`.

Results (`results/controls/summary.md`, read once with the pre-registered rule). The rule divides the mean flips of the three sham cells by the mean flips of the two steps they are sized to (JPEG off and bilinear), both above the identical rerun, and calls the sham flips many at a ratio of one half or more.

| | Sham flips (noise draw 1, draw 2, JPEG q94) | Ratio [bootstrap 95%] |
|---|---|---|
| OpenVLA-7B | 61, 83, 78 | 0.94 [0.81, 1.10] |
| OpenVLA-OFT | 4, 7, 5 | 0.63 [0.30, 1.04], close to the cutoff |

For OpenVLA-7B, most flips of the mild steps therefore reflect sensitivity to any change of about one intensity level, not an effect of the particular step. For OpenVLA-OFT the counts are small, and its steps, the crop above all, lose episodes the shams do not. The render-at-224 rerun on the other host CPU repeats all 500 outcomes of the October cell, and the OpenVLA-OFT stack check repeats all 500 outcomes of the October reference.

## Repository layout

| Path | Contents |
|---|---|
| `scripts/image_pipeline.py` | The evaluation image steps, switchable one at a time (`JPEG_ROUNDTRIP`, `IMAGE_VARIANT`), the two sham controls (`IMAGE_VARIANT=jpeg_q94`, `IMAGE_VARIANT=noise` with `NOISE_SEED`), and helpers that record what the policy saw. |
| `scripts/run_openvla_libero_logged.py`, `scripts/run_oft_libero_logged.py` | Run the original OpenVLA or OpenVLA-OFT evaluation script unchanged and append one record per episode (initial-state hash checked against the LIBERO init file, fixture placement, first-frame hashes, input-image differences). |
| `scripts/check_image_variants.py` | Pre-run check of the image code against the official step. |
| `scripts/paired_stats.py` | Paired statistics of every cell against its reference cell. |
| `scripts/post_lock_checks.py` | Exploratory checks made after the results were fixed. |
| `results/<model>_spatial_<cell>/` | Per-episode records (`episodes.jsonl`) and run metadata (`run_meta.json`) of each cell. The OpenVLA-OFT reference cell holds the logs of the original script instead. |
| `results/summary.md` | Output of `paired_stats.py` with the reading of the results. |
| `scripts/exact_bootstrap.py` | Exact percentile bootstrap for 0/1 outcomes (paired and unpaired), used by the analysis and the paper assets. |
| `audit/` | Independent recheck of every number of the paper from the per-episode files, and its report. |
| `scripts/open_loop_actions.py`, `scripts/analyze_open_loop.py`, `scripts/summarize_open_loop.py` | Open-loop action check: query every pipeline on identical observations, then summarize. |
| `results/open_loop/` | Summary of the open-loop check (`summary.json`) and its run log. |
| `controls/` | Plan of the sham and CPU controls (`PLAN.md`), the cells (`cells.json`), the code hashes they must run with, the pod scripts and the run guide. |
| `scripts/sham_control_analysis.py` | Checks the control cells and applies the reading rule of `controls/PLAN.md`. |

## License

The code in this repository is under the MIT license (see `LICENSE`). OpenVLA, OpenVLA-OFT, their checkpoints and LIBERO are not included and keep their own licenses.
