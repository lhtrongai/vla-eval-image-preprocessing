# Timeline of the control cells

The control cells of `controls/PLAN.md` (the sham cells, the rerun of the OpenVLA-7B render-at-224 cell on the other host CPU, and the OpenVLA-OFT stack check) were planned and committed before any of them ran. The earlier CPU control of the OpenVLA-OFT crop-off cell (`results/oft_spatial_crop_off_cpu_control/`, run on 21-22 November 2026) was not part of this plan. Times are commit times in UTC, as recorded by git and the hosting service; the logs in `results/controls/pods/*/chain.log` give the start and end of every cell.

| Event | Time (UTC) |
|---|---|
| Plan of the controls committed and pushed (`controls/PLAN.md`, `controls/cells.json`, `controls/code_sha256.txt`, launch scripts, `scripts/sham_control_analysis.py`) | 2026-11-22 14:18 |
| One correction pushed: the GPU check of `controls/run_pod.sh` read a truncated GPU name and refused the right GPU; logged in `controls/PLAN.md` under the changes after the plan commit | 2026-11-22 18:12 |
| First control cell started (`oft-controls`, see its `chain.log`) | 2026-11-22 18:21 |
| Last control cell finished | 2026-11-22 23:59 |
| Logs and the single pre-registered reading (`results/controls/summary.json`) committed | 2026-11-23 10:51 |

The cells, sizes of the changes, reading rule and analysis script did not change after the plan commit apart from the correction above. The commit identifiers can be given to the action editor on request.
