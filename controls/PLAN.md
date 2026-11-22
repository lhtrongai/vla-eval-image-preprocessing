# Sham control and render-at-224 CPU control: plan fixed before the runs

This file, `controls/cells.json`, `controls/code_sha256.txt` and every file that `code_sha256.txt` lists (the image code, both runners, the launch scripts and the analysis script `scripts/sham_control_analysis.py`) were committed before any cell below started. The commit time on GitHub is the timestamp of the plan. Nothing in them changes after the first cell starts; a correction would be a new commit, listed under "Changes after the plan commit" at the end of this file with its reason, and reported with the results.

No outcome of these cells has been seen: none of them has run, there is no pilot, and the notifications during the runs carry only exit codes and episode counts.

## 1. Questions

1. **Sham control.** Each of the four image steps flips 74 to 92 of the 500 OpenVLA-7B episodes against the October reference cell, while an identical rerun flips 3 (OpenVLA-OFT: 7 to 18 against 0). The rerun shows that the flips come from the change, not that they are specific to the steps: any change of the same pixel size might flip as many. Does a meaningless change of the same size, one that belongs to no evaluation pipeline and carries no information, flip about as many episodes as the steps, or about as few as the rerun?
2. **CPU control.** The OpenVLA-7B render-at-224 cell is the only OpenVLA-7B harness cell that ran on another host CPU (AMD EPYC 7443; the others ran on EPYC 7663), and a CPU change alone can change LIBERO rollouts (Jiang et al., 2026, Appendix B). Does the cell repeat its outcomes on an EPYC 7663 host?

## 2. Cells

Eight cells of 500 episodes (10 tasks of LIBERO-Spatial x the 50 stored initial states), with the checkpoints, step budget, software versions, GPU type and command of the October cells (the GPU driver of the host may be newer; it is recorded), all on hosts with an AMD EPYC 7663 56-Core Processor and an NVIDIA RTX PRO 4500 Blackwell. The exact environment and command of each cell is in `controls/cells.json`; how to run them is in `controls/RUN_GUIDE.md`.

| Cell | Model | What changes against the official pipeline |
|---|---|---|
| `openvla7b_spatial_sham_noise_seed1` | OpenVLA-7B | noise of one intensity level on every policy input, draw 1 |
| `openvla7b_spatial_sham_noise_seed2` | OpenVLA-7B | the same noise, draw 2 |
| `openvla7b_spatial_sham_jpeg_q94` | OpenVLA-7B | JPEG round trip at quality 94 instead of 95 |
| `openvla7b_spatial_render224_cpu_control` | OpenVLA-7B | nothing new: the render-at-224 cell of 29 October, repeated on an EPYC 7663 host |
| `oft_spatial_rerun_stack_check` | OpenVLA-OFT | nothing: the reference pipeline, repeated, to check that this run's stack repeats October |
| `oft_spatial_sham_noise_seed1` | OpenVLA-OFT | noise of one intensity level on every policy input (third-person and wrist), draw 1 |
| `oft_spatial_sham_noise_seed2` | OpenVLA-OFT | the same noise, draw 2 |
| `oft_spatial_sham_jpeg_q94` | OpenVLA-OFT | JPEG round trip of both images at quality 94 instead of 95 |

OpenVLA-OFT cells run as two segments, initial states 0-19 and 20-49, like every OpenVLA-OFT cell of October, so that the scenes are the same.

**The two sham changes.**

- *Noise.* Every value of every image the policy receives (the processor input, after the crop step; for OpenVLA-OFT the third-person and the wrist image) moves by exactly one intensity level, up or down. The sign of each value comes from the bits of SHAKE-256 of the key `noise-control|seed=S|task=T|state=I|call=C` (seed, task, initial state, processor call in the episode), so the noise is new at every query, identical on every machine and for every rerun of the cell; values at 0 move up and values at 255 move down. The image steps themselves stay official. Two draws, seeds 1 and 2. Code: `scripts/image_pipeline.py` (`add_noise`, `NoisyProcessor`).
- *JPEG quality 94.* The JPEG round trip encodes at quality 94; the official step uses 95, the default of `tf.image.encode_jpeg`. A change no one would read as another pipeline.

**Size of the changes** at the 224 x 224 policy input of OpenVLA-7B (mean absolute difference to the official input over all pixels and channels, in intensity levels; first frames of initial state 0 of the 10 tasks, rendered on CPU; `controls/measure_sham_sizes.py`, output `controls/sham_sizes.json`; the script reproduces the stored values of JPEG off and bilinear exactly):

| Change | Mean change (levels) | Pixels changed |
|---|---|---|
| Bilinear resize (image step) | 0.64 | 40% |
| JPEG off (image step) | 1.26 | 96% |
| Render at 224 (image step; 50 frames, `paper/generated/table_eda.tex`) | 1.76 | 79% |
| Crop step off (image step; 50 frames, same table) | 8.33 | 88% |
| JPEG quality 94 (sham) | 0.54 | 59% |
| Noise of one level (sham) | 1.00 | 100% |

The two shams are of the size of the two mildest steps, bilinear (0.64) and JPEG off (1.26); neither is of the size of the crop step.

**Considered and not run.** Pillow JPEG at quality 75 and Pillow Lanczos (what some harnesses use) are realistic implementation differences, not meaningless changes, and answer another question. Another evaluation seed would not change the input image, which is what the sham has to change. Fresh initial states and other suites address power and scope, not the question above. An OpenVLA-7B identical rerun in this batch would cost as much as a sham cell; the render-at-224 control plays that role for OpenVLA-7B when it repeats its cell.

## 3. What is compared

Every control cell is paired with its model's October reference cell by (task, initial state), as every variant of the paper. A flip is a pair whose outcome differs.

- **Comparator:** the mean flips of JPEG off and bilinear, the two steps whose input change is of the size of the shams (0.64 and 1.26 levels, against 0.54 and 1.00) and which ran on EPYC 7663 hosts: OpenVLA-7B (74 + 83) / 2 = 78.5, OpenVLA-OFT (10 + 7) / 2 = 8.5. Render at 224 is left out so that the CPU control cannot move the reading; crop off is left out because its change is eight times larger.
- **Floor:** the flips of the identical October rerun: 3 (OpenVLA-7B), 0 (OpenVLA-OFT).
- **Ratio:** R = (mean flips of the three sham cells - floor) / (comparator - floor), the share of the steps' flips above the floor that a meaningless change of the same size also produces.

## 4. Reading rule

- **OpenVLA-7B: many flips if R is at least 0.5, that is, if the three sham cells flip at least 123 episodes in total (41 per cell on average); few flips if they flip 122 or fewer.**
- **OpenVLA-OFT: many flips if the three sham cells flip at least 13 episodes in total; few flips if 12 or fewer.**
- **The writing branch is set by OpenVLA-7B**, where the 74 to 92 flips carry the claims of the paper. The OpenVLA-OFT reading is reported; if it differs, one prepared sentence says so (section 6).
- If the 95% bootstrap interval of R (episodes resampled, fixed seed, descriptive only) contains 0.5, the text says that the result is close to the cutoff, in either branch.

Why 0.5: at least half of the steps' flips above the floor means that most of them are what any small change produces. The two alternatives are far apart: a sham that behaves like the steps gives about 78 flips per OpenVLA-7B cell (standard deviation about 8), one that behaves like the rerun gives about 3, and the cutoff of 41 per cell is far from both. It decides only an intermediate result, and then the text reports the ratio and its interval.

`scripts/sham_control_analysis.py` implements this rule. It recomputes the comparator, the floor and the two totals (123 and 13) from the October files and stops if they differ from this section.

## 5. Validity, and when the results are read

A control cell is valid only if all of these hold:

1. it holds the 500 (task, initial state) pairs, with the initial-state hash of the LIBERO init file in every pair;
2. the fixture placement equals the October rerun of its model in every pair, and the first frame of the cameras the policy uses (OpenVLA-7B: third-person; OpenVLA-OFT: third-person and wrist) equals it in all but at most 5 of the 500 pairs. The pairs that differ are counted in the report. The OpenVLA-OFT CPU control of November, on a newer GPU driver (595.112.07 against 595.91.07 in October), differed in 1 pair, in the wrist image only; more than 5 would mean that the stack renders differently, and then the runs stop until the stacks are compared. For the CPU control the first-frame hashes are reported, not required;
3. `run_meta.json` of every segment records the EPYC 7663 CPU, the RTX PRO 4500 Blackwell GPU, the software versions of October (torch 2.8.0+cu128, MuJoCo 3.3.7, robosuite 1.4.1, numpy 1.26.4, transformers 4.40.1, TensorFlow 2.16.2), the image settings and command of `cells.json`, and the SHA-256 of `controls/code_sha256.txt` for the image code and the runner that ran;
4. the sham was applied: in a noise cell every episode logs a change of exactly 1.0 level on its first processor input and one processor call per query (OpenVLA-7B: one per policy step; OpenVLA-OFT: two per chunk of 8 steps); in a JPEG-94 cell every episode logs a nonzero change of its first input;
5. the evaluation log has 500 finished episodes and no episode that ended with a caught exception (an error in the control code stops the run instead: `image_pipeline.guarded`), and every segment exited with code 0.

An invalid cell is run again on a new EPYC 7663 host with the same configuration, as its next attempt, if the budget allows; the failed attempt is kept under `results/controls/invalid/` with the reason. The results are read once, by running `scripts/sham_control_analysis.py` after every cell is valid. If the budget is spent first, the script runs with `--budget-spent`: each model is then read with its valid sham cells (at least two; the totals become 82 for OpenVLA-7B and 9 for OpenVLA-OFT for two cells) and the text names the missing cell. No success count or flip is looked at before that.

## 6. Writing branches

Placeholders: `{s7}` the three OpenVLA-7B sham flips (for example "75, 81 and 70"), `{s7r}` their range, `{s7p}` their range in percent of 500, `{r7}` the ratio in percent, `{so}`, `{sor}`, `{ro}` the same for OpenVLA-OFT, `{n12}` the flips between the two noise draws of OpenVLA-7B, `{pool}` the share of sham flips among the 189 OpenVLA-7B episodes of the October fragile pool.

### Many flips (fragility branch)

- **Title:** "Outcome Fragility of Two OpenVLA Policies Under Small Evaluation Image Changes in LIBERO-Spatial".
- **Abstract**, in place of "This extends to the evaluator's own image steps the cancellation of opposing outcome changes that paired evaluations have reported for compound perturbations.": "A meaningless change of the same pixel size, independent noise of one intensity level or JPEG quality 94 instead of 95, flips {s7r} episodes, {r7}% of the steps' flips above the rerun floor, so most of these flips reflect how sensitive the policy is to any small change of its input, not an effect of the particular steps." (If R is 1 or more: "as many episodes as the steps or more" in place of "{r7}% of the steps' flips above the rerun floor".)
- **Contributions, second item:** "... while each step flips 14.8% to 18.4% of OpenVLA-7B episodes in both directions, from a shared pool of fragile episodes, and a meaningless change of the same pixel size flips {s7p}, against 3 of 500 for an identical rerun on the same stack".
- **End of the introduction:** "... what is new is that they hold for changes of about one intensity level on clean frames, whether the change is an image step of the evaluator or meaningless noise."
- **Results, new paragraph "Sham control":** "A meaningless change of the same pixel size flips {s7} OpenVLA-7B and {so} OpenVLA-OFT episodes, {r7}% and {ro}% of the steps' flips above the rerun floor (the steps flip 74 to 92 and 7 to 18, the identical rerun 3 and 0). Two draws of the same noise differ in {n12} OpenVLA-7B episodes." Add, only if the share of sham flips inside the fragile pool is at least twice the pool's share of episodes (75.6% for OpenVLA-7B): "{pool} of the sham flips fall among the 189 fragile episodes of the four steps, which hold 38% of the episodes." The sentence "The flips come from a common pool of fragile episodes rather than from one step." stays.
- **Discussion, "What this means for practice":** "... the larger risk to comparisons is not one step: any change to the evaluation, even meaningless noise of one intensity level, reshuffles the fragile episodes, and other studies show that for some stacks even a different machine does".
- **Recommendation (iii):** "measure the floor of flips with a meaningless change of the size of the change being compared, not only with an identical rerun, on the same hardware and policy".
- **Conclusion:** "Yet every step, including a JPEG change of about one intensity level, flips 14.8% to 18.4% of OpenVLA-7B episodes in both directions and changes almost every trajectory, and a meaningless change of the same size flips {s7p}: on clean frames the outcome of these episodes depends on any small change of the input, so the cancellation that paired evaluations have reported for large perturbations already occurs for changes this small."

### Few flips (step-specific branch)

- **Title:** unchanged, "Per-Step Effects of Evaluation Image Preprocessing on Two OpenVLA Policies in LIBERO-Spatial".
- **Abstract**, in place of the same sentence: "A meaningless change of the same pixel size, independent noise of one intensity level or JPEG quality 94 instead of 95, flips {s7r} episodes, {r7}% of the steps' flips above the rerun floor, so most of a step's flips are specific to that step, and the cancellation of opposing outcome changes that paired evaluations have reported for compound perturbations holds for the evaluator's own image steps."
- **Contributions, second item:** "... while each step flips 14.8% to 18.4% of OpenVLA-7B episodes in both directions, from a shared pool of fragile episodes, against {s7p} for a meaningless change of the same pixel size and 3 of 500 for an identical rerun on the same stack".
- **End of the introduction:** "... what is new is that they hold for the mild image steps of the evaluator itself, applied to clean frames, beyond what a meaningless change of the same size produces."
- **Results, new paragraph "Sham control":** "A meaningless change of the same pixel size flips {s7} OpenVLA-7B and {so} OpenVLA-OFT episodes, against 74 to 92 and 7 to 18 for the steps and 3 and 0 for the identical rerun, so each step flips more episodes than its pixel change alone explains." The sentence "The flips come from a common pool of fragile episodes rather than from one step." becomes "The flips of the four steps fall largely in a common pool of fragile episodes."
- **Discussion, "What this means for practice":** the clause "any change to the evaluation reshuffles the fragile episodes" is cut; the passage becomes: "For the two checkpoints studied here, each step flips more episodes than a meaningless change of the same size ({s7r} against 74 to 92), so the steps have to be matched one by one, and other studies show that for some stacks a different machine changes outcomes as well".
- **Recommendation (iii):** "measure an A/A floor on the same hardware and policy, and the flips of a meaningless change of the same size".
- **Conclusion:** "Yet every step, including a JPEG change of about one intensity level, flips 14.8% to 18.4% of OpenVLA-7B episodes in both directions and changes almost every trajectory, more than a meaningless change of the same size ({s7p}), so the cancellation that paired evaluations have reported for large perturbations already occurs for the evaluator's own steps on clean frames."

### If OpenVLA-OFT reads differently

- OpenVLA-7B many, OpenVLA-OFT few: "For OpenVLA-OFT the sham cells flip {sor} episodes, fewer than its steps (7 to 18), so its few flips are specific to the steps." Title and claims of fragility then name OpenVLA-7B.
- OpenVLA-7B few, OpenVLA-OFT many: "For OpenVLA-OFT the sham cells flip {sor} episodes, about as many as its steps (7 to 18): near full success, its few flips are what any small change produces."

### In both branches

- The sham cells are reported with success, lost and gained episodes, net change with its exact paired bootstrap interval and McNemar p (outside the Holm family of the paper), next to the steps.
- **Band.** If the net change of any sham cell of a model lies outside its band of plus or minus 1.96 sqrt(f) / n, the band is not presented as the range that a change with no systematic effect produces for that model; the text reports the sham cells' net changes instead. Otherwise the band sentence stays and cites the sham cells as a check.
- Limitations gain one sentence: the sham control covers two kinds of meaningless change at the size of the mild steps, not at the size of the crop step.

## 7. Render-at-224 CPU control: reading rule

The same form as the CPU control of the OpenVLA-OFT crop-off cell (run 21-22 November 2026, results in `results/oft_spatial_crop_off_cpu_control/`), with the OpenVLA-7B rerun floor of 3 in place of the OpenVLA-OFT floor of 0. Compared pair by pair with the October cell `openvla7b_spatial_render224`:

- **(a) The outcomes differ in at most 3 of the 500 pairs:** the October cell stays the result; the rerun is reported as a CPU check in the appendix, next to the OpenVLA-OFT one; the CPU caveat of this cell is dropped from the setup, the run log and the limitations.
- **(b) They differ in more than 3 pairs:** both runs are reported (the results table keeps the October cell and adds the rerun below it, each with its CPU and GPU driver); the text states that the OpenVLA-7B render-at-224 result depends on the host it runs on (the CPU type, and the GPU driver where it differs; the OpenVLA-OFT stack check tells whether the driver alone changes outcomes); the caveat stays, and the OpenVLA-7B flip range is quoted with both values of this cell.

This reading does not change the sham reading: render at 224 is not in the comparator.

## 8. OpenVLA-OFT stack check: reading rule

- **(a) The outcomes differ from the October OpenVLA-OFT reference in 0 of the 500 pairs** (its floor): the cells of this run and of October share one stack.
- **(b) Otherwise:** the difference is reported, the OpenVLA-OFT sham flips are also given against this cell, and the OpenVLA-OFT reading stays the one computed against the October reference.

## 9. Also reported, without changing any reading

For every sham cell: flips against the October rerun used as the reference; the ratio with render at 224 added to the comparator and with the October rerun as the reference; flips between the two noise draws; the share of its flips inside the October fragile pool against the pool's share of episodes; the share of episodes that succeed at the same step as in the step reference (OpenVLA-7B: the reference; OpenVLA-OFT: the October rerun); flips per task. For the CPU control: outcomes, lost and gained against the reference for both runs, and the pairs whose success step or first-frame hash differs.

## 10. Budget

At most 30 GPU-hours in total, counted as billed pod time (setup, checks, model loading and idle time included). Estimate from the October cells (OpenVLA-7B: 4.2 to 4.7 hours of episodes per cell; OpenVLA-OFT: 0.7 hours), five pods in parallel, about 5 hours of wall time:

| Pod | Cells | Estimate (GPU-hours) |
|---|---|---|
| `openvla7b-noise-seed1` | sham noise, draw 1 | 5.1 |
| `openvla7b-noise-seed2` | sham noise, draw 2 | 5.1 |
| `openvla7b-jpeg-q94` | sham JPEG quality 94 | 5.1 |
| `openvla7b-render224-cpu` | CPU control | 4.7 |
| `oft-controls` | stack check, then the three shams | 3.3 |
| one short pod at the end | packing the logs | 0.2 |
| **Total** | | **23.5** |

The 6.5 hours left cover one OpenVLA-7B cell run again.

## Changes after the plan commit

1. 23 November 2026, before any cell started. The GPU check of `controls/run_pod.sh` searched the `nvidia-smi` table for the full name `NVIDIA RTX PRO 4500 Blackwell`, but the table cuts the name to `NVIDIA RTX PRO 4500 Blac...`, so the check refused the right GPU and no cell could start. The check now reads `nvidia-smi --query-gpu=name --format=csv,noheader` (saved as `gpu_name.txt`, which `controls/pack_logs.sh` now also packs) and requires exactly one GPU with that full name. `controls/code_sha256.txt` has the new hashes of `run_pod.sh` and `pack_logs.sh`, and `controls/RUN_GUIDE.md` now runs from the last commit that changed `code_sha256.txt`. The cells, settings, sizes, reading rule and analysis are unchanged.
