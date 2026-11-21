"""Pure space decor: 3D stars and smoke clouds around the islands.

Both are static (not animated). They are placed outside the play area,
so they never touch the terrain, and they are seeded by the map name.
"""

import math
import random
import zlib
from dataclasses import dataclass

from flyin.src.viewer3d.meshbuilder import MeshBuilder
from flyin.src.viewer3d.terrain import CELL, TerrainPlan

STAR_COLORS = ("#ffffff", "#cfe8ff", "#fff1c9", "#bfa8ff", "#9fe9ff")
SMOKE_COLORS = ("#6a58b8", "#7966c4", "#8a73cc", "#5a7dc0", "#9a78c0",
                "#6f86cc")
SMOKE_ALPHA = 0.45
STAR_COUNT = 320
STAR_CLEAR_Y = 38.0
SMOKE_TOP = -5.4
SMOKE_BOTTOM = -9.5
ISLET_SAFE_Y = -6.5


@dataclass(frozen=True)
class Star:
    """A small glowing star in space."""

    x: float
    y: float
    z: float
    size: float
    color: str


@dataclass(frozen=True)
class Puff:
    """One blob of a smoke cloud."""

    x: float
    y: float
    z: float
    radius: float
    flat: float
    color: str


def extent(plan: TerrainPlan) -> tuple[float, float, float, float]:
    """Center and half size (cx, cz, rx, rz) of all the ground cells."""
    i_values = [i for i, _ in plan.cells]
    j_values = [j for _, j in plan.cells]
    cx = (min(i_values) + max(i_values)) / 2 * CELL
    cz = (min(j_values) + max(j_values)) / 2 * CELL
    rx = (max(i_values) - min(i_values)) / 2 * CELL + 1
    rz = (max(j_values) - min(j_values)) / 2 * CELL + 1
    return cx, cz, rx, rz


def _rng(plan: TerrainPlan, seed: str, salt: str) -> random.Random:
    """Deterministic generator for a map and a kind of decor."""
    del plan
    return random.Random(zlib.crc32(f"{seed}:{salt}".encode()))


def star_points(plan: TerrainPlan, seed: str,
                count: int = STAR_COUNT) -> list[Star]:
    """Stars spread around the islands, never inside the play volume."""
    rng = _rng(plan, seed, "stars")
    cx, cz, rx, rz = extent(plan)
    boost = 1.0 + 0.02 * (rx + rz)
    stars: list[Star] = []
    while len(stars) < count:
        x = cx + rng.uniform(-1, 1) * (rx + 50)
        z = cz + rng.uniform(-1, 1) * (rz + 50)
        y = rng.uniform(-45.0, 38.0)
        inside = (((x - cx) / (rx + 8)) ** 2 + ((z - cz) / (rz + 8)) ** 2
                  + (y / STAR_CLEAR_Y) ** 2)
        if inside < 1.0:
            continue
        stars.append(Star(x, y, z,
                          (0.04 + 0.12 * rng.random() ** 3) * boost,
                          rng.choice(STAR_COLORS)))
    return stars


def build_stars(plan: TerrainPlan, seed: str) -> MeshBuilder:
    """Make the star field mesh (glowing, not shaded)."""
    builder = MeshBuilder()
    for star in star_points(plan, seed):
        builder.diamond(star.x, star.y, star.z, star.size, star.color)
    return builder


def smoke_puffs(plan: TerrainPlan, seed: str) -> list[Puff]:
    """A layer of smoke under the islands, with a few wisps at the sides."""
    rng = _rng(plan, seed, "smoke")
    cx, cz, rx, rz = extent(plan)
    cells = list(plan.cells)
    puffs: list[Puff] = []
    clusters = 8 + int((rx + rz) / 4)
    for index in range(clusters):
        if index % 4 != 3:
            x = cx + rng.uniform(-1.05, 1.05) * rx
            z = cz + rng.uniform(-1.05, 1.05) * rz
            y = rng.uniform(SMOKE_BOTTOM, SMOKE_BOTTOM + 3.0)
        else:
            angle = rng.uniform(0, 2 * math.pi)
            x = cx + math.cos(angle) * (rx + 3 + rng.uniform(0, 8))
            z = cz + math.sin(angle) * (rz + 3 + rng.uniform(0, 8))
            y = rng.uniform(SMOKE_BOTTOM + 1, SMOKE_TOP)
        if y > ISLET_SAFE_Y and _near_islet(plan, cells, x, z):
            continue
        for _ in range(rng.randint(5, 8)):
            puffs.append(Puff(
                x + rng.uniform(-2.2, 2.2), y + rng.uniform(-0.5, 0.5),
                z + rng.uniform(-2.4, 2.4), rng.uniform(1.2, 2.6),
                rng.uniform(0.65, 0.9), rng.choice(SMOKE_COLORS)))
    return puffs


def _near_islet(plan: TerrainPlan, cells: list[tuple[int, int]],
                x: float, z: float) -> bool:
    """Tell whether a cloud would touch an islet or its underside."""
    for cell in cells:
        if plan.island[cell] == 0:
            continue
        if math.hypot(x - cell[0] * CELL, z - cell[1] * CELL) < 6.5:
            return True
    return False


def build_smoke(plan: TerrainPlan, seed: str) -> MeshBuilder:
    """Make the smoke mesh: overlapping low-poly blobs."""
    builder = MeshBuilder()
    for puff in smoke_puffs(plan, seed):
        builder.blob(puff.x, puff.y, puff.z, puff.radius, puff.color,
                     (1.0, puff.flat, 1.0), 4, 9)
    return builder
