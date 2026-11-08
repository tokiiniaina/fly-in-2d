"""Pure terrain planning: where pads, paths, ground and props go.

Everything is derived from the parsed map. Zones keep their exact
coordinates (scaled by SPACING), and a path exists only for a real
connection of the graph. Decor (plateaus, islets, props) is generated
from a seed built from the map name, so a map always looks the same.
"""

import math
import random
import zlib
from dataclasses import dataclass, field

from flyin.src.map_data import MapData

SPACING = 2.0
CELL = 1.0
REACH = 1.15
PLATEAU_REACH = 2.35
PLATEAU_HEIGHT = 0.42
MAIN_DEPTH = 1.6
ISLET_DEPTH = 1.1

Cell = tuple[int, int]


@dataclass(frozen=True)
class PadPlan:
    """A zone: a pad at the exact map position."""

    name: str
    kind: str
    x: float
    z: float
    half: float
    color_word: str
    capacity: int


@dataclass(frozen=True)
class PathPlan:
    """A real connection of the graph, drawn between two pads."""

    first: str
    second: str
    x0: float
    z0: float
    x1: float
    z1: float
    width: float
    capacity: int
    closed: bool


@dataclass(frozen=True)
class PropPlan:
    """A decorative object standing on the ground."""

    kind: str
    x: float
    y: float
    z: float
    scale: float
    variant: int


@dataclass
class TerrainPlan:
    """Everything the builders need to make the scene."""

    pads: list[PadPlan] = field(default_factory=list)
    paths: list[PathPlan] = field(default_factory=list)
    cells: dict[Cell, float] = field(default_factory=dict)
    island: dict[Cell, int] = field(default_factory=dict)
    base_level: dict[int, float] = field(default_factory=dict)
    depth: dict[int, float] = field(default_factory=dict)
    props: list[PropPlan] = field(default_factory=list)

    def pad(self, name: str) -> PadPlan:
        """Return a pad by zone name."""
        return next(p for p in self.pads if p.name == name)

    def bounds(self, main_only: bool = False
               ) -> tuple[float, float, float, float, float, float]:
        """Return (min_x, max_x, min_y, max_y, min_z, max_z).

        With `main_only`, the decor islets are left out (camera framing).
        """
        cells = [c for c in self.cells
                 if not main_only or self.island[c] == 0]
        islands = {0} if main_only else set(self.base_level)
        low = min(self.base_level[k] - self.depth[k] - 1.3
                  for k in islands)
        return (min(i for i, _ in cells) * CELL - 0.5,
                max(i for i, _ in cells) * CELL + 0.5, low, 2.2,
                min(j for _, j in cells) * CELL - 0.5,
                max(j for _, j in cells) * CELL + 0.5)


def segment_distance(px: float, pz: float, path: PathPlan) -> float:
    """Distance from a point to the center line of a path."""
    dx, dz = path.x1 - path.x0, path.z1 - path.z0
    length2 = dx * dx + dz * dz
    t = 0.0 if length2 == 0 else max(0.0, min(
        1.0, ((px - path.x0) * dx + (pz - path.z0) * dz) / length2))
    return math.hypot(px - (path.x0 + t * dx), pz - (path.z0 + t * dz))


def pad_radius(pad: PadPlan) -> float:
    """Radius of the circle that contains a pad."""
    return pad.half * 1.42


def noise(seed: str, i: int, j: int) -> float:
    """Deterministic value in [0, 1) for a block of 2x2 cells."""
    return (zlib.crc32(f"{seed}:{i // 2}:{j // 2}".encode())
            % 10000) / 10000.0


def graph_distance(plan: TerrainPlan, x: float, z: float) -> float:
    """How far a point is from the nearest pad or path surface."""
    best = 1e9
    for pad in plan.pads:
        best = min(best, math.hypot(x - pad.x, z - pad.z) - pad.half)
    for path in plan.paths:
        best = min(best, segment_distance(x, z, path) - path.width / 2)
    return best


class TerrainPlanner:
    """Build a TerrainPlan from a parsed map."""

    def __init__(self, data: MapData, seed: str) -> None:
        """Remember the map and the decor seed."""
        self._data = data
        self._seed = seed
        self._rng = random.Random(zlib.crc32(seed.encode()))

    def plan(self) -> TerrainPlan:
        """Plan pads, paths, ground, islets and props."""
        plan = TerrainPlan()
        self._pads_and_paths(plan)
        self._ground(plan)
        self._islets(plan)
        self._props(plan)
        return plan

    def _pads_and_paths(self, plan: TerrainPlan) -> None:
        """One pad per zone, one path per real connection."""
        data = self._data
        zones = data.zones
        gaps = [math.hypot(zones[c.zone1].x - zones[c.zone2].x,
                           zones[c.zone1].y - zones[c.zone2].y) * SPACING
                for c in data.connections
                if (zones[c.zone1].x, zones[c.zone1].y)
                != (zones[c.zone2].x, zones[c.zone2].y)]
        gap = min(gaps) if gaps else SPACING
        half = max(0.4, min(0.62, 0.28 * gap))
        for name, zone in zones.items():
            kind = zone.zone_type
            if name == data.start_hub:
                kind = "start"
            elif name == data.end_hub:
                kind = "end"
            plan.pads.append(PadPlan(
                name, kind, zone.x * SPACING, zone.y * SPACING, half,
                zone.color, zone.max_drones))
        for conn in data.connections:
            a, b = zones[conn.zone1], zones[conn.zone2]
            width = half * min(1.0 + 0.35 * (conn.max_link_capacity - 1),
                               1.8)
            closed = "blocked" in (a.zone_type, b.zone_type)
            plan.paths.append(PathPlan(
                conn.zone1, conn.zone2, a.x * SPACING, a.y * SPACING,
                b.x * SPACING, b.y * SPACING, width,
                conn.max_link_capacity, closed))

    def _ground(self, plan: TerrainPlan) -> None:
        """Main island: flat cells around the graph, plateaus beyond."""
        xs = [p.x for p in plan.pads]
        zs = [p.z for p in plan.pads]
        i0, i1 = int(min(xs)) - 4, int(max(xs)) + 4
        j0, j1 = int(min(zs)) - 4, int(max(zs)) + 4
        dist: dict[Cell, float] = {}
        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                dist[(i, j)] = graph_distance(plan, i * CELL, j * CELL)
        base = {c for c, d in dist.items() if d <= REACH}
        base |= self._fill_bays(base)
        raised = {c for c, d in dist.items()
                  if REACH < d <= PLATEAU_REACH and c not in base
                  and noise(self._seed, *c) > 0.5}
        raised = self._connected(raised, base)
        plan.base_level[0] = 0.0
        plan.depth[0] = MAIN_DEPTH
        for cell in base:
            plan.cells[cell] = 0.0
            plan.island[cell] = 0
        for cell in raised:
            plan.cells[cell] = PLATEAU_HEIGHT
            plan.island[cell] = 0

    @staticmethod
    def _neighbors(cell: Cell) -> list[Cell]:
        """The four side neighbors of a cell."""
        i, j = cell
        return [(i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)]

    def _fill_bays(self, base: set[Cell]) -> set[Cell]:
        """Cells with at least three footprint neighbors (smooth edges)."""
        extra: set[Cell] = set()
        for cell in {n for c in base for n in self._neighbors(c)} - base:
            if sum(n in base for n in self._neighbors(cell)) >= 3:
                extra.add(cell)
        return extra

    def _connected(self, raised: set[Cell], base: set[Cell]) -> set[Cell]:
        """Keep only raised cells linked to the base ground."""
        keep: set[Cell] = set()
        frontier = [c for c in raised
                    if any(n in base for n in self._neighbors(c))]
        while frontier:
            cell = frontier.pop()
            if cell in keep:
                continue
            keep.add(cell)
            frontier.extend(n for n in self._neighbors(cell)
                            if n in raised and n not in keep)
        return keep

    def _islets(self, plan: TerrainPlan) -> None:
        """Small floating islets around the map (decor only)."""
        rng = self._rng
        min_i = min(i for i, _ in plan.cells)
        max_i = max(i for i, _ in plan.cells)
        min_j = min(j for _, j in plan.cells)
        max_j = max(j for _, j in plan.cells)
        cx, cz = (min_i + max_i) / 2, (min_j + max_j) / 2
        reach = math.hypot(max_i - min_i, max_j - min_j) / 2 + 4
        wanted = 3 + rng.randrange(3)
        index = 0
        for _ in range(60):
            if index >= wanted:
                break
            angle = rng.uniform(0, 2 * math.pi)
            dist = reach + rng.uniform(0, 3)
            width, height = rng.choice((2, 3)), rng.choice((2, 3))
            ci = round(cx + dist * math.cos(angle))
            cj = round(cz + dist * math.sin(angle))
            rect = {(ci + a, cj + b) for a in range(width)
                    for b in range(height)}
            if not self._islet_fits(plan, rect):
                continue
            index += 1
            plan.base_level[index] = round(rng.uniform(-1.6, -0.2), 2)
            plan.depth[index] = ISLET_DEPTH
            for cell in rect:
                plan.cells[cell] = plan.base_level[index]
                plan.island[cell] = index

    @staticmethod
    def _islet_fits(plan: TerrainPlan, rect: set[Cell]) -> bool:
        """An islet keeps a clear gap from every other cell."""
        for (i, j) in rect:
            for a in range(-3, 4):
                for b in range(-3, 4):
                    if (i + a, j + b) in plan.cells:
                        return False
        return True

    def _props(self, plan: TerrainPlan) -> None:
        """Rocks and crystals, never on a pad or a path."""
        rng = self._rng
        for cell in sorted(plan.cells):
            island = plan.island[cell]
            x, z = cell[0] * CELL, cell[1] * CELL
            if island == 0:
                dist = graph_distance(plan, x, z)
                chance = 0.8 if plan.cells[cell] > 0 else (
                    0.4 if dist > 0.7 else 0.0)
            else:
                chance = 0.35
            if rng.random() >= chance:
                continue
            kind = rng.choices(("rock", "crystal"), (62, 38))[0]
            scale = rng.uniform(0.85, 1.2)
            px = x + rng.uniform(-0.12, 0.12)
            pz = z + rng.uniform(-0.12, 0.12)
            if self._prop_fits(plan, kind, px, pz, scale):
                plan.props.append(PropPlan(
                    kind, px, plan.cells[cell], pz, scale,
                    rng.randrange(3)))

    @staticmethod
    def _prop_fits(plan: TerrainPlan, kind: str, x: float, z: float,
                   scale: float) -> bool:
        """Check clearance from pads, paths and other props."""
        radius = prop_radius(kind, scale)
        for pad in plan.pads:
            if math.hypot(x - pad.x, z - pad.z) < (
                    pad_radius(pad) + radius * 0.6):
                return False
        for path in plan.paths:
            if segment_distance(x, z, path) < (
                    path.width / 2 + radius * 0.6 + 0.12):
                return False
        for other in plan.props:
            gap = radius + prop_radius(other.kind, other.scale)
            if math.hypot(x - other.x, z - other.z) < gap * 0.8:
                return False
        return True


def prop_radius(kind: str, scale: float) -> float:
    """Approximate footprint radius of a prop."""
    base = {"rock": 0.3, "crystal": 0.24}[kind]
    return base * scale
