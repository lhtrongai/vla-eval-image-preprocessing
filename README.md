# Does each evaluation image step change OpenVLA and OpenVLA-OFT success on LIBERO-Spatial?

Before a vision-language-action (VLA) policy sees a camera frame, the evaluation code processes it with steps copied from how the training data were built. In the official OpenVLA and OpenVLA-OFT LIBERO evaluations these are a JPEG round trip (encode, decode), a Lanczos resize with antialiasing and a center crop of 90% of the image area, on cameras rendered at 256x256. Every new evaluation harness re-implements these steps, and a step that is dropped or changed raises no error, it only gives a different number.

This repository changes one step at a time and measures the effect on closed-loop success, on paired episodes that start from the same LIBERO initial states.

## Setup

- **Models:** OpenVLA-7B ([`openvla/openvla-7b-finetuned-libero-spatial`](https://huggingface.co/openvla/openvla-7b-finetuned-libero-spatial), sdpa attention) and OpenVLA-OFT ([`moojink/openvla-7b-oft-finetuned-libero-spatial`](https://huggingface.co/moojink/openvla-7b-oft-finetuned-libero-spatial)). Both were fine-tuned with random crops of 90% of the image area, and both evaluation scripts take the matching center crop.
- **Episodes:** LIBERO-Spatial, 10 tasks x the 50 stored initial states, 500 episodes per cell. Every cell is paired with its model's reference cell by (task, initial state); the initial-state hashes match the reference in all 500 pairs of every cell.
- **Cells** (one step changed per cell):

| Cell | What changes |
|---|---|
| `reference` | The original evaluation script, unchanged. |
| `jpeg_off` | The JPEG round trip is skipped; the resize is otherwise identical. |
| `crop_off` | The center crop is skipped (the evaluation script's own `--center_crop False`). |
| `bilinear` | The Lanczos resize is replaced by bilinear (JPEG round trip and antialiasing kept). |
| `render224` | The cameras render at 224x224 instead of 256x256. |
| `rerun` | The reference repeated unchanged, to measure the run-to-run noise floor. |

- **Analysis fixed before the variant runs:** the primary comparison is the JPEG round trip off on OpenVLA-7B, with 3 points as the smallest loss that matters. A pilot on initial states 0-19 found 17.5% of episodes changing outcome, so the rule reports the one-sided 95% upper bound on the loss at 500 pairs. The other seven variant comparisons are secondary, Holm-adjusted.
- **Stack:** MuJoCo 3.3.7, robosuite 1.4.1, torch 2.8.0+cu128, one NVIDIA RTX PRO 4500 (32 GB) per cell, 220 policy steps plus 10 settle steps per episode.

## Results

Difference to the model's reference cell, in points, with a 95% paired bootstrap interval (20,000 draws over paired episodes):

| Cell | OpenVLA-7B | OpenVLA-OFT |
|---|---|---|
| reference success | 425/500 = 85.0% | 495/500 = 99.0% |
| `jpeg_off` | -0.8 [-4.2, +2.6] (primary) | -0.8 [-2.0, +0.4] |
| `crop_off` | -1.0 [-4.6, +2.6] | -2.4 [-4.0, -0.8], Holm p = 0.053 |
| `bilinear` | -2.2 [-5.8, +1.4] | +0.2 [-0.8, +1.2] |
| `render224` | +0.4 [-3.4, +4.2] | -0.8 [-2.0, +0.4] |
| `rerun` | -0.2 (3 of 500 episodes change) | 0.0 (no episode changes) |

- **Primary result.** Turning the JPEG round trip off changes OpenVLA-7B by -0.8 points, with a one-sided 95% upper bound of 3.6 points on the loss. The bound is above the 3 points fixed beforehand, so a 3-point loss is not ruled out: the result does not show that the JPEG step can be skipped.
- **No secondary comparison passes 0.05 after Holm correction.** The closest, the center crop on OpenVLA-OFT, rests mostly on one task: 9 of its 15 lost episodes are in task 5 (black bowl on the ramekin); without task 5 it loses 6 and gains 2 (McNemar p = 0.29).
- **Small net effects, many flips.** Every OpenVLA-7B variant changes the outcome of 74-92 of 500 episodes, in both directions, while the identical rerun changes 3. Different variants flip largely the same fragile episodes (2.5-3 times as often as chance), so the flips do not belong to one image step. For OpenVLA-7B, almost every trajectory changes under any variant: among episodes that succeed in both, only 3-5% succeed at the same step.
- **Consequence for comparing scores.** Given its number of flips, a pipeline change with no systematic effect still moves a 500-episode LIBERO-Spatial score within about ±3.4 to ±3.8 points (95%) for OpenVLA-7B and ±1.0 to ±1.7 for OpenVLA-OFT. Score gaps of that size between two evaluation pipelines are not evidence that the pipelines differ.
- The center-crop cost on OpenVLA-7B (-1.0 points, upper bound 4.0 on the loss) is consistent with the about 3 points reported by the [vla-evaluation-harness](https://github.com/allenai/vla-evaluation-harness) over four suites, but not distinguishable from zero here.

Full table (Wilson intervals, lost and gained episodes, McNemar and Holm p-values, flips per task) and the reading: [`results/summary.md`](results/summary.md). The exploratory checks made after the results were fixed (fragile episodes, overlap of flips, step budget, trajectory divergence) are at the end of that file.

**Scope.** One suite, in simulation; two released checkpoints; one GPU type. The intervals cover these 500 (task, initial state) pairs, not other tasks or suites.

## Reproduce the analysis (CPU, a few seconds)

Requires Python 3 and numpy.

```bash
python scripts/paired_stats.py      # the table in results/summary.md
python scripts/post_lock_checks.py  # every number in the exploratory section
```

## Rerun the evaluation (GPU)

The evaluation runs on top of [libero-vla-eval](https://github.com/lhtrongai/libero-vla-eval), which holds the environment (exact package versions, setup scripts, the OpenVLA and OpenVLA-OFT commits) and the per-episode logging shared by these runs. Set up as described in its README (section on the original OpenVLA and OpenVLA-OFT scripts), then:

1. Copy `libero-vla-eval/scripts/` to a working folder and copy this repository's `scripts/*.py` over it. `image_pipeline.py` and the two runners here are the libero-vla-eval files with the `IMAGE_VARIANT` switch (`bilinear`, `render224`) added, and the OpenVLA-OFT runner also takes `INIT_OFFSET` (start at a later stored initial state); `check_image_variants.py` is new. The runners import `episode_logging.py` and `per_camera_textures.py` from libero-vla-eval.
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

## Repository layout

| Path | Contents |
|---|---|
| `scripts/image_pipeline.py` | The evaluation image steps, switchable one at a time (`JPEG_ROUNDTRIP`, `IMAGE_VARIANT`), and helpers that record what the policy saw. |
| `scripts/run_openvla_libero_logged.py`, `scripts/run_oft_libero_logged.py` | Run the original OpenVLA or OpenVLA-OFT evaluation script unchanged and append one record per episode (initial-state hash checked against the LIBERO init file, fixture placement, first-frame hashes, input-image differences). |
| `scripts/check_image_variants.py` | Pre-run check of the image code against the official step. |
| `scripts/paired_stats.py` | Paired statistics of every cell against its reference cell. |
| `scripts/post_lock_checks.py` | Exploratory checks made after the results were fixed. |
| `results/<model>_spatial_<cell>/` | Per-episode records (`episodes.jsonl`) and run metadata (`run_meta.json`) of each cell. The OpenVLA-OFT reference cell holds the logs of the original script instead. |
| `results/summary.md` | Output of `paired_stats.py` with the reading of the results. |

## License

The code in this repository is under the MIT license (see `LICENSE`). OpenVLA, OpenVLA-OFT, their checkpoints and LIBERO are not included and keep their own licenses.
