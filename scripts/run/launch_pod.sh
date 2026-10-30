#!/usr/bin/env bash
# One pod, one cell (variant and OFT cells are checked before they start): set up the pod, then start the cell and its watchdog in tmux windows of session "night".
# Usage (inside tmux session night): launch_pod.sh <pod label> <deadline "YYYY-MM-DD HH:MM" ICT> <cell spec>
export TZ=ICT-7
source /workspace/.prompt.sh 2>/dev/null
grep -v '^python-apt' /workspace/libero-vla-eval/env/requirements-lock.txt > /root/lock.txt   # python-apt is not on PyPI
export LOCK=/root/lock.txt
bash /workspace/setup_pod.sh 2>&1 | tee /root/setup_pod.log; rc=${PIPESTATUS[0]}
echo "SETUP_DONE rc=$rc"
if [ $rc -ne 0 ]; then source /workspace/notify.sh; notify "$1: pod setup failed (rc=$rc), nothing started"; exit 1; fi
cd /workspace/runs/run_scripts
# Variant and OFT cells use new code: check it against the official image step on this pod first.
case "$3" in
  vla:*:bilinear|vla:*:render224) venv=openvla; which=openvla;;
  oft:*) venv=oft; which=oft;;
  *) which="";;
esac
if [ -n "$which" ]; then
  ( source /workspace/venvs/$venv/bin/activate; export PYTHONPATH=/workspace/LIBERO LIBERO_CONFIG_PATH=/workspace/.libero MUJOCO_GL=egl TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1
    python /workspace/runs/image_variant_code/scripts/check_image_variants.py $which ) 2>&1 | tee /root/check_image_variants.log
  grep -q CHECK_OK /root/check_image_variants.log || { source /workspace/notify.sh; notify "$1: image variant check failed, nothing started"; exit 1; }
fi
tmux new-window -d -t night -n chain "bash run_cell.sh $1 \"$2\" $3; exec bash"
tmux new-window -d -t night -n watchdog "sleep 20; bash watchdog.sh $1; exec bash"
echo "STARTED $1: $3 (deadline $2)"
