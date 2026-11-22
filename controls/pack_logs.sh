#!/usr/bin/env bash
# Pack the logs of every control cell on the network volume for download, without rollout videos, saved input
# images or the pod setup log, and write an md5 list of every packed file (controls/RUN_GUIDE.md, step 7).
# Usage, on any pod with the volume at /workspace:  bash controls/pack_logs.sh
#   -> /workspace/runs/controls/outbox/controls_logs.tar.gz, controls_logs.md5 (files) and controls_logs.tar.gz.md5
set -eu
cd /workspace/runs/controls
mkdir -p outbox
find . -path ./outbox -prune -o -type f \( -name episodes.jsonl -o -name run_meta.json -o -name cell.json \
  -o -name 'EVAL-*.txt' -o -name run.log -o -name chain.log -o -name lscpu.txt -o -name nvidia-smi.txt \
  -o -name image_check.log -o -name code_check.txt \) -print | sort > outbox/files.txt
xargs -d '\n' md5sum < outbox/files.txt > outbox/controls_logs.md5
tar -czf outbox/controls_logs.tar.gz -T outbox/files.txt outbox/controls_logs.md5
(cd outbox && md5sum controls_logs.tar.gz > controls_logs.tar.gz.md5)   # bare file name: checked next to the download
echo "$(wc -l < outbox/files.txt) files packed:"; cat outbox/controls_logs.tar.gz.md5
