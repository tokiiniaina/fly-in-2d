"""Turn a TerrainPlan into low-poly meshes (pure, no Ursina)."""

import math
from dataclasses import dataclass

from flyin.src.viewer3d import environment, palette
from flyin.src.viewer3d.meshbuilder import MeshBuilder, as_rgb
from flyin.src.viewer3d.terrain import (
    CELL,
    PadPlan,
    PathPlan,
    PropPlan,
    TerrainPlan,
)
from flyin.src.viewer.geometry import rounded_rect_outline
from flyin.src.map_data import MapData

CHAMFER = 0.10
PAD_HEIGHT = 0.22
Cell = tuple[int, int]


def map_colors(data: MapData) -> list[str]:
    """The colors written in the map (rainbow is not averaged)."""
    found: list[str] = []
    for zone in data.zones.values():
        stops = palette.color_stops(zone.color)
        if stops is not None and zone.color.strip().lower() != "rainbow":
            found.append(stops[0])
    return found


def _wiggle(seed: int, amount: float) -> float:
    """Small deterministic variation in [-amount, amount]."""
    return ((seed * 7919 + 104729) % 1000 / 1000.0 - 0.5) * 2 * amount


def build_ground(plan: TerrainPlan, colors: list[str]) -> MeshBuilder:
    """Space-ground tiles with glowing rims and rock cliffs, plus islets."""
    builder = MeshBuilder()
    grass_a = palette.harmonize(palette.GROUND_A, colors)
    grass_b = palette.harmonize(palette.GROUND_B, colors)
    for (i, j), height in sorted(plan.cells.items()):
        island = plan.island[(i, j)]
        _tile(builder, plan, i, j, height, island, grass_a, grass_b)
    for island in sorted(plan.base_level):
        if island == 0:
            continue
        cells = [c for c, k in plan.island.items() if k == island]
        i0, i1 = min(c[0] for c in cells), max(c[0] for c in cells)
        j0, j1 = min(c[1] for c in cells), max(c[1] for c in cells)
        top = plan.base_level[island] - plan.depth[island]
        builder.pyramid_down(
            (i0 + i1) / 2 * CELL, (j0 + j1) / 2 * CELL,
            ((i1 - i0) / 2 + 0.5) * CELL, ((j1 - j0) / 2 + 0.5) * CELL,
            top, top - 1.3, palette.STONE_DARK)
    return builder


def _tile(builder: MeshBuilder, plan: TerrainPlan, i: int, j: int,
          h: float, island: int, grass_a: str, grass_b: str) -> None:
    """One ground cell: top, chamfered rims and cliff walls."""
    x, z = i * CELL, j * CELL
    half = CELL / 2
    x0, x1, z0, z1 = x - half, x + half, z - half, z + half
    sides = {"l": (i - 1, j), "r": (i + 1, j), "b": (i, j - 1),
             "t": (i, j + 1)}
    drop: dict[str, float | None] = {}
    for key, cell in sides.items():
        other = plan.cells.get(cell)
        if other is None:
            drop[key] = plan.base_level[island] - plan.depth[island]
        elif other < h - 1e-6:
            drop[key] = other
        else:
            drop[key] = None
    c = CHAMFER
    il = c if drop["l"] is not None else 0.0
    ir = c if drop["r"] is not None else 0.0
    ib = c if drop["b"] is not None else 0.0
    it = c if drop["t"] is not None else 0.0
    tx0, tx1, tz0, tz1 = x0 + il, x1 - ir, z0 + ib, z1 - it
    base = grass_a if (i + j) % 2 == 0 else grass_b
    top = palette.brighten(base, 0.05 + _wiggle(i * 31 + j, 0.03)
                           ) if (i * 7 + j * 13) % 5 == 0 else base
    builder.face([(tx0, h, tz0), (tx1, h, tz0), (tx1, h, tz1),
                  (tx0, h, tz1)], top, (0.0, 1.0, 0.0))
    _speck(builder, i, j, h)
    lip = palette.RIM_GLOW
    stone_top = as_rgb(palette.brighten(palette.STONE, 0.05))
    stone_bottom = as_rgb(palette.darken(palette.STONE, 0.2))
    walls = {
        "l": ([(x0, h - c, z0), (x0, h - c, z1), (tx0, h, tz1),
               (tx0, h, tz0)], (-0.7, 0.7, 0.0),
              [(x0, h - c, z0), (x0, h - c, z1)], (-1.0, 0.0, 0.0)),
        "r": ([(x1, h - c, z0), (x1, h - c, z1), (tx1, h, tz1),
               (tx1, h, tz0)], (0.7, 0.7, 0.0),
              [(x1, h - c, z0), (x1, h - c, z1)], (1.0, 0.0, 0.0)),
        "b": ([(x0, h - c, z0), (x1, h - c, z0), (tx1, h, tz0),
               (tx0, h, tz0)], (0.0, 0.7, -0.7),
              [(x0, h - c, z0), (x1, h - c, z0)], (0.0, 0.0, -1.0)),
        "t": ([(x0, h - c, z1), (x1, h - c, z1), (tx1, h, tz1),
               (tx0, h, tz1)], (0.0, 0.7, 0.7),
              [(x0, h - c, z1), (x1, h - c, z1)], (0.0, 0.0, 1.0)),
    }
    for key, (slope, slope_n, edge, wall_n) in walls.items():
        bottom = drop[key]
        if bottom is None:
            continue
        builder.face(slope, lip, slope_n, lit=False)
        (ax, ay, az), (bx, _, bz) = edge
        builder.face([(ax, ay, az), (bx, ay, bz), (bx, bottom, bz),
                      (ax, bottom, az)], stone_top, wall_n,
                     gradient=(stone_top, stone_bottom))


def _speck(builder: MeshBuilder, i: int, j: int, h: float) -> None:
    """A tiny glowing star dust speck on some ground tiles."""
    key = (i * 73856093) ^ (j * 19349663)
    if key % 5 != 0:
        return
    x = i * CELL + _wiggle(key, 0.3)
    z = j * CELL + _wiggle(key >> 3, 0.3)
    size = 0.035 + (key % 7) * 0.007
    color = palette.SPECKS[key % len(palette.SPECKS)]
    builder.face([(x - size, h + 0.004, z), (x, h + 0.004, z + size),
                  (x + size, h + 0.004, z), (x, h + 0.004, z - size)],
                 color, (0.0, 1.0, 0.0), lit=False)


def build_paths(plan: TerrainPlan) -> MeshBuilder:
    """Metal plate strips, one per real connection of the graph."""
    builder = MeshBuilder()
    for index, path in enumerate(plan.paths):
        _cobbles(builder, plan, path, index)
    return builder


def _cobbles(builder: MeshBuilder, plan: TerrainPlan, path: PathPlan,
             index: int) -> None:
    """Lay the stones of one path between its two pads."""
    dx, dz = path.x1 - path.x0, path.z1 - path.z0
    length = math.hypot(dx, dz)
    if length < 1e-9:
        return
    ux, uz = dx / length, dz / length
    pad = plan.pad(path.first)
    start = pad.half * 0.6
    usable = max(length - 2 * start, 0.2)
    count = max(1, round(usable / 0.6))
    step = usable / count
    base = palette.PLATE_CLOSED if path.closed else palette.PLATE
    for k in range(count):
        t = start + step * (k + 0.5)
        shade_k = _wiggle(index * 97 + k, 0.05)
        top = palette.brighten(base, shade_k) if shade_k > 0 else (
            palette.darken(base, -shade_k))
        side = palette.darken(base, 0.18)
        offset = _wiggle(index * 13 + k * 5, 0.03)
        builder.box(
            path.x0 + ux * t - uz * offset, 0.0,
            path.z0 + uz * t + ux * offset, (ux, uz), step - 0.07, 0.08,
            path.width * (0.92 + _wiggle(k + index, 0.04)), top, side,
            bevel=0.025)


def build_pad(pad: PadPlan) -> MeshBuilder:
    """A zone pad, shaped by its type and colored by the map."""
    builder = MeshBuilder()
    stops = palette.color_stops(pad.color_word)
    rainbow = stops is not None and len(stops) > 1
    color = (stops[0] if stops else palette.DEFAULT_PAD[pad.kind])
    if pad.kind == "blocked":
        _blocked(builder, pad, stops[0] if stops else "#e85d5d")
        return builder
    height = {"priority": 0.34, "restricted": 0.12}.get(pad.kind,
                                                        PAD_HEIGHT)
    half, x, z = pad.half, pad.x, pad.z
    radius = half * 0.55
    builder.rounded_prism(x, z, half + 0.09, half + 0.09, radius + 0.05,
                          0.0, 0.03, palette.SHADOW_PLATE,
                          palette.SHADOW_PLATE)
    if pad.kind == "priority":
        builder.rounded_prism(x, z, half * 1.18, half * 1.18, radius,
                              0.03, 0.09, "#ffe08a", "#e9b949",
                              bevel=0.03)
    builder.rounded_prism(
        x, z, half, half, radius, 0.0, height,
        palette.brighten(color, 0.1), palette.darken(color, 0.22),
        bevel=0.07)
    builder.rounded_prism(
        x, z, half * 0.66, half * 0.66, radius * 0.6, height,
        height + 0.02, palette.brighten(color, 0.3),
        palette.brighten(color, 0.3))
    if rainbow and stops is not None:
        _rainbow_top(builder, pad, stops, height + 0.03)
    _decorate(builder, pad, height)
    return builder


def _rainbow_top(builder: MeshBuilder, pad: PadPlan, stops: list[str],
                 y: float) -> None:
    """Cover the pad top with colored wedges (the rainbow color)."""
    ring = rounded_rect_outline(pad.half * 1.7, pad.half * 1.7,
                                pad.half * 0.45, 2)
    count = len(ring)
    for k, color in enumerate(stops):
        lo = count * k // len(stops)
        hi = count * (k + 1) // len(stops)
        arc = [(pad.x + px, y, pad.z + pz)
               for px, pz in ring[lo:hi + 1]
               ] if hi < count else [
            (pad.x + px, y, pad.z + pz) for px, pz in ring[lo:] + ring[:1]]
        builder.face([(pad.x, y, pad.z)] + arc, color, (0.0, 1.0, 0.0))


def _decorate(builder: MeshBuilder, pad: PadPlan, height: float) -> None:
    """Marks that tell the type of a zone apart."""
    half, x, z = pad.half, pad.x, pad.z
    if pad.kind == "priority":
        builder.star(x, height + 0.02, z, half * 0.5, half * 0.22, 0.1,
                     "#fff2b0", "#e9b949")
    elif pad.kind == "restricted":
        for side in range(4):
            ux, uz = [(1, 0), (0, 1), (-1, 0), (0, -1)][side]
            px, pz = -uz, ux
            for k in range(4):
                along = (k - 1.5) * half * 0.5
                shade = "#2b2f3b" if (k + side) % 2 == 0 else "#ffd23f"
                builder.box(x + ux * half * 1.12 + px * along, 0.0,
                            z + uz * half * 1.12 + pz * along,
                            (px, pz) if px or pz else (1, 0),
                            half * 0.42, 0.07, 0.1, shade, shade)
    elif pad.kind == "start":
        _flag(builder, x + half * 0.5, z + half * 0.5, height, "#35d0e6",
              False)
    elif pad.kind == "end":
        _flag(builder, x + half * 0.5, z + half * 0.5, height, "#ffffff",
              True)


def _flag(builder: MeshBuilder, x: float, z: float, height: float,
          color: str, checkered: bool) -> None:
    """A flag on a pole (checkered for the goal)."""
    top = height + 1.25
    builder.cylinder(x, z, 0.035, height, top, "#ffffff", "#e6e1d8", 6)
    if not checkered:
        builder.box(x + 0.27, top - 0.34, z, (1, 0), 0.5, 0.3, 0.03,
                    color, palette.darken(color, 0.2))
        return
    cell = 0.13
    for row in range(2):
        for col in range(4):
            shade = "#2b2f3b" if (row + col) % 2 == 0 else "#ffffff"
            builder.box(x + 0.07 + cell * (col + 0.5),
                        top - cell * (row + 1), z, (1, 0), cell, cell,
                        0.03, shade, shade)


def _blocked(builder: MeshBuilder, pad: PadPlan, color: str) -> None:
    """A closed zone: dark stone block with a crossed barrier."""
    half, x, z = pad.half, pad.x, pad.z
    builder.rounded_prism(x, z, half + 0.09, half + 0.09, half * 0.6,
                          0.0, 0.03, palette.SHADOW_PLATE,
                          palette.SHADOW_PLATE)
    builder.rounded_prism(x, z, half, half, half * 0.5, 0.0, 0.32,
                          "#8a8794", "#676373", bevel=0.07)
    for direction in ((1, 1), (1, -1)):
        builder.box(x, 0.32, z, direction, half * 1.7, 0.1, half * 0.28,
                    color, palette.darken(color, 0.25), bevel=0.02)
    builder.blob(x - half * 0.55, 0.32, z - half * 0.55, 0.14,
                 palette.ROCK, (1.0, 0.7, 1.0), 2, 5)


def build_props(plan: TerrainPlan) -> MeshBuilder:
    """Asteroid rocks and glowing crystals."""
    builder = MeshBuilder()
    for prop in plan.props:
        _prop(builder, prop)
    return builder


def _prop(builder: MeshBuilder, prop: PropPlan) -> None:
    """Build one low-poly prop."""
    s, x, y, z = prop.scale, prop.x, prop.y, prop.z
    if prop.kind == "crystal":
        color = palette.CRYSTALS[prop.variant % len(palette.CRYSTALS)]
        for dx, dz, height, radius in ((0.0, 0.0, 0.8, 0.13),
                                       (0.14, 0.05, 0.5, 0.09),
                                       (-0.1, 0.1, 0.38, 0.08)):
            builder.cone(x + dx * s, z + dz * s, radius * s, y,
                         y + height * s, color, 5)
    else:
        builder.blob(x, y + 0.1 * s, z, 0.3 * s, palette.ROCK,
                     (1.0, 0.7, 0.85), 2, 5, prop.variant)


@dataclass(frozen=True)
class SceneMesh:
    """A builder and how opaque it is (smoke is translucent)."""

    builder: MeshBuilder
    alpha: float = 1.0


def build_all(plan: TerrainPlan, data: MapData, seed: str
              ) -> list[SceneMesh]:
    """Every mesh of the scene: world, pads, stars and smoke."""
    result = [SceneMesh(build_ground(plan, map_colors(data))),
              SceneMesh(build_paths(plan)), SceneMesh(build_props(plan))]
    result.extend(SceneMesh(build_pad(pad)) for pad in plan.pads)
    result.append(SceneMesh(environment.build_stars(plan, seed)))
    result.append(SceneMesh(environment.build_smoke(plan, seed),
                            environment.SMOKE_ALPHA))
    return result
