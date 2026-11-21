"""Render LIBERO-Spatial frames on CPU and push them through OpenVLA's official image steps, with and without
the JPEG round trip, to illustrate what the evaluator's image pipeline does. Illustration only: the pilot
measured its input distances on the GPU pod (EGL on NVIDIA), this runs Mesa llvmpipe on a CPU.

Usage: python render_inputs.py <libero_root> <out_dir>
"""
import json
import os
import sys

os.environ.setdefault("MUJOCO_GL", "egl")
libero_root, out = sys.argv[1], sys.argv[2]
sys.path.insert(0, libero_root)

import numpy as np  # noqa: E402
import tensorflow as tf  # noqa: E402
from PIL import Image  # noqa: E402
from libero.libero import benchmark, get_libero_path  # noqa: E402
from libero.libero.envs import OffScreenRenderEnv  # noqa: E402

os.makedirs(out, exist_ok=True)


def official_resize(img, size=(224, 224), jpeg=True):
    """openvla experiments/robot/libero/libero_utils.py resize_image, with the JPEG round trip switchable."""
    t = tf.convert_to_tensor(np.ascontiguousarray(img), dtype=tf.uint8)
    if jpeg:
        t = tf.image.encode_jpeg(t)
        t = tf.io.decode_image(t, expand_animations=False, dtype=tf.uint8)
    t = tf.image.resize(t, size, method="lanczos3", antialias=True)
    return tf.cast(tf.clip_by_value(tf.round(t), 0, 255), tf.uint8).numpy()


def official_center_crop(img, crop_scale=0.9):
    """openvla experiments/robot/openvla_utils.py crop_and_resize (area fraction 0.9, bilinear back to 224)."""
    t = tf.image.convert_image_dtype(tf.convert_to_tensor(img), tf.float32)[None]
    side = float(np.sqrt(crop_scale))
    off = (1 - side) / 2
    t = tf.image.crop_and_resize(t, [[off, off, off + side, off + side]], [0], (224, 224))
    t = tf.clip_by_value(t[0], 0, 1)
    return tf.image.convert_image_dtype(t, tf.uint8, saturate=True).numpy()


suite = benchmark.get_benchmark_dict()["libero_spatial"]()
stats = {}
for task_id, state_idx in [(0, 0), (4, 0), (9, 0)]:
    task = suite.get_task(task_id)
    bddl = os.path.join(get_libero_path("bddl_files"), task.problem_folder, task.bddl_file)
    env = OffScreenRenderEnv(bddl_file_name=bddl, camera_heights=256, camera_widths=256)
    env.seed(0)
    env.reset()
    obs = env.set_init_state(suite.get_task_init_states(task_id)[state_idx])
    for _ in range(10):  # the official evaluation waits 10 steps for objects to settle
        obs, _, _, _ = env.step([0, 0, 0, 0, 0, 0, -1])
    raw = obs["agentview_image"][::-1, ::-1]  # rotate 180 degrees, as the official code does
    on = official_resize(raw, jpeg=True)
    off = official_resize(raw, jpeg=False)
    crop_on = official_center_crop(on)
    diff = np.abs(on.astype(np.int16) - off.astype(np.int16))
    tag = f"task{task_id}_state{state_idx}"
    Image.fromarray(np.ascontiguousarray(raw)).save(f"{out}/{tag}_render256.png")
    Image.fromarray(on).save(f"{out}/{tag}_input_jpeg_on.png")
    Image.fromarray(off).save(f"{out}/{tag}_input_jpeg_off.png")
    Image.fromarray(crop_on).save(f"{out}/{tag}_input_jpeg_on_cropped.png")
    np.save(f"{out}/{tag}_absdiff.npy", diff)
    stats[tag] = {"instruction": task.language, "mean_abs_diff": float(diff.mean()),
                  "p99_abs_diff": float(np.percentile(diff, 99)), "max_abs_diff": int(diff.max()),
                  "share_pixels_changed": float((diff.max(axis=2) > 0).mean())}
    env.close()
json.dump(stats, open(f"{out}/stats.json", "w"), indent=1)
print(json.dumps(stats, indent=1))
