# Timeline of the control cells

The sham and CPU control cells were planned and committed before any of them ran. Times are commit times in UTC, as recorded by git and the hosting service; the logs in `results/controls/pods/*/chain.log` give the start and end of every cell.

| Event | Time (UTC) |
|---|---|
| Plan of the controls committed and pushed (`controls/PLAN.md`, `controls/cells.json`, `controls/code_sha256.txt`, launch scripts, `scripts/sham_control_analysis.py`) | 2026-11-22 14:18 |
| One correction pushed: the GPU check of `controls/run_pod.sh` read a truncated GPU name and refused the right GPU; logged in `controls/PLAN.md` under the changes after the plan commit | 2026-11-22 18:12 |
| First control cell started (`oft-controls`, see its `chain.log`) | 2026-11-22 18:21 |
| Last control cell finished | 2026-11-22 23:59 |
| Logs and the single pre-registered reading (`results/controls/summary.json`) committed | 2026-11-23 10:51 |

The cells, sizes of the changes, reading rule and analysis script did not change after the plan commit apart from the correction above. The commit identifiers can be given to the action editor on request.
