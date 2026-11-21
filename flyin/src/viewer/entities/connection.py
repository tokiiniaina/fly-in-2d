"""Roads between zones: smooth, round-ended, in one entity tree."""

import math
from typing import Any

from ursina import Entity, Mesh

from flyin.src.connection import Connection
from flyin.src.viewer import theme
from flyin.src.viewer.geometry import (
    Triangle,
    Vertex,
    circle_outline,
    fan,
)
from flyin.src.viewer.layout import NetworkLayout
from flyin.src.viewer.shapes import label, smooth_disc, tint

Point = tuple[float, float]
Segment = tuple[Point, Point, float]


class RoadMesh:
    """Many thick segments with round ends, merged in a single entity."""

    def __init__(self, parent: Any, segments: list[Segment], fill: str,
                 z: float) -> None:
        """Build one entity from (start, end, width) segments."""
        self.entity: Any = None
        vertices: list[Vertex] = []
        triangles: list[Triangle] = []
        for start, end, width in segments:
            self._add_quad(vertices, triangles, start, end, width)
            for point in (start, end):
                cap_v, cap_t = fan(circle_outline(width / 2, 10), point,
                                   len(vertices))
                vertices.extend(cap_v)
                triangles.extend(cap_t)
        if vertices:
            self.entity = Entity(
                parent=parent, model=Mesh(vertices=vertices,
                                          triangles=triangles),
                color=tint(fill), double_sided=True, z=z)

    @staticmethod
    def _add_quad(vertices: list[Vertex], triangles: list[Triangle],
                  start: Point, end: Point, width: float) -> None:
        """Append the two triangles of a thick segment."""
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = math.hypot(dx, dy)
        if length < 1e-9:
            return
        nx, ny = -dy / length * width / 2, dx / length * width / 2
        base = len(vertices)
        vertices.extend([
            (start[0] + nx, start[1] + ny, 0.0),
            (start[0] - nx, start[1] - ny, 0.0),
            (end[0] - nx, end[1] - ny, 0.0),
            (end[0] + nx, end[1] + ny, 0.0),
        ])
        triangles.extend([(base, base + 1, base + 2),
                          (base, base + 2, base + 3)])


class ConnectionLayer:
    """Draw every connection of the map on a layout.

    All coordinates are relative to the center of the drawing area, so
    scaling `root` makes the whole road network grow from the middle.
    """

    def __init__(self, parent: Any, layout: NetworkLayout,
                 connections: list[Connection],
                 blocked: set[str]) -> None:
        """Draw the roads; roads touching a blocked zone are dimmed."""
        area = layout.area
        self.root = Entity(parent=parent,
                           position=(area.cx, area.cy, theme.Z_ROAD))
        usable: list[Segment] = []
        dead: list[Segment] = []
        outline: list[Segment] = []
        pad = layout.node_radius * 0.28
        for conn in connections:
            start = self._local(layout, conn.zone1)
            end = self._local(layout, conn.zone2)
            width = layout.link_width(conn.max_link_capacity)
            outline.append((start, end, width + pad))
            closed = conn.zone1 in blocked or conn.zone2 in blocked
            (dead if closed else usable).append((start, end, width))
        self.meshes = [
            RoadMesh(self.root, outline, theme.ROAD_OUTLINE, 0.0),
            RoadMesh(self.root, dead, theme.ROAD_DEAD, -0.01),
            RoadMesh(self.root, usable, theme.ROAD, -0.02),
        ]
        self.badges: list[Any] = []
        for conn in connections:
            if conn.max_link_capacity > 1:
                self._badge(layout, conn)

    @staticmethod
    def _local(layout: NetworkLayout, name: str) -> Point:
        """Zone position relative to the center of the area."""
        x, y = layout.positions[name]
        return x - layout.area.cx, y - layout.area.cy

    def _badge(self, layout: NetworkLayout, conn: Connection) -> None:
        """Show the capacity number at the middle of a wide connection."""
        ax, ay = self._local(layout, conn.zone1)
        bx, by = self._local(layout, conn.zone2)
        if math.hypot(ax - bx, ay - by) < layout.node_radius * 3.2:
            return
        mx, my = (ax + bx) / 2, (ay + by) / 2
        size = layout.node_radius * 1.0
        self.badges.append(smooth_disc(self.root, mx, my, size,
                                       theme.INK_SOFT, -0.05))
        self.badges.append(
            label(self.root, str(conn.max_link_capacity), mx, my,
                  max(size * 22, 0.55), theme.TEXT, theme.Z_LABEL))

    def set_scale(self, factor: float) -> None:
        """Scale the whole road network around the area center."""
        value = max(factor, 1e-3)
        self.root.scale = (value, value)
