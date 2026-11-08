"""Pure geometry: fit a map into a screen rectangle (no Ursina)."""

import math
from dataclasses import dataclass

from flyin.src.map_data import MapData

MAX_VISIBLE_DRONES = 4


@dataclass(frozen=True)
class Rect:
    """A rectangle in camera.ui units, given by center and size."""

    cx: float
    cy: float
    width: float
    height: float


def _clamp(value: float, low: float, high: float) -> float:
    """Limit a value to the range [low, high]."""
    return max(low, min(high, value))


class NetworkLayout:
    """Map coordinates to screen positions and element sizes.

    The map is centered in the area, scaled uniformly (relative positions
    and topology are preserved) and never scaled above `max_unit`, so a
    tiny map does not become gigantic.
    """

    def __init__(self, data: MapData, area: Rect,
                 margin: float = 0.07, max_unit: float = 0.2) -> None:
        """Compute the screen position of every zone."""
        self.area = area
        margin = min(margin, 0.25 * min(area.width, area.height))
        xs = [zone.x for zone in data.zones.values()]
        ys = [zone.y for zone in data.zones.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        limits = [max_unit]
        if max_x > min_x:
            limits.append((area.width - 2 * margin) / (max_x - min_x))
        if max_y > min_y:
            limits.append((area.height - 2 * margin) / (max_y - min_y))
        self.unit: float = max(min(limits), 1e-4)
        mid_x = (min_x + max_x) / 2
        mid_y = (min_y + max_y) / 2
        self.positions: dict[str, tuple[float, float]] = {
            name: (area.cx + (zone.x - mid_x) * self.unit,
                   area.cy + (zone.y - mid_y) * self.unit)
            for name, zone in data.zones.items()
        }
        gap = self._min_gap(data)
        self.gap: float | None = gap
        self.node_radius: float = (
            0.05 if gap is None else _clamp(0.32 * gap, 0.011, 0.06))

    def _min_gap(self, data: MapData) -> float | None:
        """Smallest on-screen distance between two linked zones."""
        pairs = [(c.zone1, c.zone2) for c in data.connections]
        names = list(self.positions)
        if len(names) <= 300:
            pairs += [(a, b) for i, a in enumerate(names)
                      for b in names[i + 1:]]
        best: float | None = None
        for first, second in pairs:
            ax, ay = self.positions[first]
            bx, by = self.positions[second]
            dist = math.hypot(ax - bx, ay - by)
            if dist > 1e-9 and (best is None or dist < best):
                best = dist
        return best

    @property
    def label_size(self) -> float:
        """Text scale of the zone name labels."""
        return max(self.node_radius * 15, 0.6)

    def name_fits(self, name: str) -> bool:
        """Tell whether a zone name fits between two neighbor zones."""
        if self.gap is None:
            return True
        return len(name) * CHAR_WIDTH * self.label_size * 1.25 <= self.gap

    @property
    def drone_height(self) -> float:
        """Height of a drone sprite."""
        return _clamp(self.node_radius * 1.7, 0.03, 0.085)

    def link_width(self, capacity: int) -> float:
        """Road width, thicker for links of higher capacity."""
        base = self.node_radius * 0.5
        return base * min(1.0 + 0.35 * (capacity - 1), 2.2)


def cluster_offsets(count: int, spread: float
                    ) -> list[tuple[float, float]]:
    """Spread `count` drones around a point, without overlap."""
    if count <= 1:
        return [(0.0, 0.0)] * max(count, 0)
    return [(spread * math.cos(math.pi / 2 + 2 * math.pi * i / count),
             spread * math.sin(math.pi / 2 + 2 * math.pi * i / count))
            for i in range(count)]


def cover_scale(window_aspect: float, image_aspect: float
                ) -> tuple[float, float]:
    """Size of a background that covers camera.ui (height 1) fully."""
    if window_aspect >= image_aspect:
        return window_aspect, window_aspect / image_aspect
    return image_aspect, 1.0


CHAR_WIDTH = 0.0145


def fit_size(text: str, base: float, max_width: float) -> float:
    """Text scale that keeps `text` within `max_width` (camera.ui units)."""
    if not text:
        return base
    return min(base, max_width / (len(text) * CHAR_WIDTH))
