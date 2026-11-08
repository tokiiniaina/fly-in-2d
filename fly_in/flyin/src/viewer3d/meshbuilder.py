"""Pure mesh construction: flat-shaded, vertex-colored low-poly shapes.

Shading is computed here (a fixed light from the upper left), so the
scene looks the same with any Ursina shader. Meshes are double sided, so
the winding of a face does not matter, only its stated normal.
"""

import math

from flyin.src.viewer.geometry import circle_outline, rounded_rect_outline
from flyin.src.viewer3d.palette import hex_to_rgb

Vec = tuple[float, float, float]
RGB = tuple[float, float, float]
Triangle = tuple[int, int, int]
MeshData = tuple[list[Vec], list[Triangle], list[RGB]]

MAX_VERTICES = 60000
AMBIENT = 0.58


def unit(vector: Vec) -> Vec:
    """Normalize a vector (zero stays zero)."""
    length = math.sqrt(sum(c * c for c in vector))
    if length < 1e-12:
        return (0.0, 0.0, 0.0)
    return (vector[0] / length, vector[1] / length, vector[2] / length)


LIGHT: Vec = unit((-0.5, 0.8, 0.14))


def shade(color: RGB, normal: Vec) -> RGB:
    """Apply the fixed light to a color for a surface normal."""
    n = unit(normal)
    lit = max(0.0, n[0] * LIGHT[0] + n[1] * LIGHT[1] + n[2] * LIGHT[2])
    k = AMBIENT + (1.0 - AMBIENT) * lit
    return (min(1.0, color[0] * k), min(1.0, color[1] * k),
            min(1.0, color[2] * k))


def as_rgb(color: str | RGB) -> RGB:
    """Accept '#rrggbb' or an RGB tuple."""
    return hex_to_rgb(color) if isinstance(color, str) else color


class _Part:
    """One mesh worth of vertices."""

    def __init__(self) -> None:
        """Start empty."""
        self.vertices: list[Vec] = []
        self.triangles: list[Triangle] = []
        self.colors: list[RGB] = []


class MeshBuilder:
    """Collect faces and shapes, split into meshes of bounded size."""

    def __init__(self) -> None:
        """Start with one empty mesh."""
        self._parts = [_Part()]
        self._soft = False

    def face(self, points: list[Vec], color: str | RGB, normal: Vec,
             gradient: tuple[RGB, RGB] | None = None,
             lit: bool = True) -> None:
        """Add a flat convex polygon with a stated normal.

        With `gradient` (top color, bottom color), the vertices are
        colored by height between the lowest and highest point. With
        `lit` false the color is kept as is (glowing surface).
        """
        part = self._parts[-1]
        if len(part.vertices) + len(points) > MAX_VERTICES:
            part = _Part()
            self._parts.append(part)
        base = len(part.vertices)
        flat = shade(as_rgb(color), normal) if lit else as_rgb(color)
        low = min(p[1] for p in points)
        high = max(p[1] for p in points)
        for point in points:
            part.vertices.append(point)
            if gradient is None or high - low < 1e-9:
                part.colors.append(flat)
            else:
                t = (point[1] - low) / (high - low)
                top, bottom = shade(gradient[0], normal), shade(
                    gradient[1], normal)
                part.colors.append((
                    bottom[0] + (top[0] - bottom[0]) * t,
                    bottom[1] + (top[1] - bottom[1]) * t,
                    bottom[2] + (top[2] - bottom[2]) * t))
        for i in range(1, len(points) - 1):
            part.triangles.append((base, base + i, base + i + 1))

    def meshes(self) -> list[MeshData]:
        """Return the non-empty meshes as (vertices, triangles, colors)."""
        return [(p.vertices, p.triangles, p.colors)
                for p in self._parts if p.vertices]

    @property
    def vertex_count(self) -> int:
        """Total number of vertices."""
        return sum(len(p.vertices) for p in self._parts)

    def box(self, x: float, y0: float, z: float, direction: tuple[float,
            float], length: float, height: float, width: float,
            top: str | RGB, side: str | RGB, bevel: float = 0.0) -> None:
        """Add a box standing on y0, long axis along `direction` (x, z)."""
        ux, uz = direction
        norm = math.hypot(ux, uz) or 1.0
        ux, uz = ux / norm, uz / norm
        wx, wz = -uz, ux
        hl, hw = length / 2, width / 2
        corners = [(x + ux * a + wx * b, z + uz * a + wz * b)
                   for a, b in ((-hl, -hw), (hl, -hw), (hl, hw),
                                (-hl, hw))]
        inner = [(x + ux * a + wx * b, z + uz * a + wz * b)
                 for a, b in ((-hl + bevel, -hw + bevel),
                              (hl - bevel, -hw + bevel),
                              (hl - bevel, hw - bevel),
                              (-hl + bevel, hw - bevel))]
        self._prism(corners, inner, y0, y0 + height, bevel, top, side)

    def rounded_prism(self, x: float, z: float, half_x: float,
                      half_z: float, radius: float, y0: float,
                      y1: float, top: str | RGB, side: str | RGB,
                      bevel: float = 0.0, segments: int = 3) -> None:
        """Add an extruded rounded rectangle with an optional bevel."""
        outer = rounded_rect_outline(2 * half_x, 2 * half_z, radius,
                                     segments)
        small = rounded_rect_outline(
            2 * (half_x - bevel), 2 * (half_z - bevel),
            max(radius - bevel, 1e-3), segments)
        self._prism([(x + px, z + pz) for px, pz in outer],
                    [(x + px, z + pz) for px, pz in small],
                    y0, y1, bevel, top, side)

    def cylinder(self, x: float, z: float, radius: float, y0: float,
                 y1: float, top: str | RGB, side: str | RGB,
                 sides: int = 8) -> None:
        """Add an upright cylinder."""
        ring = [(x + px, z + pz) for px, pz in circle_outline(radius, sides)]
        self._prism(ring, ring, y0, y1, 0.0, top, side)

    def _prism(self, outer: list[tuple[float, float]],
               inner: list[tuple[float, float]], y0: float, y1: float,
               bevel: float, top: str | RGB, side: str | RGB) -> None:
        """Walls, optional sloped rim and top of an extruded outline."""
        count = len(outer)
        wall_top = y1 - bevel
        for i in range(count):
            (ax, az), (bx, bz) = outer[i], outer[(i + 1) % count]
            dx, dz = bx - ax, bz - az
            normal = unit((dz, 0.0, -dx))
            nx, nz = normal[0], normal[2]
            self.face([(ax, y0, az), (bx, y0, bz), (bx, wall_top, bz),
                       (ax, wall_top, az)], side, (nx, 0.0, nz))
            if bevel > 0:
                (iax, iaz), (ibx, ibz) = inner[i], inner[(i + 1) % count]
                self.face([(ax, wall_top, az), (bx, wall_top, bz),
                           (ibx, y1, ibz), (iax, y1, iaz)], top,
                          (nx * 0.7, 0.7, nz * 0.7))
        self.face([(px, y1, pz) for px, pz in inner], top, (0.0, 1.0, 0.0))

    def cone(self, x: float, z: float, radius: float, y0: float,
             y1: float, color: str | RGB, sides: int = 6) -> None:
        """Add an upright cone (pine layers)."""
        ring = circle_outline(radius, sides)
        slope = radius / max(y1 - y0, 1e-6)
        for i in range(sides):
            (ax, az), (bx, bz) = ring[i], ring[(i + 1) % sides]
            mx, mz = (ax + bx) / 2, (az + bz) / 2
            n = unit((mx, slope * radius, mz))
            self.face([(x + ax, y0, z + az), (x + bx, y0, z + bz),
                       (x, y1, z)], color, n)

    def blob(self, x: float, y: float, z: float, radius: float,
             color: str | RGB, squash: Vec = (1.0, 1.0, 1.0),
             rings: int = 3, sectors: int = 7, turn: float = 0.0,
             soft: bool = False) -> None:
        """Add a low-poly rounded blob (boulder, smoke).

        A `soft` blob is not shaded per face: it only gets lighter toward
        its top, so it looks like a puff of smoke instead of a rock.
        """
        self._soft = soft
        grid: list[list[Vec]] = []
        for r in range(rings + 1):
            theta = math.pi * r / rings
            ring_points: list[Vec] = []
            for s in range(sectors if 0 < r < rings else 1):
                phi = turn + 2 * math.pi * (s + 0.5 * (r % 2)) / sectors
                ring_points.append((
                    x + radius * squash[0] * math.sin(theta) * math.cos(phi),
                    y + radius * squash[1] * math.cos(theta),
                    z + radius * squash[2] * math.sin(theta) * math.sin(phi),
                ))
            grid.append(ring_points)
        for r in range(rings):
            self._band(grid[r], grid[r + 1], (x, y, z), color, squash)

    def _band(self, upper: list[Vec], lower: list[Vec], center: Vec,
              color: str | RGB, squash: Vec) -> None:
        """Faces between two rings of a blob (either may be a pole)."""
        if len(upper) == 1:
            ring, pole = lower, upper[0]
            for i in range(len(ring)):
                self._blob_face([pole, ring[i], ring[(i + 1) % len(ring)]],
                                center, color, squash)
        elif len(lower) == 1:
            ring, pole = upper, lower[0]
            for i in range(len(ring)):
                self._blob_face([ring[i], ring[(i + 1) % len(ring)], pole],
                                center, color, squash)
        else:
            count = len(upper)
            for i in range(count):
                j = (i + 1) % count
                self._blob_face([upper[i], upper[j], lower[j], lower[i]],
                                center, color, squash)

    def _blob_face(self, points: list[Vec], center: Vec,
                   color: str | RGB, squash: Vec) -> None:
        """Add one blob face, lit by its outward direction."""
        mx = sum(p[0] for p in points) / len(points) - center[0]
        my = sum(p[1] for p in points) / len(points) - center[1]
        mz = sum(p[2] for p in points) / len(points) - center[2]
        normal = (mx / squash[0] ** 2, my / squash[1] ** 2,
                  mz / squash[2] ** 2)
        if not self._soft:
            self.face(points, color, normal)
            return
        up = (unit(normal)[1] + 1.0) / 2.0
        base = as_rgb(color)
        factor = 0.78 + 0.34 * up
        self.face(points, (min(1.0, base[0] * factor),
                           min(1.0, base[1] * factor),
                           min(1.0, base[2] * factor)), normal, lit=False)

    def star(self, x: float, y0: float, z: float, outer: float,
             inner: float, height: float, top: str | RGB,
             side: str | RGB, points: int = 5) -> None:
        """Add an extruded star (priority mark)."""
        ring: list[tuple[float, float]] = []
        for i in range(points * 2):
            radius = outer if i % 2 == 0 else inner
            angle = math.pi / 2 + math.pi * i / points
            ring.append((x + radius * math.cos(angle),
                         z + radius * math.sin(angle)))
        self._prism(ring, ring, y0, y0 + height, 0.0, top, side)

    def diamond(self, x: float, y: float, z: float, size: float,
                color: str | RGB) -> None:
        """Add a small glowing octahedron (a star)."""
        top, bottom = (x, y + size, z), (x, y - size, z)
        ring = [(x + size * 0.6, y, z), (x, y, z + size * 0.6),
                (x - size * 0.6, y, z), (x, y, z - size * 0.6)]
        for i in range(4):
            a, b = ring[i], ring[(i + 1) % 4]
            self.face([a, b, top], color, (0.0, 1.0, 0.0), lit=False)
            self.face([b, a, bottom], color, (0.0, -1.0, 0.0), lit=False)

    def pyramid_down(self, x: float, z: float, half_x: float,
                     half_z: float, y_top: float, y_tip: float,
                     color: str | RGB) -> None:
        """Add an inverted pyramid (underside of a floating islet)."""
        tip = (x, y_tip, z)
        base = [(x - half_x, y_top, z - half_z), (x + half_x, y_top,
                z - half_z), (x + half_x, y_top, z + half_z),
                (x - half_x, y_top, z + half_z)]
        for i in range(4):
            a, b = base[i], base[(i + 1) % 4]
            mx, mz = (a[0] + b[0]) / 2 - x, (a[2] + b[2]) / 2 - z
            self.face([a, b, tip], color, unit((mx, -0.6, mz)))
