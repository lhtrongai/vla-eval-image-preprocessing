"""How far each sham control moves the 224x224 policy input of OpenVLA-7B, next to the image steps (CPU, no rollout).

Frames: the first policy frame of initial state 0 of every LIBERO-Spatial task, rendered at 256x256 on CPU and stored
by paper/scripts/eda_frames.py (paper/eda/task*_state0_raw256.png). The resize and the crop are the functions of that
script (the official TensorFlow steps); for JPEG off and bilinear the numbers must equal the stored ones in
paper/eda/frames.jsonl, which checks that this machine computes the steps as the EDA did.
Distances: mean absolute difference over all pixels and the three channels, in intensity levels (0-255), at the
policy input (after the crop step) and, for the JPEG settings, before the crop step (what the runs log).
Usage: python controls/measure_sham_sizes.py   (needs tensorflow and Pillow; writes controls/sham_sizes.json)
"""
import json
import os
import sys

import numpy as np

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
import tensorflow as tf  # noqa: E402
from PIL import Image  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
import image_pipeline as ip  # noqa: E402


def resize(img, jpeg=True, method="lanczos3", quality=95):
    t = tf.convert_to_tensor(np.ascontiguousarray(img), dtype=tf.uint8)
    if jpeg:
        t = tf.io.decode_image(tf.image.encode_jpeg(t, quality=quality), expand_animations=False, dtype=tf.uint8)
    t = tf.image.resize(t, (224, 224), method=method, antialias=True)
    return tf.cast(tf.clip_by_value(tf.round(t), 0, 255), tf.uint8).numpy()


def crop(img, scale=0.9):
    t = tf.image.convert_image_dtype(tf.convert_to_tensor(img), tf.float32)[None]
    side = float(np.sqrt(scale)); off = (1 - side) / 2
    t = tf.image.crop_and_resize(t, [[off, off, off + side, off + side]], [0], (224, 224))
    return tf.image.convert_image_dtype(tf.clip_by_value(t[0], 0, 1), tf.uint8, saturate=True).numpy()


def changed(a, b):
    return float((np.abs(a.astype(np.int16) - b.astype(np.int16)).max(axis=2) > 0).mean())


eda = {(r["task"], r["state"]): r for r in map(json.loads, open(os.path.join(REPO, "paper/eda/frames.jsonl")))}
rows = []
for task in range(10):
    raw = np.asarray(Image.open(os.path.join(REPO, f"paper/eda/task{task}_state0_raw256.png")).convert("RGB"))
    pre = resize(raw)
    ref = crop(pre)
    jpeg_off, bil = crop(resize(raw, jpeg=False)), crop(resize(raw, method="bilinear"))
    assert abs(ip.mean_abs_diff(ref, jpeg_off) - eda[(task, 0)]["jpeg_off"]["mad"]) < 1e-12, "JPEG off differs from the EDA"
    assert abs(ip.mean_abs_diff(ref, bil) - eda[(task, 0)]["bilinear"]["mad"]) < 1e-12, "bilinear differs from the EDA"
    q94_pre = resize(raw, quality=94)
    q94 = crop(q94_pre)
    noisy = ip.add_noise(ref, f"noise-control|seed=1|task={task}|state=0|call=0")
    rows.append({"task": task,
                 "jpeg_off": ip.mean_abs_diff(ref, jpeg_off), "jpeg_off_changed": changed(ref, jpeg_off),
                 "bilinear": ip.mean_abs_diff(ref, bil), "bilinear_changed": changed(ref, bil),
                 "jpeg_q94": ip.mean_abs_diff(ref, q94), "jpeg_q94_changed": changed(ref, q94),
                 "jpeg_q94_before_crop": ip.mean_abs_diff(pre, q94_pre),
                 "noise": ip.mean_abs_diff(ref, noisy), "noise_changed": changed(ref, noisy)})

summary = {k: {"mean": float(np.mean([r[k] for r in rows])), "min": float(np.min([r[k] for r in rows])),
               "max": float(np.max([r[k] for r in rows]))} for k in rows[0] if k != "task"}
summary["_frames"] = "initial state 0 of the 10 LIBERO-Spatial tasks, CPU render (paper/eda/task*_state0_raw256.png)"
summary["_tensorflow"] = tf.__version__
with open(os.path.join(REPO, "controls", "sham_sizes.json"), "w") as f:
    json.dump(summary, f, indent=2)
    f.write("\n")
for k, v in summary.items():
    if not k.startswith("_"):
        print(f"{k:22s} mean {v['mean']:.3f}  range {v['min']:.3f}-{v['max']:.3f}")
