"""Evaluation image steps that can be switched off one at a time, plus helpers to record what the policy saw.

Both OpenVLA and OpenVLA-OFT resize LIBERO camera images the way their RLDS training data was built:
JPEG encode, decode, then a TensorFlow Lanczos3 resize with antialiasing. `resize_without_jpeg` is that same
resize call with the JPEG round trip removed, so a run with JPEG_ROUNDTRIP=off differs from the official
pipeline in exactly one step.

Environment variables read by the runners:
    JPEG_ROUNDTRIP=on|off   on (default) keeps the official pipeline; off skips the JPEG encode/decode.
    SAVE_POLICY_INPUTS=1    save the first image the policy receives in every episode as a lossless PNG
                            under OUT_DIR/policy_inputs/, to measure input distances between cells later.
"""
import os

import numpy as np

JPEG_ROUNDTRIP = os.environ.get("JPEG_ROUNDTRIP", "on").lower()
assert JPEG_ROUNDTRIP in ("on", "off"), f"JPEG_ROUNDTRIP must be on or off, got {JPEG_ROUNDTRIP!r}"
SAVE_POLICY_INPUTS = os.environ.get("SAVE_POLICY_INPUTS", "0") == "1"

# IMAGE_VARIANT changes one more step of the official pipeline, one at a time:
#   bilinear   - the TensorFlow resize uses method="bilinear" instead of "lanczos3" (JPEG round trip and antialias kept).
#   render224  - the simulator renders the cameras at 224x224 instead of 256x256; the resize step is kept as is
#                (resizing 224 to 224 leaves only the JPEG round trip and the Lanczos filter at scale 1).
IMAGE_VARIANT = os.environ.get("IMAGE_VARIANT", "").lower()
assert IMAGE_VARIANT in ("", "bilinear", "render224"), f"IMAGE_VARIANT must be bilinear or render224, got {IMAGE_VARIANT!r}"
assert not (IMAGE_VARIANT and JPEG_ROUNDTRIP == "off"), "change one step at a time"
RENDER_RESOLUTION = 224 if IMAGE_VARIANT == "render224" else 256


def resize_with_jpeg(img, resize_size, method):
    """The official resize (JPEG encode/decode, then `method` with antialias, round, clip to uint8).

    With method="lanczos3" this is exactly the official step; the runners check that once at start."""
    import tensorflow as tf

    if isinstance(resize_size, int):
        resize_size = (resize_size, resize_size)
    img = tf.image.encode_jpeg(np.ascontiguousarray(img))
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


def mean_abs_diff(a, b):
    """Mean absolute pixel difference of two uint8 images, in grey levels (0-255)."""
    return float(np.mean(np.abs(np.asarray(a, dtype=np.int16) - np.asarray(b, dtype=np.int16))))


def save_png(path, img):
    from PIL import Image

    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(np.asarray(img, dtype=np.uint8)).save(path)


def settings(center_crop):
    return {"jpeg_roundtrip": JPEG_ROUNDTRIP, "center_crop": center_crop, "save_policy_inputs": SAVE_POLICY_INPUTS,
            "resize_method": "bilinear" if IMAGE_VARIANT == "bilinear" else "lanczos3",
            "render_resolution": RENDER_RESOLUTION, "image_variant": IMAGE_VARIANT or "none"}
