"""Generate the static galaxy backdrop (assets/background/space.jpg).

Deterministic: the same script always gives the same image.

Usage: python3 -m tools.make_space_background
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

WIDTH, HEIGHT = 2048, 1152
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "background" \
    / "space.jpg"


def fbm(rng: np.random.Generator, octaves: int = 6,
        base: int = 3) -> np.ndarray:
    """Smooth fractal noise in [0, 1] (sum of upscaled random grids)."""
    total = np.zeros((HEIGHT, WIDTH), dtype=np.float32)
    amplitude, norm = 1.0, 0.0
    for octave in range(octaves):
        cols = base * 2 ** octave + 1
        rows = max(2, round(cols * HEIGHT / WIDTH)) + 1
        grid = (rng.random((rows, cols)) * 255).astype(np.uint8)
        layer = Image.fromarray(grid).resize((WIDTH, HEIGHT),
                                             Image.BICUBIC)
        total += amplitude * np.asarray(layer, dtype=np.float32) / 255
        norm += amplitude
        amplitude *= 0.55
    return total / norm


def smooth(values: np.ndarray, low: float, high: float) -> np.ndarray:
    """Smoothstep of an array between two thresholds."""
    t = np.clip((values - low) / (high - low), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def make() -> Image.Image:
    """Build the image."""
    rng = np.random.default_rng(7)
    yy = np.linspace(0, 1, HEIGHT, dtype=np.float32)[:, None]
    xx = np.linspace(0, 1, WIDTH, dtype=np.float32)[None, :]
    top = np.array([6, 8, 24], dtype=np.float32)
    bottom = np.array([20, 12, 46], dtype=np.float32)
    image = top + (bottom - top) * yy[..., None]
    image = np.broadcast_to(image, (HEIGHT, WIDTH, 3)).copy()
    purple = np.array([118, 62, 168], dtype=np.float32)
    orange = np.array([232, 132, 74], dtype=np.float32)
    blue = np.array([54, 118, 205], dtype=np.float32)
    band = np.exp(-((xx + yy * 0.6 - 0.95) ** 2) / 0.05)
    cloud_a = smooth(fbm(rng), 0.45, 0.8) * (0.35 + band)
    cloud_b = smooth(fbm(rng), 0.5, 0.82) * np.exp(
        -((xx - 0.08) ** 2 + (yy - 0.78) ** 2) / 0.09)
    cloud_c = smooth(fbm(rng), 0.5, 0.85) * np.exp(
        -((xx - 0.55) ** 2 + (yy - 0.12) ** 2) / 0.12)
    image += purple * (cloud_a * 0.62)[..., None]
    image += orange * (cloud_b * 0.7)[..., None]
    image += blue * (cloud_c * 0.45)[..., None]
    dust = smooth(fbm(rng, 5, 4), 0.55, 0.9)
    image *= (1.0 - 0.45 * dust)[..., None]
    result = Image.fromarray(np.clip(image, 0, 255).astype(np.uint8))
    return _stars(result, rng)


def _stars(image: Image.Image, rng: np.random.Generator) -> Image.Image:
    """Add small stars, a few bright ones with a soft glow."""
    layer = np.zeros((HEIGHT, WIDTH, 3), dtype=np.float32)
    for _ in range(2600):
        x, y = int(rng.integers(0, WIDTH)), int(rng.integers(0, HEIGHT))
        level = float(rng.random()) ** 3
        tint = np.array([1.0, 0.97 - 0.2 * rng.random(),
                         0.9 + 0.1 * rng.random()], dtype=np.float32)
        layer[y, x] = np.maximum(layer[y, x], tint * (90 + 165 * level))
    glow = np.zeros_like(layer)
    for _ in range(90):
        x = int(rng.integers(2, WIDTH - 2))
        y = int(rng.integers(2, HEIGHT - 2))
        glow[y - 1:y + 2, x - 1:x + 2] = 255
        glow[y, x - 3:x + 4] = np.maximum(glow[y, x - 3:x + 4], 200)
        glow[y - 3:y + 4, x] = np.maximum(glow[y - 3:y + 4, x], 200)
    soft = Image.fromarray(glow.astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(1.6))
    base = np.asarray(image, dtype=np.float32)
    out = base + layer + np.asarray(soft, dtype=np.float32) * 0.9
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


if __name__ == "__main__":
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    make().save(OUTPUT, quality=90)
    print(f"wrote {OUTPUT} ({OUTPUT.stat().st_size // 1024} KB)")
