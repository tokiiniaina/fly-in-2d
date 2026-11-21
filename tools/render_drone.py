"""Close-up software render of the 3D drone (see render_preview.py).

Usage: python3 -m tools.render_drone out.png [yaw_degrees]
"""

import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from flyin.src.viewer3d import drone_model
from flyin.src.viewer3d.camera import PITCH, YAW_START, iso_axes
from tools.render_preview import _raster


def render(out: Path, yaw: float = 225.0) -> None:
    """Draw the drone alone on a plain background."""
    width, height = 900, 900
    color = np.zeros((height, width, 3), dtype=np.float32)
    color[:] = (200, 205, 220)
    zbuf = np.full((height, width), np.inf, dtype=np.float32)
    right, up, forward = iso_axes(PITCH, YAW_START)
    rad = math.radians(yaw)
    cos, sin = math.cos(rad), math.sin(rad)
    ppu = height / 1.7
    builder = drone_model.build_static_drone()
    for vertices, tris, colors in builder.meshes():
        turned = [(x * cos + z * sin, y, -x * sin + z * cos)
                  for x, y, z in vertices]
        for a, b, c in tris:
            _raster(color, zbuf, [turned[k] for k in (a, b, c)],
                    [colors[k] for k in (a, b, c)], (0.0, -0.05, 0.0),
                    (right, up, forward), ppu, width, height)
    Image.fromarray(color.astype(np.uint8), "RGB").save(out)


if __name__ == "__main__":
    render(Path(sys.argv[1]),
           float(sys.argv[2]) if len(sys.argv) > 2 else 225.0)
