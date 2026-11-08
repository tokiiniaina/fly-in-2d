"""Pure isometric camera math (no Ursina).

Ursina convention: X right, Y up, Z forward. A camera with pitch p
(rotation_x, looking down) and yaw w (rotation_y) looks along
(sin w cos p, -sin p, cos w cos p).
"""

import math
from dataclasses import dataclass

Vec = tuple[float, float, float]

PITCH = 35.0
YAW_START = 45.0


@dataclass(frozen=True)
class ViewFit:
    """Where to aim the camera and how large the view must be."""

    target: Vec
    fov: float


def iso_axes(pitch: float, yaw: float) -> tuple[Vec, Vec, Vec]:
    """Return the (right, up, forward) unit vectors of the camera."""
    p, w = math.radians(pitch), math.radians(yaw)
    right = (math.cos(w), 0.0, -math.sin(w))
    up = (math.sin(w) * math.sin(p), math.cos(p),
          math.cos(w) * math.sin(p))
    forward = (math.sin(w) * math.cos(p), -math.sin(p),
               math.cos(w) * math.cos(p))
    return right, up, forward


def dot(a: Vec, b: Vec) -> float:
    """Dot product."""
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def project(point: Vec, pitch: float, yaw: float) -> tuple[float, float,
                                                           float]:
    """Return (screen x, screen y, depth) of a world point."""
    right, up, forward = iso_axes(pitch, yaw)
    return dot(point, right), dot(point, up), dot(point, forward)


def box_corners(bounds: tuple[float, float, float, float, float, float]
                ) -> list[Vec]:
    """The eight corners of (min_x, max_x, min_y, max_y, min_z, max_z)."""
    x0, x1, y0, y1, z0, z1 = bounds
    return [(x, y, z) for x in (x0, x1) for y in (y0, y1)
            for z in (z0, z1)]


def fit_view(points: list[Vec], pitch: float, yaw: float, aspect: float,
             margin: float = 1.1) -> ViewFit:
    """Aim at the middle of the projected points and size the view."""
    right, up, forward = iso_axes(pitch, yaw)
    xs = [dot(p, right) for p in points]
    ys = [dot(p, up) for p in points]
    zs = [dot(p, forward) for p in points]
    mid_x = (min(xs) + max(xs)) / 2
    mid_y = (min(ys) + max(ys)) / 2
    mid_z = (min(zs) + max(zs)) / 2
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    fov = max(height, width / max(aspect, 1e-6)) * margin
    target = (right[0] * mid_x + up[0] * mid_y + forward[0] * mid_z,
              right[1] * mid_x + up[1] * mid_y + forward[1] * mid_z,
              right[2] * mid_x + up[2] * mid_y + forward[2] * mid_z)
    return ViewFit(target, max(fov, 1.0))
