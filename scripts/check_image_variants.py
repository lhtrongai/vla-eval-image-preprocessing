"""Check the image-variant code against the official image step before any variant cell runs.

On a real LIBERO-Spatial frame (task 0, initial state 0), rendered at 256x256:
  - ip.resize_with_jpeg(..., "lanczos3") must equal the official resize of the evaluation code given (pixel-identical);
  - ip.resize_with_jpeg(..., "bilinear") must differ from it (the variant changes the input);
and for render224 the env must return 224x224 camera images.
Usage: python check_image_variants.py openvla|oft
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import image_pipeline as ip  # noqa: E402

which = sys.argv[1]
root = {"openvla": os.environ.get("OPENVLA_ROOT", "/workspace/openvla"),
        "oft": os.environ.get("OFT_ROOT", "/workspace/openvla-oft")}[which]
sys.path.insert(0, root)
from experiments.robot.libero import libero_utils as lu  # noqa: E402
if which == "oft":  # the names the OFT evaluation script itself imported (what the wrapper replaces)
    import experiments.robot.libero.run_libero_eval as rle  # noqa: E402
from libero.libero import benchmark  # noqa: E402

suite = benchmark.get_benchmark_dict()["libero_spatial"]()
task = suite.get_task(0)
out = {}
for res in (256, 224):
    env, _ = (lu if which == "openvla" else rle).get_libero_env(task, "openvla", resolution=res)
    env.reset()
    obs = env.set_init_state(suite.get_task_init_states(0)[0])
    out[res] = obs["agentview_image"][::-1, ::-1].copy()
    env.close()
assert out[256].shape == (256, 256, 3) and out[224].shape == (224, 224, 3), {k: v.shape for k, v in out.items()}

official_fn = lu.resize_image if which == "openvla" else rle.resize_image_for_policy
official = np.asarray(official_fn(out[256], (224, 224) if which == "openvla" else 224))
mine = ip.resize_with_jpeg(out[256], 224, "lanczos3")
bil = ip.resize_with_jpeg(out[256], 224, "bilinear")
print(f"{which}: official vs resize_with_jpeg(lanczos3): identical={np.array_equal(official, mine)} "
      f"mad={ip.mean_abs_diff(official, mine):.4f}")
print(f"{which}: official vs bilinear variant: mad={ip.mean_abs_diff(official, bil):.4f} grey levels")
r224 = np.asarray(official_fn(out[224], (224, 224) if which == "openvla" else 224))
print(f"{which}: render224 input shape {r224.shape}, mad vs official 256 path={ip.mean_abs_diff(official, r224):.4f}")
assert np.array_equal(official, mine), "resize_with_jpeg does not reproduce the official step"
assert not np.array_equal(official, bil), "bilinear variant does not change the input"
print("CHECK_OK")
