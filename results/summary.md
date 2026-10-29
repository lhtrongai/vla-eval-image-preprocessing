# Image-pipeline cells on LIBERO-Spatial (500 paired episodes per cell)

Every cell changes one step of the evaluation image pipeline and runs the 10 tasks x 50 stored initial states of LIBERO-Spatial. Episodes are paired with the model's reference cell by (task, initial state); the initial-state hashes match the reference in all 500 pairs of every cell.

- Models: OpenVLA-7B (`openvla/openvla-7b-finetuned-libero-spatial`, sdpa attention) and OpenVLA-OFT (`moojink/openvla-7b-oft-finetuned-libero-spatial`).
- Stack: MuJoCo 3.3.7, robosuite 1.4.1, torch 2.8.0+cu128, one RTX PRO 4500 per cell, step budget 220 policy steps plus 10 settle steps.
- Reference cells: OpenVLA-7B ran on 6 October 2026, OFT on 3 and 5 October 2026 (initial states 0-19 and 20-49, the original evaluation script). Variant cells and the identical reruns ran on 28-29 October 2026, OFT again as two runs (0-19, 20-49).
- Variants: `jpeg_off` skips the JPEG round trip; `crop_off` skips the center crop of the evaluation script; `bilinear` replaces the Lanczos resize with bilinear (JPEG round trip and antialias kept); `render224` renders the cameras at 224x224 instead of 256x256; `rerun` repeats the reference unchanged.
- Primary comparison, fixed before any run: JPEG round trip off on OpenVLA-7B. A pilot on initial states 0-19 found 17.5% of episodes changing outcome, so the rule fixed beforehand reports the one-sided 95% upper bound on the loss at 500 pairs. The other seven variant comparisons are secondary, Holm-adjusted.

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
- Turning the JPEG round trip off costs OpenVLA-7B less than 3.6 points on LIBERO-Spatial (one-sided 95% bound; estimate -0.8), although 74 of 500 episodes change outcome, in both directions.
- No secondary comparison passes 0.05 after Holm. The closest is the center crop on OpenVLA-OFT (-2.4 points, Holm p 0.053), with 10 of its 18 changed episodes in task 5; OFT was trained with random 90% crops, so turning the crop off at evaluation is a train/test mismatch.
- The center-crop cost on OpenVLA-7B (-1.0 points, loss interval [-2.6, +4.6]) is consistent with the about 3 points reported by vla-eval but not distinguishable from zero.
- Noise floor: the identical rerun changes 3 of 500 OpenVLA-7B episodes (run on another day and pod than the reference) and none of the OFT episodes.

Image steps were checked before the runs on a LIBERO-Spatial frame: the rewritten resize reproduces the official step pixel for pixel; the bilinear variant changes the policy input by 0.76 grey levels on average and rendering at 224 by 1.84 (`scripts/check_image_variants.py`).
