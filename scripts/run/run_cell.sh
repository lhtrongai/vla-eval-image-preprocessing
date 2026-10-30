#!/usr/bin/env bash
# Image-pipeline cell on LIBERO-Spatial, all 500 stored initial states (one cell per pod).
# Reference-pipeline cells (jpeg_off, crop_off, rerun on OpenVLA-7B) use the libero-vla-eval scripts unchanged;
# variant cells (bilinear, render224) and every OFT cell use the variant copy of the scripts (this repository's scripts/);
# OFT cells run initial states 0-19 and 20-49 as two runs, like the OFT reference cell they are paired with.
# Usage: run_cell.sh <pod label> <deadline "YYYY-MM-DD HH:MM" ICT> <cell spec>...
# Cell spec: <model>:<cell name>:<JPEG_ROUNDTRIP>:<center crop True|False>[:<bilinear|render224>]
source /workspace/notify.sh
D=2026-10-28; L=/workspace/runs/$1_$D; DEADLINE="$2"; shift 2
mkdir -p $L; echo "$DEADLINE" > $L/deadline.txt
export HF_HOME=/workspace/hf_cache HF_HUB_ENABLE_HF_TRANSFER=0 MUJOCO_GL=egl TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1 TZ=ICT-7
export PYTHONPATH=/workspace/LIBERO LIBERO_CONFIG_PATH=/workspace/.libero SAVE_POLICY_INPUTS=1
V=/workspace/runs/image_variant_code/scripts
vla() { (source /workspace/venvs/openvla/bin/activate; OUT_DIR=$1 JPEG_ROUNDTRIP=$2 python $S/run_openvla_libero_logged.py \
  --model_family openvla --pretrained_checkpoint openvla/openvla-7b-finetuned-libero-spatial \
  --task_suite_name libero_spatial --center_crop $3 --num_trials_per_task 50 --seed 7); }
oftrun() { (source /workspace/venvs/oft/bin/activate; OUT_DIR=$1 JPEG_ROUNDTRIP=$2 INIT_OFFSET=$4 python $V/run_oft_libero_logged.py \
  --pretrained_checkpoint moojink/openvla-7b-oft-finetuned-libero-spatial --task_suite_name libero_spatial \
  --center_crop $3 --num_trials_per_task $5 --env_img_res $RES --local_log_dir $1); }
oft() { oftrun $1/states_0-19 $2 $3 0 20 && oftrun $1/states_20-49 $2 $3 20 30
        local rc=$?; cat $1/states_0-19/episodes.jsonl $1/states_20-49/episodes.jsonl > $1/episodes.jsonl 2>/dev/null; return $rc; }
for spec in "$@"; do
  IFS=: read model name jpeg crop variant <<< "$spec"
  O=/workspace/runs/${name}_$D; mkdir -p $O
  export IMAGE_VARIANT=${variant:-}; RES=256; [ "$variant" = render224 ] && RES=224
  if [ -n "$variant" ] || [ $model = oft ]; then S=$V
    [ -f $V/image_pipeline.py ] || { notify "$name: variant code missing in $V, cell skipped"; date "+%F %T skip $name (no variant code)" >> $L/chain.log; continue; }
  else S=/workspace/libero-vla-eval/scripts; fi
  date "+%F %T start $name" >> $L/chain.log
  $model $O $jpeg $crop > $O/run.log 2>&1; rc=$?
  n=$(wc -l < $O/episodes.jsonl 2>/dev/null || echo 0); k=$(grep -c '"success": true' $O/episodes.jsonl 2>/dev/null || echo 0)
  date "+%F %T end $name rc=$rc $k/$n" >> $L/chain.log
  notify "$name: $k/$n success (exit $rc)"
done
date "+%F %T chain finished" >> $L/chain.log
