# Control Results Summary

Pre-registered plan: `controls/PLAN.md` (plan commit `04fb502c2dd076ca8a66f645b78ca60d145efea2`; run commit `e6ec1c2ee91cd246427c0a4a98a28a8ec0be2cd5`, which fixed the truncated GPU name check in `controls/run_pod.sh` before any cell started).
Analysis output: `results/controls/summary.md` and `results/controls/summary.json`, produced by running `python scripts/sham_control_analysis.py --json results/controls/summary.json > results/controls/summary.md` once after all eight cells completed.

## 1. Host CPU, GPU and Validity Check of Every Cell

Every cell ran on a RunPod Secure Cloud pod in `EU-RO-1` with an `AMD EPYC 7663 56-Core Processor`, one `NVIDIA RTX PRO 4500 Blackwell` (GPU driver `595.112.07`), and the exact software stack and SHA-256 code hashes of `controls/code_sha256.txt`. All eight cells passed every validity check in `controls/PLAN.md` Section 5 (500 finished episodes, exit code 0, initial-state hashes, fixture placement, first-frame agreement, sham perturbation logged on every episode):

| Cell | Pod Label (`Pod ID`) | Host CPU | GPU (`Driver`) | Episodes (Exit Code) | First-Frame Diffs vs Check Reference | Sham / Perturbation Check | Validity |
|---|---|---|---|---|---|---|---|
| `openvla7b_spatial_sham_noise_seed1` | `openvla7b-noise-seed1` (`vjd8p17tv8lxc6`) | `AMD EPYC 7663 56-Core Processor` | `NVIDIA RTX PRO 4500 Blackwell` (`595.112.07`) | 500 (`rc=0`) | 0 / 500 vs October rerun | 1.0 level on every first input, 1 call/step | **valid** |
| `openvla7b_spatial_sham_noise_seed2` | `openvla7b-noise-seed2` (`a91vxubp4g0xis`) | `AMD EPYC 7663 56-Core Processor` | `NVIDIA RTX PRO 4500 Blackwell` (`595.112.07`) | 500 (`rc=0`) | 0 / 500 vs October rerun | 1.0 level on every first input, 1 call/step | **valid** |
| `openvla7b_spatial_sham_jpeg_q94` | `openvla7b-jpeg-q94` (`vfhsjqyivuhbg4`) | `AMD EPYC 7663 56-Core Processor` | `NVIDIA RTX PRO 4500 Blackwell` (`595.112.07`) | 500 (`rc=0`) | 0 / 500 vs October rerun | nonzero JPEG-94 diff on every first input | **valid** |
| `openvla7b_spatial_render224_cpu_control` | `openvla7b-render224-cpu` (`ivbephacqutm5t`) | `AMD EPYC 7663 56-Core Processor` | `NVIDIA RTX PRO 4500 Blackwell` (`595.112.07`) | 500 (`rc=0`) | 0 / 500 vs 29 Oct cell | render-at-224 CPU control | **valid** |
| `oft_spatial_rerun_stack_check` | `oft-controls` (`n4y72ojze627sl`) | `AMD EPYC 7663 56-Core Processor` | `NVIDIA RTX PRO 4500 Blackwell` (`595.112.07`) | 500 (`rc=0`) | 0 / 500 vs October rerun | reference pipeline stack check | **valid** |
| `oft_spatial_sham_noise_seed1` | `oft-controls` (`n4y72ojze627sl`) | `AMD EPYC 7663 56-Core Processor` | `NVIDIA RTX PRO 4500 Blackwell` (`595.112.07`) | 500 (`rc=0`) | 0 / 500 vs October rerun | 1.0 level on both cameras, 2 calls/chunk | **valid** |
| `oft_spatial_sham_noise_seed2` | `oft-controls` (`n4y72ojze627sl`) | `AMD EPYC 7663 56-Core Processor` | `NVIDIA RTX PRO 4500 Blackwell` (`595.112.07`) | 500 (`rc=0`) | 0 / 500 vs October rerun | 1.0 level on both cameras, 2 calls/chunk | **valid** |
| `oft_spatial_sham_jpeg_q94` | `oft-controls` (`n4y72ojze627sl`) | `AMD EPYC 7663 56-Core Processor` | `NVIDIA RTX PRO 4500 Blackwell` (`595.112.07`) | 500 (`rc=0`) | 0 / 500 vs October rerun | nonzero JPEG-94 diff on both cameras | **valid** |

## 2. Sham Control Results: Flips per Cell, Totals, and Ratio R

### OpenVLA-7B (paired against October reference `openvla7b_spatial_reference`, 425/500)

| Cell | Success | Lost / Gained | Flips | Net Diff, percentage points (95% CI) | McNemar p | Band (points) | Inside Band | Flips vs October Rerun | Flips in October Fragile Pool |
|---|---|---|---|---|---|---|---|---|---|
| `openvla7b_spatial_sham_noise_seed1` | 428 / 500 (85.6%) | 29 / 32 | **61** | +0.6 [-2.4, +3.6] | 0.798 | ±3.1 | yes | 62 | 45 / 61 |
| `openvla7b_spatial_sham_noise_seed2` | 420 / 500 (84.0%) | 44 / 39 | **83** | -1.0 [-4.6, +2.6] | 0.661 | ±3.6 | yes | 82 | 62 / 83 |
| `openvla7b_spatial_sham_jpeg_q94` | 421 / 500 (84.2%) | 41 / 37 | **78** | -0.8 [-4.2, +2.6] | 0.734 | ±3.5 | yes | 77 | 56 / 78 |

- **Flips per OpenVLA-7B sham cell:** `61`, `83`, `78` (`12.2%`, `16.6%`, `15.6%` of 500 episodes; noise draw 1 vs draw 2: `78` flips).
- **Total sham flips for OpenVLA-7B:** **`222`** (mean `74.0` flips/cell; cutoff for many flips is `>= 123` total, `41.0` per cell).
- **Comparator and floor (OpenVLA-7B):** mild steps JPEG off (`74`) and bilinear (`83`), mean `78.5`; identical October rerun floor `3`.
- **Ratio R for OpenVLA-7B:** **`R = 0.94`** (`0.9404`, or `94%`), descriptive 95% paired bootstrap interval **`[0.81, 1.10]`** (`[0.8073, 1.1024]`).
  - Secondary ratios: with render-at-224 included in comparator `0.89` (`0.8875`); against the October rerun as reference `0.92` (`0.9237`).
  - Share of sham flips inside the 189-episode October fragile pool: `163 / 222 = 73.4%` (`73%`, against the pool's `37.8%` share of episodes; below the `2x = 75.6%` threshold, so `same_pool: false`).
  - Every OpenVLA-7B sham cell lies inside its `±1.96 sqrt(f) / n` band (`band_supported: true`).

### OpenVLA-OFT (paired against October reference `oft_spatial_reference`, 495/500)

| Cell | Success | Lost / Gained | Flips | Net Diff, percentage points (95% CI) | McNemar p | Band (points) | Inside Band | Flips vs October Rerun | Flips in October Fragile Pool |
|---|---|---|---|---|---|---|---|---|---|
| `oft_spatial_sham_noise_seed1` | 497 / 500 (99.4%) | 1 / 3 | **4** | +0.4 [-0.4, +1.2] | 0.625 | ±0.8 | yes | 4 | 4 / 4 |
| `oft_spatial_sham_noise_seed2` | 494 / 500 (98.8%) | 4 / 3 | **7** | -0.2 [-1.2, +0.8] | 1.000 | ±1.0 | yes | 7 | 3 / 7 |
| `oft_spatial_sham_jpeg_q94` | 496 / 500 (99.2%) | 2 / 3 | **5** | +0.2 [-0.6, +1.0] | 1.000 | ±0.9 | yes | 5 | 5 / 5 |

- **Flips per OpenVLA-OFT sham cell:** `4`, `7`, `5` (`0.8%`, `1.4%`, `1.0%` of 500 episodes; noise draw 1 vs draw 2: `5` flips).
- **Total sham flips for OpenVLA-OFT:** **`16`** (mean `5.33` flips/cell; cutoff for many flips is `>= 13` total).
- **Comparator and floor (OpenVLA-OFT):** mild steps JPEG off (`10`) and bilinear (`7`), mean `8.5`; identical October rerun floor `0`.
- **Ratio R for OpenVLA-OFT:** **`R = 0.63`** (`0.6275`, or `63%`), descriptive 95% paired bootstrap interval **`[0.30, 1.04]`** (`[0.2963, 1.0417]`). Because the interval contains the `0.5` cutoff, the OpenVLA-OFT ratio is noted as close to the cutoff.
  - Secondary ratios: with render-at-224 included in comparator `0.59` (`0.5926`); against the October rerun as reference `0.63` (`0.6275`).
  - Share of sham flips inside the 29-episode October fragile pool: `12 / 16 = 75.0%` (against the pool's `5.8%` share of episodes; `same_pool: true`).
  - Every OpenVLA-OFT sham cell lies inside its `±1.96 sqrt(f) / n` band (`band_supported: true`).

## 3. Pre-Registered Readings

1. **Writing branch (`controls/PLAN.md` Sections 4 and 6):** **Branch A — Many flips (`fragility` branch)**.
   - OpenVLA-7B sets the writing branch with `222 >= 123` total sham flips and `R = 0.94 >= 0.5` (95% CI `[0.81, 1.10]`, strictly above `0.5`).
   - OpenVLA-OFT also reads **many flips** (`16 >= 13` total sham flips, `R = 0.63 >= 0.5`, 95% CI `[0.30, 1.04]`, close to the cutoff), agreeing with OpenVLA-7B (`oft_agrees: true`).
2. **Render-at-224 CPU control reading (`controls/PLAN.md` Section 7):** **Reading (a)**.
   - `openvla7b_spatial_render224_cpu_control` (run on `AMD EPYC 7663 56-Core Processor`, GPU driver `595.112.07`) differs from the 29 October cell `openvla7b_spatial_render224` (`AMD EPYC 7443 24-Core Processor`, GPU driver `595.91.07`) in **`0` of 500 pairs** (cutoff: at most the OpenVLA-7B rerun floor of `3`), and the success step differs in **`0` of 500 pairs**.
   - Against `openvla7b_spatial_reference`, both runs produce `427 / 500` successes, `45` lost, `47` gained, **`92` flips** (+0.4 percentage points, 95% CI `[-3.4, +4.2]`, McNemar `p = 0.917`).
   - Action under Reading (a): keep the October cell in the main table, report this run as a CPU check in the appendix alongside the OpenVLA-OFT CPU control, and drop the CPU caveat of this cell.
3. **OpenVLA-OFT stack check reading (`controls/PLAN.md` Section 8):** **Reading (a)**.
   - `oft_spatial_rerun_stack_check` (GPU driver `595.112.07`) differs from the October reference `oft_spatial_reference` in **`0` of 500 pairs** and from the October rerun `oft_spatial_rerun` in **`0` of 500 pairs** (`495 / 500` successes), and its success step equals the October rerun in **`500` of 500 pairs**.
   - Action under Reading (a): the cells of this run and of October share one stack.

## 4. GPU-Hours Used, Cost, and RunPod Cleanup Note

Detailed per-pod timestamps and durations are logged in `results/controls/pods.md`:

- **Active GPU-hours for the experiment:** **`25.3101` GPU-hours** (within the 30 GPU-hour budget):
  - 5 evaluation pods from pod creation through setup, 500-episode evaluation chains, and watchdog trigger: `24.0297` GPU-hours (`oft-controls`: `4.0224 h`; `openvla7b-render224-cpu`: `4.9607 h`; `openvla7b-jpeg-q94`: `5.1221 h`; `openvla7b-noise-seed1`: `4.9319 h`; `openvla7b-noise-seed2`: `4.9926 h`).
  - 94 short-lived recycled/terminated pods before and during host CPU selection: `1.2467` GPU-hours (`0.7257` GPU-hours across 85 wrong-CPU pods terminated immediately after `lscpu`, plus `0.5209` GPU-hours across 9 pods terminated during initial SSH key and pre-`e6ec1c2` GPU check setup).
  - 1 short packing pod (`2l4bhuaepz5j40`, RTX 4090) to run `controls/pack_logs.sh` and transfer the archive: `0.0337` GPU-hours (`2.02` minutes).
- **Post-watchdog idle GPU-hours billed:** **`18.9879` GPU-hours** (`1,139.27` minutes across the 5 evaluation pods after `controls/watchdog.sh` invoked `runpodctl remove pod`, which failed inside the containers with `Runpod config file not found` / `Error: API key not found`, leaving the 5 pods idle until the initial account balance ran out at `~2026-11-23 03:06:44 UTC`).
- **Total billed GPU-hours on RunPod:** **`44.2980` GPU-hours**.
- **Total cost billed:** **`$32.28`** (`$32.2207` initial balance down to `-$0.0278`, plus `$0.0281` after `$10.00` top-up; ending balance `$9.9441`; comprises `~$31.93` pod compute/disk and `~$0.35` for the `vla-workspace` network volume at `$0.019/hr`).
- **All pods stopped and terminated:** `runpodctl pod list` verified empty (`[]`).
- **Temporary RunPod SSH key to remove:** `controls-run-2026-11-23` (ed25519 public key registered on the RunPod account for this run).
