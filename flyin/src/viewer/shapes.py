"""Small Ursina helpers to draw flat 2D shapes and text in camera.ui."""

from typing import Any

from ursina import Entity, Mesh, Text, color

from flyin.src.viewer.geometry import (
    circle_outline,
    fan,
    rounded_rect_outline,
)


def clean(text: str) -> str:
    """Make a text safe for Ursina.

    Ursina reads '<...>' as a formatting tag and fails on an empty text,
    so angle brackets become parentheses and '' becomes a space.
    """
    text = text.replace("<", "(").replace(">", ")")
    return text if text else " "


def tint(value: str) -> Any:
    """Convert a '#rrggbb' string to an Ursina color."""
    return color.hex(value)


def block(parent: Any, x: float, y: float, width: float, height: float,
          fill: str, z: float = 0.0, angle: float = 0.0) -> Any:
    """Draw a filled rectangle, optionally rotated by `angle` degrees."""
    return Entity(parent=parent, model="quad", color=tint(fill),
                  position=(x, y, z), scale=(width, height),
                  rotation_z=angle)


def rounded_block(parent: Any, x: float, y: float, width: float,
                  height: float, radius: float, fill: str,
                  z: float = 0.0) -> Any:
    """Draw a rounded rectangle as one flat mesh."""
    vertices, triangles = fan(rounded_rect_outline(width, height, radius))
    return Entity(parent=parent, model=Mesh(vertices=vertices,
                                            triangles=triangles),
                  color=tint(fill), double_sided=True,
                  position=(x, y, z))


def smooth_disc(parent: Any, x: float, y: float, diameter: float,
                fill: str, z: float = 0.0) -> Any:
    """Draw a circle as one flat mesh (no dependency on a model name)."""
    vertices, triangles = fan(circle_outline(diameter / 2, 20))
    return Entity(parent=parent, model=Mesh(vertices=vertices,
                                            triangles=triangles),
                  color=tint(fill), double_sided=True,
                  position=(x, y, z))


def label(parent: Any, text: str, x: float, y: float, size: float,
          fill: str, z: float = -0.2,
          origin: tuple[float, float] = (0, 0)) -> Any:
    """Draw a text line."""
    return Text(text=clean(text), parent=parent, position=(x, y, z),
                origin=origin, scale=size, color=tint(fill))
