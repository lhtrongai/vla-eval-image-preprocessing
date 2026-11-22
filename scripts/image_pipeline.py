"""Evaluation image steps that can be switched off one at a time, plus helpers to record what the policy saw.

Both OpenVLA and OpenVLA-OFT resize LIBERO camera images the way their RLDS training data was built:
JPEG encode, decode, then a TensorFlow Lanczos3 resize with antialiasing. `resize_without_jpeg` is that same
resize call with the JPEG round trip removed, so a run with JPEG_ROUNDTRIP=off differs from the official
pipeline in exactly one step.

Environment variables read by the runners:
    JPEG_ROUNDTRIP=on|off   on (default) keeps the official pipeline; off skips the JPEG encode/decode.
    SAVE_POLICY_INPUTS=1    save the first image the policy receives in every episode as a lossless PNG
                            under OUT_DIR/policy_inputs/, to measure input distances between cells later.
    IMAGE_VARIANT=...       one more change, see below.
    NOISE_SEED=k            draw of the noise control (IMAGE_VARIANT=noise only), a positive integer.
"""
import hashlib
import os

import numpy as np

JPEG_ROUNDTRIP = os.environ.get("JPEG_ROUNDTRIP", "on").lower()
assert JPEG_ROUNDTRIP in ("on", "off"), f"JPEG_ROUNDTRIP must be on or off, got {JPEG_ROUNDTRIP!r}"
SAVE_POLICY_INPUTS = os.environ.get("SAVE_POLICY_INPUTS", "0") == "1"

# IMAGE_VARIANT changes one more step of the official pipeline, one at a time:
#   bilinear   - the TensorFlow resize uses method="bilinear" instead of "lanczos3" (JPEG round trip and antialias kept).
#   render224  - the simulator renders the cameras at 224x224 instead of 256x256; the resize step is kept as is
#                (resizing 224 to 224 leaves only the JPEG round trip and the Lanczos filter at scale 1).
# Two more values are sham controls: changes that belong to no evaluation pipeline and carry no information, with a
# pixel change of the same size as the steps above (controls/PLAN.md):
#   jpeg_q94   - the JPEG round trip encodes at quality 94 instead of 95, the default of tf.image.encode_jpeg that the
#                official step uses; everything else is official.
#   noise      - every image the policy receives (the processor input, after the crop step) moves by exactly one
#                intensity level in every value, +1 or -1 drawn from SHAKE-256 of a key (NOISE_SEED, task, initial
#                state, processor call), reflected at 0 and 255; every image step stays official.
IMAGE_VARIANT = os.environ.get("IMAGE_VARIANT", "").lower()
assert IMAGE_VARIANT in ("", "bilinear", "render224", "jpeg_q94", "noise"), \
    f"IMAGE_VARIANT must be bilinear, render224, jpeg_q94 or noise, got {IMAGE_VARIANT!r}"
assert not (IMAGE_VARIANT and JPEG_ROUNDTRIP == "off"), "change one step at a time"
RENDER_RESOLUTION = 224 if IMAGE_VARIANT == "render224" else 256
OFFICIAL_JPEG_QUALITY = 95
JPEG_QUALITY = 94 if IMAGE_VARIANT == "jpeg_q94" else OFFICIAL_JPEG_QUALITY
_noise_seed = os.environ.get("NOISE_SEED")
if IMAGE_VARIANT == "noise":
    assert _noise_seed is not None and _noise_seed.isdigit() and int(_noise_seed) > 0, \
        "IMAGE_VARIANT=noise needs NOISE_SEED=<positive integer>"
else:
    assert _noise_seed is None, "NOISE_SEED is only read with IMAGE_VARIANT=noise"
NOISE_SEED = int(_noise_seed) if _noise_seed is not None else None


def resize_with_jpeg(img, resize_size, method, quality=OFFICIAL_JPEG_QUALITY):
    """The official resize (JPEG encode/decode, then `method` with antialias, round, clip to uint8).

    With method="lanczos3" and quality 95 this is exactly the official step; the runners check that once at start."""
    import tensorflow as tf

    if isinstance(resize_size, int):
        resize_size = (resize_size, resize_size)
    img = tf.image.encode_jpeg(np.ascontiguousarray(img), quality=quality)
    img = tf.io.decode_image(img, expand_animations=False, dtype=tf.uint8)
    img = tf.image.resize(img, resize_size, method=method, antialias=True)
    img = tf.cast(tf.clip_by_value(tf.round(img), 0, 255), tf.uint8)
    return img.numpy()


def resize_without_jpeg(img, resize_size):
    """The official resize (Lanczos3, antialias, round, clip to uint8) without the JPEG round trip."""
    import tensorflow as tf

    if isinstance(resize_size, int):
        resize_size = (resize_size, resize_size)
    img = tf.convert_to_tensor(np.ascontiguousarray(img), dtype=tf.uint8)
    img = tf.image.resize(img, resize_size, method="lanczos3", antialias=True)
    img = tf.cast(tf.clip_by_value(tf.round(img), 0, 255), tf.uint8)
    return img.numpy()


def guarded(fn, *args, **kwargs):
    """Run a control step; an error stops the whole run instead of counting as a failed episode.

    The original evaluation loops catch every Exception inside an episode and score the episode as a failure, so
    an error in new code would look like a result. SystemExit is not an Exception and passes through those loops."""
    try:
        return fn(*args, **kwargs)
    except Exception as e:  # noqa: BLE001
        raise SystemExit(f"control step {getattr(fn, '__name__', fn)} failed: {e!r}") from e


def noise_key(task_id, initial_state, call_index):
    """Key of the noise drawn for one processor call; the same key gives the same noise on every machine."""
    return f"noise-control|seed={NOISE_SEED}|task={int(task_id)}|state={int(initial_state)}|call={int(call_index)}"


def noise_signs(shape, key):
    """+1 or -1 for every value of an array of `shape`: the bits of SHAKE-256(key), in C order."""
    n = int(np.prod(shape))
    raw = np.frombuffer(hashlib.shake_256(key.encode()).digest((n + 7) // 8), dtype=np.uint8)
    return (np.unpackbits(raw)[:n].astype(np.int16) * 2 - 1).reshape(shape)


def add_noise(img, key):
    """The noise control on one uint8 image: every value moves by exactly one level, reflected at 0 and 255."""
    img = np.asarray(img, dtype=np.uint8)
    delta = noise_signs(img.shape, key)
    delta[img == 0] = 1
    delta[img == 255] = -1
    return (img.astype(np.int16) + delta).astype(np.uint8)


class NoisyProcessor:
    """Wraps the policy's Hugging Face processor so that every image it receives gets the noise control.

    Both evaluation scripts call processor(prompt, image) with the PIL image after the crop step; OpenVLA-OFT calls it
    for the third-person image and then for the wrist image of every query. key_fn() returns (key, call index) and
    counts the call; on_call(call index, image before, image after) lets the runner record the change."""

    def __init__(self, processor, key_fn, on_call):
        self._processor = processor
        self._key_fn = key_fn
        self._on_call = on_call

    def __getattr__(self, name):
        return getattr(self._processor, name)

    def __call__(self, *args, **kwargs):
        args, kwargs = guarded(self._perturb, list(args), dict(kwargs))
        return self._processor(*args, **kwargs)

    def _perturb(self, args, kwargs):
        from PIL import Image

        if len(args) >= 2:
            image = args[1]
        elif "images" in kwargs:
            image = kwargs["images"]
        else:
            raise ValueError("no image among the processor arguments")
        assert isinstance(image, Image.Image) and image.mode == "RGB", f"unexpected processor image {type(image)}"
        before = np.asarray(image, dtype=np.uint8)
        key, index = self._key_fn()
        after = add_noise(before, key)
        noisy = Image.fromarray(after)
        if len(args) >= 2:
            args[1] = noisy
        else:
            kwargs["images"] = noisy
        self._on_call(index, before, after)
        return args, kwargs


def file_sha256(paths):
    """SHA-256 of each file, keyed by file name (recorded in run_meta.json, checked by the control analysis)."""
    out = {}
    for p in paths:
        with open(p, "rb") as f:
            out[os.path.basename(p)] = hashlib.sha256(f.read()).hexdigest()
    return out


def mean_abs_diff(a, b):
    """Mean absolute pixel difference of two uint8 images, in grey levels (0-255)."""
    return float(np.mean(np.abs(np.asarray(a, dtype=np.int16) - np.asarray(b, dtype=np.int16))))


def save_png(path, img):
    from PIL import Image

    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(np.asarray(img, dtype=np.uint8)).save(path)


def settings(center_crop):
    s = {"jpeg_roundtrip": JPEG_ROUNDTRIP, "center_crop": center_crop, "save_policy_inputs": SAVE_POLICY_INPUTS,
         "resize_method": "bilinear" if IMAGE_VARIANT == "bilinear" else "lanczos3",
         "render_resolution": RENDER_RESOLUTION, "image_variant": IMAGE_VARIANT or "none", "jpeg_quality": JPEG_QUALITY}
    if IMAGE_VARIANT == "noise":
        s["noise_seed"] = NOISE_SEED
        s["noise"] = ("+1 or -1 on every value of every processor input (after the crop step), from SHAKE-256 of "
                      "the key noise-control|seed|task|state|call, reflected at 0 and 255")
    return s
