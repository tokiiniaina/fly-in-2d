"""A drone sprite with a soft ground shadow."""

from typing import Any

from ursina import Entity

from flyin.src.viewer import theme
from flyin.src.viewer.shapes import smooth_disc


class DroneView:
    """One sprite, kept in a pool and driven by the animator."""

    def __init__(self, parent: Any, drone_id: int, texture: Any,
                 aspect: float, height: float) -> None:
        """Create a hidden sprite that keeps the image aspect ratio."""
        self.drone_id = drone_id
        self._width = height * aspect
        self._height = height
        self.shadow = smooth_disc(parent, 0, 0, 1.0, theme.INK,
                                  theme.Z_DRONE + 0.05)
        self.shadow.alpha = 0.28
        self.shadow.enabled = False
        self.entity = Entity(
            parent=parent, model="quad", texture=texture,
            scale=(self._width, self._height),
            position=(0, 0, theme.Z_DRONE), enabled=False)

    def apply(self, x: float, y: float, visible: bool,
              scale_x: float = 1.0, scale_y: float = 1.0,
              lift: float = 0.0) -> None:
        """Draw the sprite at (x, y), floating `lift` above its shadow."""
        height = self._height
        self.entity.position = (x, y + lift, theme.Z_DRONE)
        self.entity.scale = (self._width * scale_x, height * scale_y)
        self.entity.enabled = visible
        squeeze = max(1.0 - 4.0 * lift / height, 0.5)
        self.shadow.position = (x, y - height * 0.42,
                                theme.Z_DRONE + 0.05)
        self.shadow.scale = (self._width * 0.62 * scale_x * squeeze,
                             height * 0.16 * scale_y)
        self.shadow.enabled = visible

    def place(self, x: float, y: float) -> None:
        """Show the sprite, motionless, at a screen position."""
        self.apply(x, y, True)

    def set_texture(self, texture: Any) -> None:
        """Change the image."""
        self.entity.texture = texture

    def hide(self) -> None:
        """Hide the sprite and its shadow."""
        self.entity.enabled = False
        self.shadow.enabled = False
