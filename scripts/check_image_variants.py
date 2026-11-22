"""Check the image-variant code against the official image step before any variant cell runs.

On a real LIBERO-Spatial frame (task 0, initial state 0), rendered at 256x256:
  - ip.resize_with_jpeg(..., "lanczos3") must equal the official resize of the evaluation code given (pixel-identical);
  - ip.resize_with_jpeg(..., "bilinear") must differ from it (the variant changes the input);
  - ip.resize_with_jpeg(..., "lanczos3", quality=94) must differ from it (the JPEG-quality sham control);
and for render224 the env must return 224x224 camera images. The noise sham control is checked on the official
224x224 input: every value moves by exactly one level, the same key gives the same noise (and the digest fixed in
this file, so every machine draws the same noise), another key gives other noise, and the processor wrapper passes
the noisy image on.
Usage: python check_image_variants.py openvla|oft
"""
import hashlib
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
q94 = ip.resize_with_jpeg(out[256], 224, "lanczos3", quality=94)
print(f"{which}: official vs resize_with_jpeg(lanczos3): identical={np.array_equal(official, mine)} "
      f"mad={ip.mean_abs_diff(official, mine):.4f}")
print(f"{which}: official vs bilinear variant: mad={ip.mean_abs_diff(official, bil):.4f} grey levels")
print(f"{which}: official vs JPEG quality 94: mad={ip.mean_abs_diff(official, q94):.4f} grey levels (before the crop)")
r224 = np.asarray(official_fn(out[224], (224, 224) if which == "openvla" else 224))
print(f"{which}: render224 input shape {r224.shape}, mad vs official 256 path={ip.mean_abs_diff(official, r224):.4f}")
assert np.array_equal(official, mine), "resize_with_jpeg does not reproduce the official step"
assert not np.array_equal(official, bil), "bilinear variant does not change the input"
assert not np.array_equal(official, q94), "JPEG quality 94 does not change the input"

# Noise sham control. The reference digest was computed once when the control was written (numpy, SHAKE-256).
KEY = "noise-control|seed=1|task=0|state=0|call=0"
signs = ip.noise_signs((224, 224, 3), KEY)
assert hashlib.sha256(signs.astype("<i2").tobytes()).hexdigest() == \
    "82c123a8998a7f54d00fc16801f275d14ad9efe9acfc9bdfa6611b2da01e827a", "noise draw differs from the reference draw"
noisy = ip.add_noise(official, KEY)
step = np.abs(noisy.astype(np.int16) - official.astype(np.int16))
assert step.min() == 1 and step.max() == 1, "the noise must move every value by exactly one level"
assert np.array_equal(noisy, ip.add_noise(official, KEY)), "the same key must give the same noise"
assert not np.array_equal(noisy, ip.add_noise(official, KEY.replace("seed=1", "seed=2"))), "seeds must differ"
print(f"{which}: noise control: every value moves by 1, mad={ip.mean_abs_diff(official, noisy):.4f}")


class _Recorder:
    """Stands in for the Hugging Face processor: keeps the image it receives."""
    tokenizer = "tokenizer passes through"

    def __call__(self, text, images):
        self.text, self.image = text, np.asarray(images)
        return "processed"


from PIL import Image  # noqa: E402

calls, recorder = [], _Recorder()
wrapped = ip.NoisyProcessor(recorder, lambda: (KEY, len(calls)), lambda i, a, b: calls.append(ip.mean_abs_diff(a, b)))
assert wrapped("prompt", Image.fromarray(official)) == "processed" and recorder.text == "prompt"
assert np.array_equal(recorder.image, noisy) and calls == [1.0], "the processor wrapper must pass the noisy image on"
assert wrapped.tokenizer == recorder.tokenizer
print(f"{which}: processor wrapper passes the noisy image on")
print("CHECK_OK")
