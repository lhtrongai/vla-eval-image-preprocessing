#!/usr/bin/env bash
# Set up one pod for its control cells and start them (controls/RUN_GUIDE.md). Run inside tmux session "controls":
#   bash controls/run_pod.sh <pod label from controls/cells.json> <run commit (controls/RUN_GUIDE.md, rule 1)> [<cell of that pod>]
# With a cell name, only that cell runs, as its next attempt (a rerun of a failed or invalid cell).
# The repository clone must be on the container disk (not the network volume) and at the run commit.
export TZ=ICT-7
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(dirname "$HERE")
LABEL=$1
PLAN=$2
ONLY=${3:+--only $3}
LOG=/workspace/runs/controls/pods/$LABEL
mkdir -p "$LOG"
source /workspace/notify.sh 2>/dev/null || notify() { echo "notify: $*"; }
fail() { notify "$LABEL: $1, nothing started"; echo "FAILED: $1"; exit 1; }

# 1. Run commit and hardware, before anything is installed.
[ "$(git -C "$REPO" rev-parse HEAD)" = "$(git -C "$REPO" rev-parse "$PLAN^{commit}")" ] || fail "repository is not at the run commit"
git -C "$REPO" diff --quiet HEAD || fail "repository has local changes"
lscpu > "$LOG/lscpu.txt"; nvidia-smi > "$LOG/nvidia-smi.txt" 2>&1
grep -q "^Model name: *AMD EPYC 7663 56-Core Processor" "$LOG/lscpu.txt" \
  || fail "CPU is not an EPYC 7663 ($(grep '^Model name' "$LOG/lscpu.txt" | sed 's/  */ /g')), terminate this pod"
nvidia-smi --query-gpu=name --format=csv,noheader > "$LOG/gpu_name.txt" 2>&1
# The nvidia-smi table cuts long names ("NVIDIA RTX PRO 4500 Blac..."), so the check reads the query form.
[ "$(wc -l < "$LOG/gpu_name.txt")" -eq 1 ] && grep -qx "NVIDIA RTX PRO 4500 Blackwell" "$LOG/gpu_name.txt" \
  || fail "GPU is not one RTX PRO 4500 Blackwell ($(tr '\n' ';' < "$LOG/gpu_name.txt")), terminate this pod"
python3 "$HERE/run_cell.py" --deadline-seconds "$LABEL" > /dev/null || fail "unknown pod label $LABEL"

# 2. Environment, as for the cells of 28-29 October (scripts/run/launch_pod.sh).
source /workspace/.prompt.sh 2>/dev/null
grep -v '^python-apt' /workspace/libero-vla-eval/env/requirements-lock.txt > /root/lock.txt   # python-apt is not on PyPI
export LOCK=/root/lock.txt
bash /workspace/setup_pod.sh > "$LOG/setup_pod.log" 2>&1 || fail "pod setup failed (see $LOG/setup_pod.log)"

# 3. Code: the libero-vla-eval scripts with this repository's scripts copied over them, checked byte for byte.
CODE=$(python3 -c "import json; print(json.load(open('$HERE/cells.json'))['code_dir'])")
rm -rf "$CODE"; mkdir -p "$CODE"
cp -r /workspace/libero-vla-eval/scripts/. "$CODE/" && cp "$REPO"/scripts/*.py "$CODE/" || fail "could not copy the code"
(cd "$REPO" && sha256sum -c controls/code_sha256.txt) > "$LOG/code_check.txt" 2>&1 || fail "code differs from controls/code_sha256.txt"
sha256sum "$CODE"/episode_logging.py "$CODE"/per_camera_textures.py >> "$LOG/code_check.txt"

# 4. Image check against the official step, for the models of this pod.
python3 "$HERE/run_cell.py" --image-check "$LABEL" > "$LOG/image_check.log" 2>&1 || fail "image check failed (see $LOG/image_check.log)"

# 5. The cells, one after the other, and the watchdog that removes the pod at the end.
tmux has-session -t controls 2>/dev/null || tmux new-session -d -s controls
tmux new-window -d -t controls -n chain "python3 $HERE/run_cell.py --pod $LABEL $ONLY; exec bash"
tmux new-window -d -t controls -n watchdog "sleep 30; bash $HERE/watchdog.sh $LABEL; exec bash"
notify "$LABEL: started on $(grep '^Model name' "$LOG/lscpu.txt" | sed 's/.*: *//')"
echo "STARTED $LABEL"
