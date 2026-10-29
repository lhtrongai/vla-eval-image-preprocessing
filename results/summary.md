# Image-pipeline cells on LIBERO-Spatial (500 paired episodes per cell)

Every cell changes one step of the evaluation image pipeline and runs the 10 tasks x 50 stored initial states of LIBERO-Spatial. Episodes are paired with the model's reference cell by (task, initial state); the initial-state hashes match the reference in all 500 pairs of every cell.

- Models: OpenVLA-7B (`openvla/openvla-7b-finetuned-libero-spatial`, sdpa attention) and OpenVLA-OFT (`moojink/openvla-7b-oft-finetuned-libero-spatial`). Both were fine-tuned with random crops of 90% of the image area, and both evaluation scripts take the matching center crop (OpenVLA README, OpenVLA-OFT LIBERO.md).
- Stack: MuJoCo 3.3.7, robosuite 1.4.1, torch 2.8.0+cu128, one RTX PRO 4500 per cell, step budget 220 policy steps plus 10 settle steps.
- Reference cells: OpenVLA-7B ran on 6 October 2026, OFT on 3 and 5 October 2026 (initial states 0-19 and 20-49, the original evaluation script). Variant cells and the identical reruns ran on 28-29 October 2026, OFT again as two runs (0-19, 20-49).
- Variants: `jpeg_off` skips the JPEG round trip; `crop_off` skips the center crop of the evaluation script; `bilinear` replaces the Lanczos resize with bilinear (JPEG round trip and antialias kept); `render224` renders the cameras at 224x224 instead of 256x256; `rerun` repeats the reference unchanged.
- Primary comparison, fixed before any run: JPEG round trip off on OpenVLA-7B, with 3 points as the smallest loss that matters. A pilot on initial states 0-19 found 17.5% of episodes changing outcome, so the rule fixed beforehand reports the one-sided 95% upper bound on the loss at 500 pairs. The other seven variant comparisons are secondary, Holm-adjusted.

Produced by `python scripts/paired_stats.py` (bootstrap: 20,000 draws over paired episodes, seed 20261029):

| Cell | Success (Wilson 95%) | Difference, points (95% CI) | Lost / gained | McNemar p | Holm p | Upper bound on loss |
|---|---|---|---|---|---|---|
| oft_spatial_bilinear | 496/500 = 99.2% [98.0, 99.7] | +0.2 [-0.8, +1.2] | 3 / 4 | 1 | 1 | 0.6 |
| oft_spatial_crop_off | 483/500 = 96.6% [94.6, 97.9] | -2.4 [-4.0, -0.8] | 15 / 3 | 0.00754 | 0.0528 | 3.8 |
| oft_spatial_jpeg_off | 491/500 = 98.2% [96.6, 99.1] | -0.8 [-2.0, +0.4] | 7 / 3 | 0.344 | 1 | 1.8 |
| oft_spatial_render224 | 491/500 = 98.2% [96.6, 99.1] | -0.8 [-2.0, +0.4] | 7 / 3 | 0.344 | 1 | 1.8 |
| oft_spatial_rerun | 495/500 = 99.0% [97.7, 99.6] | +0.0 [-0.0, -0.0] | 0 / 0 | 1 | - | 0.0 |
| openvla7b_spatial_bilinear | 414/500 = 82.8% [79.2, 85.9] | -2.2 [-5.8, +1.4] | 47 / 36 | 0.272 | 1 | 5.2 |
| openvla7b_spatial_crop_off | 420/500 = 84.0% [80.5, 87.0] | -1.0 [-4.6, +2.6] | 43 / 38 | 0.657 | 1 | 4.0 |
| openvla7b_spatial_jpeg_off | 421/500 = 84.2% [80.7, 87.1] | -0.8 [-4.2, +2.6] | 39 / 35 | 0.728 | - | 3.6 |
| openvla7b_spatial_render224 | 427/500 = 85.4% [82.0, 88.2] | +0.4 [-3.4, +4.2] | 45 / 47 | 0.917 | 1 | 2.8 |
| openvla7b_spatial_rerun | 424/500 = 84.8% [81.4, 87.7] | -0.2 [-1.0, +0.4] | 2 / 1 | 1 | - | 0.8 |

Flips per task:
  oft_spatial_bilinear: [0, 0, 1, 1, 2, 2, 0, 0, 0, 1]
  oft_spatial_crop_off: [0, 2, 1, 2, 0, 10, 0, 1, 0, 2]
  oft_spatial_jpeg_off: [0, 0, 1, 2, 0, 5, 0, 0, 0, 2]
  oft_spatial_render224: [0, 0, 3, 2, 1, 3, 0, 0, 0, 1]
  oft_spatial_rerun: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
  openvla7b_spatial_bilinear: [8, 5, 5, 7, 9, 8, 7, 8, 11, 15]
  openvla7b_spatial_crop_off: [6, 9, 9, 4, 15, 5, 3, 7, 6, 17]
  openvla7b_spatial_jpeg_off: [5, 9, 7, 3, 13, 5, 4, 6, 11, 11]
  openvla7b_spatial_render224: [8, 10, 8, 5, 13, 9, 3, 9, 13, 14]
  openvla7b_spatial_rerun: [0, 2, 0, 0, 0, 0, 0, 1, 0, 0]

Reading:
- Turning the JPEG round trip off changes OpenVLA-7B by -0.8 points, with a one-sided 95% upper bound of 3.6 points on the loss. The bound is above the 3 points fixed beforehand, so a 3-point loss is not ruled out: the result does not show that the JPEG step can be skipped. 74 of 500 episodes change outcome, in both directions (39 lost, 35 gained).
- No secondary comparison passes 0.05 after Holm. The closest is the center crop on OpenVLA-OFT (-2.4 points, Holm p 0.053). 9 of its 15 lost episodes are in task 5 (black bowl on the ramekin), where crop off succeeds in 40 of 50 episodes against 45-48 for the other OFT pipelines; without task 5 it loses 6 and gains 2 (McNemar p 0.29). Turning the crop off is a train/test mismatch for both models, and OpenVLA-7B shows no detectable effect from it.
- The center-crop cost on OpenVLA-7B (-1.0 points, loss interval [-2.6, +4.6], upper bound 4.0) is consistent with the about 3 points reported by vla-eval but not distinguishable from zero.
- Noise floor: the identical rerun changes 3 of 500 OpenVLA-7B episodes (run on another day and pod than the reference) and none of the OFT episodes.

Image steps were checked before the runs on a LIBERO-Spatial frame: the rewritten resize reproduces the official step pixel for pixel; the bilinear variant changes the policy input by 0.76 grey levels on average and rendering at 224 by 1.84 (`scripts/check_image_variants.py`).

## Exploratory checks after the lock

Not registered beforehand, no new runs. `python scripts/post_lock_checks.py` prints every number below.

- Fragile episodes. Over the five OpenVLA-7B pipelines (reference and four variants), 296 episodes always succeed, 15 always fail and 189 (38%) change; 60 of the 75 reference failures succeed under at least one variant. OpenVLA-OFT: 470, 1 and 29, with 13 of the 29 in task 5.
- The flips do not belong to one image step. Every pair of OpenVLA-7B pipelines differs in 74-99 episodes, any two variants flip the same episodes 2.5-3 times as often as chance (33-40 shared against 12-15 expected), and no variant differs from another (McNemar p 0.23 or more).
- The reference cell is a little lucky. On initial states 0-19 all four OpenVLA-7B variants score above it (163-168 against 161), on states 20-49 all four score below it (251-260 against 264); it sits 4.5 episodes above the mean of the other four pipelines.
- Not an edge effect of the step budget: the episodes a variant loses had succeeded at a median of 123-128 of 230 env steps in the reference, and cutting the budget to 120-180 steps does not reduce the flips.
- Trajectories. The runs are nearly deterministic (the identical OpenVLA-7B rerun repeats 497 of 500 outcomes and the exact success step in 415 of 423), yet under any variant almost every OpenVLA-7B trajectory changes: among episodes that succeed in both, only 3-5% succeed at the same step (median difference 5-8 steps). OpenVLA-OFT keeps 9-35% (median difference 1-3 steps). Flip rates cannot compare the two models' sensitivity, because they depend on the success level (85% against 99%); these step differences can.
- OpenVLA-OFT with the crop off is below every other OFT pipeline (against bilinear: 2 gained, 15 lost, McNemar p 0.002, uncorrected), the only candidate for a real effect here, but it rests on one task.
- Consequence for comparing scores: given its number of flips, a pipeline change with no systematic effect still moves a 500-episode LIBERO-Spatial score within about ±3.4 to ±3.8 points (95%) for OpenVLA-7B and ±1.0 to ±1.7 for OpenVLA-OFT. Score gaps of that size between two evaluation pipelines are not evidence that the pipelines differ.
