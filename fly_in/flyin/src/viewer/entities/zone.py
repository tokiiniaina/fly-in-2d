"""One zone of the network: a bordered block with a drop shadow."""

from typing import Any

from ursina import Entity

from flyin.src.viewer import theme
from flyin.src.viewer.animation import (
    REVEAL_TIME,
    bump,
    clamp01,
    ease_out_back,
)
from flyin.src.viewer.shapes import (
    block,
    clean,
    label,
    rounded_block,
    smooth_disc,
    tint,
)

PULSE_TIME = 0.25


class ZoneView:
    """Draw a zone from its type, its map color and its capacity.

    The block grows in when revealed and pulses when a drone lands. Both
    effects scale `root` around the center of the block.
    """

    def __init__(self, parent: Any, name: str, kind: str, x: float,
                 y: float, radius: float, color_word: str, capacity: int,
                 show_name: bool) -> None:
        """Build the layers, the marks and the labels of the zone."""
        self.name = name
        self.kind = kind
        self.x, self.y, self.radius = x, y, radius
        self.root = Entity(parent=parent, position=(x, y, theme.Z_ZONE))
        side = 2 * radius
        rim = theme.map_color(color_word) or theme.NEUTRAL_RIM
        fill = theme.ZONE_FILL[kind]
        corner = side * 0.22
        rounded_block(self.root, 0, -radius * 0.14, side, side, corner,
                      theme.SHADOW, 0.03)
        rounded_block(self.root, 0, 0, side, side, corner,
                      theme.ROAD_OUTLINE, 0.0)
        self._rim = rounded_block(self.root, 0, 0, side * 0.86,
                                  side * 0.86, corner * 0.8, rim, -0.01)
        self._rim_color = rim
        rounded_block(self.root, 0, 0, side * 0.68, side * 0.68,
                      corner * 0.6, fill, -0.02)
        rounded_block(self.root, 0, side * 0.17, side * 0.5, side * 0.2,
                      corner * 0.3, theme.lighten(fill, 0.35), -0.03)
        self._decorate(capacity)
        self._count = label(self.root, "", 0, -radius * 1.55,
                            max(radius * 16, 0.6), theme.INK,
                            theme.Z_LABEL)
        self._title(show_name)
        self._clock = 0.0
        self._reveal_delay: float | None = None
        self._pulse_at: float | None = None
        self._active = False

    def _title(self, show_name: bool) -> None:
        """Write START / END (below) or the zone name (above)."""
        r = self.radius
        size = max(r * 15, 0.6)
        if self.kind in ("start", "end"):
            text = "START" if self.kind == "start" else "END"
            label(self.root, text, 0, -r * 1.45, size, theme.INK,
                  theme.Z_LABEL)
            self._count.position = (0, -r * 2.2, theme.Z_LABEL)
            self._flag()
        elif show_name:
            label(self.root, self.name, 0, r * 1.5, size, theme.INK,
                  theme.Z_LABEL)

    def _flag(self) -> None:
        """Plant a flag on the block: plain for start, checkered for end."""
        r = self.radius
        px = -r * 0.55
        block(self.root, px, r * 1.55, r * 0.1, r * 1.2,
              theme.FLAG_POLE, -0.04)
        top = r * 1.9
        if self.kind == "start":
            block(self.root, px + r * 0.4, top, r * 0.7, r * 0.42,
                  theme.ACCENT, -0.04)
            return
        cell = r * 0.2
        for row in range(2):
            for col in range(4):
                shade = theme.INK if (row + col) % 2 == 0 else "#ffffff"
                block(self.root, px + r * 0.1 + cell * (col + 0.5),
                      top + cell * (0.5 - row), cell, cell, shade, -0.04)

    def _decorate(self, capacity: int) -> None:
        """Add the marks that tell the zone type and capacity apart."""
        r = self.radius
        if self.kind == "blocked":
            smooth_disc(self.root, 0, 0, r * 1.15, theme.TEXT, -0.04)
            smooth_disc(self.root, 0, 0, r * 0.85, theme.ZONE_FILL[
                "blocked"], -0.05)
            block(self.root, 0, 0, r * 1.0, r * 0.2, theme.TEXT, -0.06,
                  45.0)
        elif self.kind == "restricted":
            label(self.root, "x2", 0, 0, max(r * 17, 0.6), theme.INK,
                  theme.Z_LABEL)
        elif self.kind == "priority":
            for angle in (0.0, 45.0):
                block(self.root, 0, 0, r * 0.62, r * 0.62, theme.TEXT,
                      -0.04, angle)
        if capacity > 1 and self.kind not in ("start", "end", "blocked"):
            smooth_disc(self.root, r * 0.95, r * 0.95, r * 0.9,
                        theme.INK, -0.07)
            label(self.root, str(capacity), r * 0.95, r * 0.95,
                  max(r * 14, 0.55), theme.TEXT, theme.Z_LABEL)

    def reveal(self, delay: float) -> None:
        """Hide the block now and make it pop in after `delay` seconds."""
        self._clock = 0.0
        self._reveal_delay = delay
        self._active = True
        self.root.scale = (1e-3, 1e-3)

    def pulse(self, delay: float = 0.0) -> None:
        """Make the block bump, for example when a drone lands."""
        self._pulse_at = self._clock + delay
        self._active = True

    def update(self, dt: float) -> None:
        """Advance the reveal and pulse effects."""
        if not self._active:
            return
        self._clock += dt
        factor = 1.0
        if self._reveal_delay is not None:
            age = self._clock - self._reveal_delay
            factor *= ease_out_back(clamp01(age / REVEAL_TIME))
            if age >= REVEAL_TIME:
                self._reveal_delay = None
        if self._pulse_at is not None:
            age = self._clock - self._pulse_at
            factor *= bump(age, PULSE_TIME, 0.12)
            if age > PULSE_TIME:
                self._pulse_at = None
        size = max(factor, 1e-3)
        self.root.scale = (size, size)
        self._active = (self._reveal_delay is not None
                        or self._pulse_at is not None)

    def set_occupancy(self, count: int, visible: int) -> None:
        """Show how many drones are here when sprites do not show it all."""
        hub = self.kind in ("start", "end")
        show = count > visible or (hub and count > 1)
        self._count.text = clean(f"x{count}" if show else "")

    def set_delivered(self, delivered: bool) -> None:
        """Light the end hub up once at least one drone has arrived."""
        if self.kind == "end":
            self._rim.color = tint(
                theme.ACCENT if delivered else self._rim_color)
