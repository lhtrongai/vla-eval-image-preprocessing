"""Image-level EDA on CPU: how far each evaluation image step, a grayscale input and ImageNet-C JPEG corruption
move the 224x224 RGB policy input of OpenVLA's official LIBERO pipeline.

Frames: LIBERO-Spatial, tasks 0-9, stored initial states 0..N-1, first policy frame (after the 10 settle steps),
rendered on CPU (Mesa llvmpipe), so fixture placement and rendering can differ slightly from the GPU runs.
Distances: mean absolute difference over all pixels and the three RGB channels, in intensity levels (0-255).
Usage: python eda_frames.py <libero_root> <out_dir> <n_states>
"""
import io
import json
import os
import sys
import time

os.environ.setdefault("MUJOCO_GL", "egl")
libero_root, out, n_states = sys.argv[1], sys.argv[2], int(sys.argv[3])
sys.path.insert(0, libero_root)

import numpy as np  # noqa: E402
import tensorflow as tf  # noqa: E402
from PIL import Image  # noqa: E402
from libero.libero import benchmark, get_libero_path  # noqa: E402
from libero.libero.envs import OffScreenRenderEnv  # noqa: E402

os.makedirs(out, exist_ok=True)


def resize(img, jpeg=True, method="lanczos3"):
    """openvla libero_utils.resize_image: JPEG encode/decode, resize with antialias, round, clip (switchable)."""
    t = tf.convert_to_tensor(np.ascontiguousarray(img), dtype=tf.uint8)
    if jpeg:
        t = tf.io.decode_image(tf.image.encode_jpeg(t), expand_animations=False, dtype=tf.uint8)
    t = tf.image.resize(t, (224, 224), method=method, antialias=True)
    return tf.cast(tf.clip_by_value(tf.round(t), 0, 255), tf.uint8).numpy()


def crop(img, scale=0.9):
    """openvla openvla_utils.crop_and_resize: central crop of 90% of the area, bilinear back to 224x224."""
    t = tf.image.convert_image_dtype(tf.convert_to_tensor(img), tf.float32)[None]
    side = float(np.sqrt(scale)); off = (1 - side) / 2
    t = tf.image.crop_and_resize(t, [[off, off, off + side, off + side]], [0], (224, 224))
    return tf.image.convert_image_dtype(tf.clip_by_value(t[0], 0, 1), tf.uint8, saturate=True).numpy()


def gray(img):
    """Luminance (tf.image.rgb_to_grayscale, ITU-R BT.601 weights) copied to the three channels."""
    g = tf.image.rgb_to_grayscale(tf.image.convert_image_dtype(tf.convert_to_tensor(img), tf.float32))
    g = tf.image.convert_image_dtype(g, tf.uint8, saturate=True).numpy()
    return np.repeat(g, 3, axis=2)


def jpeg_pil(img, quality):
    """ImageNet-C jpeg_compression: save with PIL at the given quality, reload."""
    buf = io.BytesIO(); Image.fromarray(img).save(buf, "JPEG", quality=quality)
    return np.array(Image.open(buf))


def stats(a, b):
    d = np.abs(a.astype(np.int16) - b.astype(np.int16))
    return {"mad": float(d.mean()), "p99": float(np.percentile(d, 99)), "max": int(d.max()),
            "changed": float((d.max(axis=2) > 0).mean())}


def first_frame(env, state):
    env.seed(0); env.reset()
    obs = env.set_init_state(state)
    for _ in range(10):  # the official evaluation waits 10 steps for objects to settle
        obs, _, _, _ = env.step([0, 0, 0, 0, 0, 0, -1])
    return obs["agentview_image"][::-1, ::-1].copy()  # 180-degree rotation, as the official code does


suite = benchmark.get_benchmark_dict()["libero_spatial"]()
rows = open(os.path.join(out, "frames.jsonl"), "a")
done = {(json.loads(l)["task"], json.loads(l)["state"]) for l in open(os.path.join(out, "frames.jsonl"))}
for task_id in range(10):
    task = suite.get_task(task_id)
    bddl = os.path.join(get_libero_path("bddl_files"), task.problem_folder, task.bddl_file)
    states = suite.get_task_init_states(task_id)
    todo = [s for s in range(n_states) if (task_id, s) not in done]
    if not todo:
        continue
    raws = {}
    for res in (256, 224):
        env = OffScreenRenderEnv(bddl_file_name=bddl, camera_heights=res, camera_widths=res)
        raws[res] = {s: first_frame(env, states[s]) for s in todo}
        env.close()
    for s in todo:
        t0 = time.time()
        raw, raw224 = raws[256][s], raws[224][s]
        pre = resize(raw)                       # official resize, before the crop step
        ref = crop(pre)                         # official policy input
        r = {"task": task_id, "state": s,
             "jpeg_off_precrop": stats(pre, resize(raw, jpeg=False)),   # what the runs record as jpeg_input_mad
             "jpeg_off": stats(ref, crop(resize(raw, jpeg=False))),
             "bilinear": stats(ref, crop(resize(raw, method="bilinear"))),
             "render224": stats(ref, crop(resize(raw224))),
             "crop_off": stats(ref, pre),
             "grayscale": stats(ref, gray(ref))}
        for sev, q in enumerate([25, 18, 15, 10, 7], start=1):
            r[f"imagenetc_jpeg_s{sev}"] = stats(ref, jpeg_pil(ref, q))
        if s == 0:
            for name, img in (("raw256", raw), ("ref", ref), ("gray", gray(ref)), ("jpeg_off", crop(resize(raw, jpeg=False))),
                              ("crop_off", pre), ("jpeg_q15", jpeg_pil(ref, 15))):
                Image.fromarray(np.ascontiguousarray(img)).save(os.path.join(out, f"task{task_id}_state0_{name}.png"))
        rows.write(json.dumps(r) + "\n"); rows.flush()
    print(f"task {task_id} done ({len(todo)} states)", flush=True)
print("EDA_DONE")
