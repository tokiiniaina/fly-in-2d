"""Software preview of the 3D scene (painter's algorithm, PIL only).

It rasterizes the very meshes the builders produce, with the same
isometric camera math as the game. It is NOT the Ursina render: use it
to check geometry and colors without a window.

Usage: python3 -m tools.render_preview maps/02_simple_fork.txt out.png
"""

import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from flyin.src.parser_function import MapParser
from flyin.src.viewer3d import builders
from flyin.src.viewer3d.camera import (
    PITCH,
    YAW_START,
    box_corners,
    fit_view,
    iso_axes,
)
from flyin.src.viewer3d.terrain import TerrainPlan, TerrainPlanner

SIZE = (1400, 900)
SCALE = 2
BACKGROUND_FILE = Path(__file__).resolve().parents[1] / "assets" \
    / "background" / "space.jpg"


def collect(path: Path) -> tuple[list[builders.SceneMesh], TerrainPlan]:
    """Plan a map and return every builder of the scene, and the plan."""
    data = MapParser().parse(str(path))
    plan = TerrainPlanner(data, path.name).plan()
    return builders.build_all(plan, data, path.name), plan


def render(path: Path, out: Path, yaw: float = YAW_START) -> None:
    """Draw a map to a PNG."""
    parts, plan = collect(path)
    right, up, forward = iso_axes(PITCH, yaw)
    width, height = SIZE[0] * SCALE, SIZE[1] * SCALE
    corners = box_corners(plan.bounds(main_only=True))
    fit = fit_view(corners, PITCH, yaw, width / height, 1.3)
    ppu = height / fit.fov
    color = backdrop(width, height)
    zbuf = np.full((height, width), np.inf, dtype=np.float32)
    axes = (right, up, forward)
    glass: list[tuple[float, list[Any], list[Any], float]] = []
    for part in parts:
        for vertices, tris, colors in part.builder.meshes():
            for a, b, c in tris:
                pts = [vertices[k] for k in (a, b, c)]
                cols = [colors[k] for k in (a, b, c)]
                if part.alpha < 1.0:
                    depth = sum(p[0] * forward[0] + p[1] * forward[1]
                                + p[2] * forward[2] for p in pts)
                    glass.append((depth, pts, cols, part.alpha))
                    continue
                _raster(color, zbuf, pts, cols, fit.target, axes, ppu,
                        width, height)
    glass.sort(key=lambda item: -item[0])
    for _, pts, cols, alpha in glass:
        _raster(color, zbuf, pts, cols, fit.target, axes, ppu, width,
                height, alpha)
    image = Image.fromarray(color.astype(np.uint8), "RGB")
    image.resize(SIZE, Image.LANCZOS).save(out)


def backdrop(width: int, height: int) -> Any:
    """The static galaxy image, scaled to cover the view."""
    image = Image.open(BACKGROUND_FILE).convert("RGB")
    scale = max(width / image.width, height / image.height)
    image = image.resize((round(image.width * scale),
                          round(image.height * scale)), Image.LANCZOS)
    left = (image.width - width) // 2
    top = (image.height - height) // 2
    cropped = image.crop((left, top, left + width, top + height))
    return np.asarray(cropped, dtype=np.float32).copy()


def _raster(color: Any, zbuf: Any, pts: list[Any], cols: list[Any],
            target: Any, axes: Any, ppu: float, width: int,
            height: int, alpha: float = 1.0) -> None:
    """Draw one triangle with a depth test (blended if translucent)."""
    right, up, forward = axes
    xs, ys, zs = [], [], []
    for p in pts:
        rel = (p[0] - target[0], p[1] - target[1], p[2] - target[2])
        xs.append(width / 2 + (rel[0] * right[0] + rel[1] * right[1]
                               + rel[2] * right[2]) * ppu)
        ys.append(height / 2 - (rel[0] * up[0] + rel[1] * up[1]
                                + rel[2] * up[2]) * ppu)
        zs.append(rel[0] * forward[0] + rel[1] * forward[1]
                  + rel[2] * forward[2])
    x0, x1 = max(int(min(xs)), 0), min(int(max(xs)) + 1, width - 1)
    y0, y1 = max(int(min(ys)), 0), min(int(max(ys)) + 1, height - 1)
    if x0 > x1 or y0 > y1:
        return
    px, py = np.meshgrid(np.arange(x0, x1 + 1) + 0.5,
                         np.arange(y0, y1 + 1) + 0.5)
    det = ((ys[1] - ys[2]) * (xs[0] - xs[2])
           + (xs[2] - xs[1]) * (ys[0] - ys[2]))
    if abs(det) < 1e-9:
        return
    l0 = ((ys[1] - ys[2]) * (px - xs[2])
          + (xs[2] - xs[1]) * (py - ys[2])) / det
    l1 = ((ys[2] - ys[0]) * (px - xs[2])
          + (xs[0] - xs[2]) * (py - ys[2])) / det
    l2 = 1 - l0 - l1
    inside = (l0 >= -1e-4) & (l1 >= -1e-4) & (l2 >= -1e-4)
    depth = l0 * zs[0] + l1 * zs[1] + l2 * zs[2]
    window = zbuf[y0:y1 + 1, x0:x1 + 1]
    mask = inside & (depth < window - 1e-5)
    if not mask.any():
        return
    if alpha >= 1.0:
        window[mask] = depth[mask]
    for k in range(3):
        channel = (l0 * cols[0][k] + l1 * cols[1][k]
                   + l2 * cols[2][k]) * 255
        view = color[y0:y1 + 1, x0:x1 + 1, k]
        view[mask] = view[mask] * (1.0 - alpha) + channel[mask] * alpha


if __name__ == "__main__":
    render(Path(sys.argv[1]), Path(sys.argv[2]),
           float(sys.argv[3]) if len(sys.argv) > 3 else YAW_START)
