"""Pure 2D geometry used to build flat meshes (no Ursina)."""

import math

Point = tuple[float, float]
Vertex = tuple[float, float, float]
Triangle = tuple[int, int, int]


def circle_outline(radius: float, segments: int = 16) -> list[Point]:
    """Points of a circle centered on the origin, counter-clockwise."""
    return [(radius * math.cos(2 * math.pi * i / segments),
             radius * math.sin(2 * math.pi * i / segments))
            for i in range(segments)]


def rounded_rect_outline(width: float, height: float, radius: float,
                         segments: int = 6) -> list[Point]:
    """Points of a rounded rectangle centered on the origin."""
    radius = max(min(radius, width / 2, height / 2), 0.0)
    half_w, half_h = width / 2, height / 2
    corners = ((half_w - radius, half_h - radius, 0.0),
               (-half_w + radius, half_h - radius, 90.0),
               (-half_w + radius, -half_h + radius, 180.0),
               (half_w - radius, -half_h + radius, 270.0))
    points: list[Point] = []
    for cx, cy, start in corners:
        for i in range(segments + 1):
            angle = math.radians(start + 90.0 * i / segments)
            points.append((cx + radius * math.cos(angle),
                           cy + radius * math.sin(angle)))
    return points


def fan(points: list[Point], center: Point = (0.0, 0.0),
        offset: int = 0) -> tuple[list[Vertex], list[Triangle]]:
    """Triangulate a convex outline as a fan around `center`.

    `offset` is the index of the first vertex in the final mesh, so
    several fans can be merged into one mesh.
    """
    vertices: list[Vertex] = [(center[0], center[1], 0.0)]
    vertices.extend((x + center[0], y + center[1], 0.0)
                    for x, y in points)
    count = len(points)
    triangles = [(offset, offset + i, offset + i + 1)
                 for i in range(1, count)]
    triangles.append((offset, offset + count, offset + 1))
    return vertices, triangles


def polygon_area(points: list[Point]) -> float:
    """Absolute area of a simple polygon (shoelace formula)."""
    total = 0.0
    for (ax, ay), (bx, by) in zip(points, points[1:] + points[:1]):
        total += ax * by - bx * ay
    return abs(total) / 2


def segment_quad(start: Point, end: Point, width: float,
                 offset: int = 0) -> tuple[list[Vertex], list[Triangle]]:
    """Two triangles covering a thick segment (empty if it is a point)."""
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    if length < 1e-9:
        return [], []
    nx, ny = -dy / length * width / 2, dx / length * width / 2
    vertices: list[Vertex] = [
        (start[0] + nx, start[1] + ny, 0.0),
        (start[0] - nx, start[1] - ny, 0.0),
        (end[0] - nx, end[1] - ny, 0.0),
        (end[0] + nx, end[1] + ny, 0.0),
    ]
    triangles = [(offset, offset + 1, offset + 2),
                 (offset, offset + 2, offset + 3)]
    return vertices, triangles


def chevron(direction: int, size: float, width: float
            ) -> tuple[list[Vertex], list[Triangle]]:
    """A '<' (direction -1) or '>' (direction +1) made of two bars."""
    tip = (direction * size / 2, 0.0)
    back_x = -direction * size / 2
    vertices: list[Vertex] = []
    triangles: list[Triangle] = []
    for back_y in (size, -size):
        new_v, new_t = segment_quad((back_x, back_y), tip, width,
                                    len(vertices))
        vertices.extend(new_v)
        triangles.extend(new_t)
    return vertices, triangles
