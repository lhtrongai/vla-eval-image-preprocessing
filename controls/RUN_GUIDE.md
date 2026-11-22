# How to run the control cells

For whoever runs the cells of `controls/PLAN.md`. Read the plan first. Do not change the plan, `cells.json` or any script: the launch scripts refuse to start from another commit, with local changes, or with code that differs from `controls/code_sha256.txt`.

## Rules

1. **Run commit.** Everything runs from the last commit that changed `controls/code_sha256.txt`: `git log -1 --format=%H -- controls/code_sha256.txt` on a full clone. That is the plan commit, or the last correction listed under "Changes after the plan commit" in `controls/PLAN.md`, all made before any cell started.
2. **Hardware.** Every pod: host CPU `AMD EPYC 7663 56-Core Processor`, one `NVIDIA RTX PRO 4500 Blackwell` (32 GB). The CPU cannot be chosen when a pod is created, so check it first (step 2 below) and terminate a pod with any other CPU at once.
3. **One evaluation process per GPU.** Two processes on one GPU silently changed outcomes before. If fewer than five GPUs are free, run the pod labels one after another.
4. **Blind until the end.** Do not read successes or flips before every cell is done: notifications carry only exit codes and episode counts; follow progress with `wc -l` on `episodes.jsonl`; do not open `run.log` or the `EVAL-*.txt` logs during the runs.
5. **No commit from a pod or from the network volume.** Pull the logs, check them, commit from a local clone.
6. **Budget.** At most 30 GPU-hours in total, counted as billed pod time. Keep `results/controls/pods.md` (one line per pod: label, pod ID, CPU, start, end, billed hours, outcome of the run as exit code and episode count).
7. **No idle pods.** The watchdog removes each pod when its chain ends, hangs (no new episode or log line for 30 minutes) or reaches its deadline; check the console anyway and terminate by hand if a removal failed.

## Pods

RunPod Secure Cloud, in the data center of the project's network volume; template `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404`; the network volume mounted at `/workspace` (it holds `/workspace/venvs`, `/workspace/hf_cache`, `/workspace/LIBERO`, `/workspace/openvla`, `/workspace/openvla-oft`, `/workspace/libero-vla-eval`, `/workspace/setup_pod.sh` and `/workspace/notify.sh`, as for the cells of October). Name each pod by its label. All five can run at the same time.

| Pod label | Cells, in order | Expected | Deadline (watchdog) |
|---|---|---|---|
| `openvla7b-noise-seed1` | `openvla7b_spatial_sham_noise_seed1` | about 5 h | 7 h |
| `openvla7b-noise-seed2` | `openvla7b_spatial_sham_noise_seed2` | about 5 h | 7 h |
| `openvla7b-jpeg-q94` | `openvla7b_spatial_sham_jpeg_q94` | about 5 h | 7 h |
| `openvla7b-render224-cpu` | `openvla7b_spatial_render224_cpu_control` | about 4.5 h | 7 h |
| `oft-controls` | `oft_spatial_rerun_stack_check`, `oft_spatial_sham_noise_seed1`, `oft_spatial_sham_noise_seed2`, `oft_spatial_sham_jpeg_q94` | about 3.3 h | 5 h |

## Steps on each pod

1. Open a terminal on the pod and start the session the scripts use:
   ```bash
   tmux new -s controls
   ```
2. Check the CPU before anything else:
   ```bash
   lscpu | grep 'Model name'      # must print: AMD EPYC 7663 56-Core Processor
   ```
   Any other CPU: terminate this pod now and create another one (note it in `pods.md`).
3. Get the code at the run commit, on the container disk:
   ```bash
   git clone https://github.com/lhtrongai/vla-eval-image-preprocessing /root/repo
   cd /root/repo
   RUN=$(git log -1 --format=%H -- controls/code_sha256.txt)
   git checkout "$RUN"
   ```
4. Set up and start:
   ```bash
   bash controls/run_pod.sh <pod label> "$RUN"
   ```
   `run_pod.sh` checks the commit, the CPU and the GPU (`lscpu.txt`, `nvidia-smi.txt`, `gpu_name.txt`), runs the pod setup of the volume (about 10 to 20 minutes, `setup_pod.log`), copies the libero-vla-eval scripts with this repository's scripts over them to `/root/controls_code/scripts` and checks them against `controls/code_sha256.txt` (`code_check.txt`), runs `check_image_variants.py` for the pod's model (`image_check.log`, must end with `CHECK_OK`), then starts the cells (tmux window `chain`) and the watchdog (window `watchdog`). Everything it writes goes to `/workspace/runs/controls/pods/<pod label>/` on the volume. On any failure it sends a notification, starts nothing and prints `FAILED: <reason>`: terminate that pod by hand, since no watchdog runs yet. On success it prints `STARTED <pod label>`. Detach with `Ctrl-b d`.
5. Follow progress without reading results:
   ```bash
   wc -l /workspace/runs/controls/<cell>/episodes.jsonl                 # OpenVLA-7B cells
   wc -l /workspace/runs/controls/<cell>/states_*/episodes.jsonl        # OpenVLA-OFT cells
   cat /workspace/runs/controls/pods/<pod label>/chain.log              # start and end of each cell, exit codes, episode counts
   ```
6. **A cell that fails** (exit code other than 0, fewer than 500 episodes, or a watchdog notification of a hang or the deadline): note it in `pods.md`, keep its folder, and run that cell again on a new EPYC 7663 pod with the same steps and the cell name as third argument. It runs as the next attempt, in `/workspace/runs/controls/<cell>__attempt2/`:
   ```bash
   bash controls/run_pod.sh <pod label> "$RUN" <cell>
   ```
   Check the budget first: one OpenVLA-7B cell costs about 5 GPU-hours.

## Pull the logs (once, after the last pod has finished)

1. Start one short pod in the same data center with the volume attached (any type; it only reads files) and open a terminal:
   ```bash
   git clone https://github.com/lhtrongai/vla-eval-image-preprocessing /root/repo && cd /root/repo
   git checkout "$(git log -1 --format=%H -- controls/code_sha256.txt)"
   bash controls/pack_logs.sh
   ```
   It writes `/workspace/runs/controls/outbox/controls_logs.tar.gz` (episodes, run metadata, `cell.json`, evaluation logs, run logs and the pod logs; no rollout videos, no saved input images, no setup log), the md5 of every packed file (`controls_logs.md5`, inside the archive) and the md5 of the archive (`controls_logs.tar.gz.md5`).
2. Download the archive and its md5 file, in one of two ways:
   - HTTP through the pod's port 8888 (stop Jupyter first if it uses that port): `cd /workspace/runs/controls/outbox && python3 -m http.server 8888`, fetch `https://<pod ID>-8888.proxy.runpod.net/controls_logs.tar.gz` and `.../controls_logs.tar.gz.md5`, then stop the server with `Ctrl-c` at once.
   - `runpodctl send controls_logs.tar.gz` on the pod, `runpodctl receive <code>` on the receiving machine (the same for the md5 file).
3. Terminate the pod.

## Check, read and commit (on a local clone, never on a pod)

1. Check the archive and its content:
   ```bash
   md5sum -c controls_logs.tar.gz.md5
   mkdir /tmp/controls_logs && tar -xzf controls_logs.tar.gz -C /tmp/controls_logs
   (cd /tmp/controls_logs && md5sum -c outbox/controls_logs.md5)
   ```
2. Put the files in place: each cell's last attempt folder becomes `results/controls/<cell>/` (an attempt folder `<cell>__attempt2` is renamed `<cell>`), earlier failed attempts go to `results/controls/invalid/<cell>__attempt<k>/` with a line in `pods.md` saying why, and `pods/` goes to `results/controls/pods/`. Do not put any control cell directly under `results/`: the paper scripts read every folder there.
3. Read the results, once, with the script of the plan:
   ```bash
   python scripts/sham_control_analysis.py --json results/controls/summary.json > results/controls/summary.md
   ```
   Exit code 1 means a cell is missing or invalid (listed at the top of the report): run it again (step 6 above) if the budget allows; only when the budget is spent, read with `--budget-spent`. Exit code 2 means the October files differ from the plan: stop and report.
4. Before committing, check that nothing private came with the logs, for example `grep -rIlE "hf_[A-Za-z0-9]{30,}|rpa_[A-Za-z0-9]{20,}|api[_-]?key|BEGIN [A-Z ]*PRIVATE KEY" results/controls`, which must print nothing.
5. Commit under the repository author's name with a plain message and nothing else in it, add the `.log` files with `git add -f` (the repository ignores `*.log`), and push to `main`.
6. The writing branch and the CPU and stack readings are at the end of `summary.md`; apply them as sections 6, 7 and 8 of `PLAN.md` write them.
