# Sham controls, render-at-224 CPU control and OpenVLA-OFT stack check

Produced by `python scripts/sham_control_analysis.py` (pre-registered in `controls/PLAN.md`).

## Validity of every control cell

- `openvla7b_spatial_sham_noise_seed1`: valid (first frame differs from the October rerun in 0 of 500 pairs; GPU driver 595.112.07)
- `openvla7b_spatial_sham_noise_seed2`: valid (first frame differs from the October rerun in 0 of 500 pairs; GPU driver 595.112.07)
- `openvla7b_spatial_sham_jpeg_q94`: valid (first frame differs from the October rerun in 0 of 500 pairs; GPU driver 595.112.07)
- `openvla7b_spatial_render224_cpu_control`: valid (first frame differs from the repeated cell in 0 of 500 pairs; GPU driver 595.112.07)
- `oft_spatial_rerun_stack_check`: valid (first frame differs from the October rerun in 0 of 500 pairs; GPU driver 595.112.07)
- `oft_spatial_sham_noise_seed1`: valid (first frame differs from the October rerun in 0 of 500 pairs; GPU driver 595.112.07)
- `oft_spatial_sham_noise_seed2`: valid (first frame differs from the October rerun in 0 of 500 pairs; GPU driver 595.112.07)
- `oft_spatial_sham_jpeg_q94`: valid (first frame differs from the October rerun in 0 of 500 pairs; GPU driver 595.112.07)

## Sham control

Flips: pairs whose outcome differs from the model's October reference cell. Ratio: (mean flips of the sham cells - flips of the identical rerun) / (mean flips of JPEG off and bilinear - flips of the identical rerun). Read as many flips when the ratio is at least 0.5.

### OpenVLA-7B

| Cell | Success | Lost / gained | Flips | Difference, points (95% CI) | McNemar p | Band, points | Inside band | Flips vs October rerun | Flips in the fragile pool |
|---|---|---|---|---|---|---|---|---|---|
| `openvla7b_spatial_sham_noise_seed1` | 428/500 | 29 / 32 | 61 | +0.6 [-2.4, +3.6] | 0.798 | ±3.1 | yes | 62 | 45 of 61 |
| `openvla7b_spatial_sham_noise_seed2` | 420/500 | 44 / 39 | 83 | -1.0 [-4.6, +2.6] | 0.661 | ±3.6 | yes | 82 | 62 of 83 |
| `openvla7b_spatial_sham_jpeg_q94` | 421/500 | 41 / 37 | 78 | -0.8 [-4.2, +2.6] | 0.734 | ±3.5 | yes | 77 | 56 of 78 |

Sham flips 61, 83, 78 (total 222; many from 123); steps [74, 83] (JPEG off, bilinear), rerun floor 3. Ratio 0.94 (bootstrap 95% interval 0.81 to 1.10, descriptive): **many flips**. With render-at-224 in the comparator 0.89; against the October rerun as reference 0.92. Sham flips in the fragile pool of October: 73% (the pool holds 38% of the episodes; same pool: no). Every sham cell inside its band: yes. Noise draw 1 against draw 2: 78 flips.

Same success step as the step reference among episodes that succeed in both: sham_noise_seed1 7% (median difference 5), sham_noise_seed2 6% (median difference 5), sham_jpeg_q94 6% (median difference 5)

Flips per task: sham_noise_seed1 [5, 9, 3, 4, 8, 3, 2, 10, 8, 9]; sham_noise_seed2 [7, 12, 5, 4, 13, 3, 7, 8, 11, 13]; sham_jpeg_q94 [8, 5, 3, 4, 10, 8, 3, 9, 12, 16]

### OpenVLA-OFT

| Cell | Success | Lost / gained | Flips | Difference, points (95% CI) | McNemar p | Band, points | Inside band | Flips vs October rerun | Flips in the fragile pool |
|---|---|---|---|---|---|---|---|---|---|
| `oft_spatial_sham_noise_seed1` | 497/500 | 1 / 3 | 4 | +0.4 [-0.4, +1.2] | 0.625 | ±0.8 | yes | 4 | 4 of 4 |
| `oft_spatial_sham_noise_seed2` | 494/500 | 4 / 3 | 7 | -0.2 [-1.2, +0.8] | 1 | ±1.0 | yes | 7 | 3 of 7 |
| `oft_spatial_sham_jpeg_q94` | 496/500 | 2 / 3 | 5 | +0.2 [-0.6, +1.0] | 1 | ±0.9 | yes | 5 | 5 of 5 |

Sham flips 4, 7, 5 (total 16; many from 13); steps [10, 7] (JPEG off, bilinear), rerun floor 0. Ratio 0.63 (bootstrap 95% interval 0.30 to 1.04, descriptive): **many flips** (close to the cutoff: the interval contains it). With render-at-224 in the comparator 0.59; against the October rerun as reference 0.63. Sham flips in the fragile pool of October: 75% (the pool holds 6% of the episodes; same pool: yes). Every sham cell inside its band: yes. Noise draw 1 against draw 2: 5 flips.

Same success step as the step reference among episodes that succeed in both: sham_noise_seed1 41% (median difference 1), sham_noise_seed2 43% (median difference 1), sham_jpeg_q94 41% (median difference 1)

Flips per task: sham_noise_seed1 [0, 0, 1, 1, 0, 2, 0, 0, 0, 0]; sham_noise_seed2 [0, 0, 2, 1, 0, 3, 0, 0, 0, 1]; sham_jpeg_q94 [0, 0, 1, 1, 0, 2, 0, 0, 0, 1]


**Writing branch (set by OpenVLA-7B): fragility.** OpenVLA-OFT reading: many flips, the same.

## Render-at-224 CPU control (OpenVLA-7B)

Outcomes differ from the cell of 29 October (EPYC 7443) in 0 of 500 pairs (rule: at most the OpenVLA-7B rerun floor, 3). **Reading (a)**: keep the October cell; report this run as a CPU check; drop the CPU caveat of this cell. Against the reference: this run 427/500, lost 45, gained 47, 92 flips (October cell 427/500, 45 / 47, 92 flips). Success step differs in 0 of 500 pairs.

## OpenVLA-OFT stack check

Outcomes differ from the October reference in 0 and from the October rerun in 0 of 500 pairs; the success step equals the October rerun in 500 of 500. **Reading (a)**: the cells of this run and of October share one stack.
