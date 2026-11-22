#!/usr/bin/env bash
# Remove this pod when its chain has finished, when no episode or log line has been written for 30 minutes (hang),
# or at the pod's deadline in controls/cells.json. Logs stay on the network volume.
# Usage: bash controls/watchdog.sh <pod label>
HERE=$(cd "$(dirname "$0")" && pwd)
L=/workspace/runs/controls/pods/$1
source /workspace/notify.sh 2>/dev/null || notify() { echo "notify: $*"; }
DEADLINE=$(( $(date +%s) + $(python3 "$HERE/run_cell.py" --deadline-seconds "$1") ))
bye() {
  notify "$1 watchdog: $2, removing pod"
  date "+%F %T watchdog: $2, removing pod" >> "$L/chain.log"
  runpodctl remove pod "$RUNPOD_POD_ID" >> "$L/chain.log" 2>&1 \
    || notify "$1: could not remove pod $RUNPOD_POD_ID, stop and terminate it by hand"
  exit 0
}
sleep 600
while true; do
  now=$(date +%s)
  grep -q "chain finished" "$L/chain.log" 2>/dev/null && { sleep 60; bye "$1" "chain finished"; }
  [ "$now" -ge "$DEADLINE" ] && bye "$1" "deadline"
  seg=$(grep " start " "$L/chain.log" 2>/dev/null | tail -1 | awk '{print $5}')
  newest=$now
  if [ -n "$seg" ]; then
    newest=$(stat -c %Y "$seg/run.log" "$seg/episodes.jsonl" 2>/dev/null | sort -n | tail -1)
    newest=${newest:-$now}
  fi
  [ $((now - newest)) -gt 1800 ] && bye "$1" "no new episode or log line in $seg for 30 min (hang)"
  sleep 120
done
