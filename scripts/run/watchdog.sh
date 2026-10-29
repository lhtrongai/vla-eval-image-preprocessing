#!/usr/bin/env bash
# Stop this pod when its first cell ends (one cell per pod) or the chain finishes, when no run.log under its cells changed for 30 min (hang), or at the deadline.
# Usage: watchdog.sh <pod label>   (reads the cells from chain.log, the deadline from deadline.txt)
source /workspace/notify.sh
L=/workspace/runs/$1_2026-10-28; DEADLINE=$(TZ=ICT-7 date -d "$(cat $L/deadline.txt)" +%s)
bye() { notify "$1 watchdog: $2, removing pod"
        date "+%F %T watchdog: $2, removing pod" >> $L/chain.log
        runpodctl remove pod "$RUNPOD_POD_ID" >> $L/chain.log 2>&1 \
          || notify "$1: could not remove pod $RUNPOD_POD_ID, please stop it"
        exit 0; }
sleep 600
while true; do
  now=$(date +%s)
  grep -qE "chain finished| end " $L/chain.log 2>/dev/null && { sleep 60; bye $1 "chain finished"; }
  [ $now -ge $DEADLINE ] && bye $1 "deadline $(cat $L/deadline.txt)"
  cur=$(grep "start" $L/chain.log | tail -1 | awk '{print $4}')
  f=/workspace/runs/${cur}_2026-10-28/run.log
  newest=$(stat -c %Y $f 2>/dev/null || echo $now)
  [ $((now - newest)) -gt 1800 ] && bye $1 "no new log in $cur for 30 min (hang)"
  sleep 120
done
