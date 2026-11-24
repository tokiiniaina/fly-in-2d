"""Turn-by-turn simulation: every drone moves closer to the end."""

from collections import Counter

from flyin.src.engine.distances import DistanceMap
from flyin.src.zone import ENTRY_COST
from flyin.src.map_data import MapData

MAX_TURNS = 10000


class Drone:
    """One drone: its zone, and its flight if it is in transit."""

    def __init__(self, drone_id: int, zone: str) -> None:
        """Create a drone waiting in `zone`."""
        self.drone_id = drone_id
        self.zone = zone
        self.flying_from: str | None = None
        self.flying_to: str | None = None


class Simulator:
    """Plays the simulation and returns one text line per turn."""

    def __init__(self, data: MapData) -> None:
        """Prepare drones, distances and lookup tables."""
        assert data.start_hub is not None and data.end_hub is not None
        self._data = data
        self._start: str = data.start_hub
        self._end: str = data.end_hub
        self._dist = DistanceMap(data)
        self._drones = [Drone(i, self._start)
                        for i in range(1, data.nb_drones + 1)]
        self._neighbors: dict[str, list[str]] = {n: [] for n in data.zones}
        self._link_cap: dict[frozenset[str], int] = {}
        self._link_name: dict[frozenset[str], str] = {}
        for c in data.connections:
            key = frozenset((c.zone1, c.zone2))
            self._link_cap[key] = c.max_link_capacity
            self._link_name[key] = f"{c.zone1}-{c.zone2}"
            self._neighbors[c.zone1].append(c.zone2)
            self._neighbors[c.zone2].append(c.zone1)
        self._inside: Counter[str] = Counter()
        self._incoming: Counter[str] = Counter()

    def _is_limited(self, zone: str) -> bool:
        """Start and end have no capacity limit."""
        return zone not in (self._start, self._end)

    def _delivered(self, drone: Drone) -> bool:
        """Whether the drone reached the end zone."""
        return drone.zone == self._end and drone.flying_to is None

    def _can_enter(self, zone: str) -> bool:
        """Whether the zone still has room."""
        if not self._is_limited(zone):
            return True
        used = self._inside[zone] + self._incoming[zone]
        return used < self._data.zones[zone].max_drones

    def run(self) -> list[str]:
        """Simulate until every drone is delivered."""
        if self._dist.to_end(self._start) is None:
            raise ValueError("the end zone cannot be reached")
        lines: list[str] = []
        while not all(self._delivered(d) for d in self._drones):
            if len(lines) >= MAX_TURNS:
                raise ValueError("simulation does not finish")
            lines.append(" ".join(self._play_turn()))
        return lines

    def _play_turn(self) -> list[str]:
        """Play one turn and return the movements as text."""
        links: Counter[frozenset[str]] = Counter()
        landed = self._land_flying_drones(links)
        moves = [f"D{d.drone_id}-{d.zone}" for d in landed]
        moves.extend(self._move_waiting_drones(
            links, {d.drone_id for d in landed}))
        return moves

    def _land_flying_drones(
            self, links: Counter[frozenset[str]]) -> list[Drone]:
        """Land every drone in flight (its landing still uses the link)."""
        landed: list[Drone] = []
        for drone in self._drones:
            if drone.flying_to is None or not drone.flying_from:
                continue
            key = frozenset((drone.flying_from, drone.flying_to))
            links[key] += 1
            drone.zone = drone.flying_to
            drone.flying_from = drone.flying_to = None
            if self._is_limited(drone.zone):
                self._incoming[drone.zone] -= 1
                self._inside[drone.zone] += 1
            landed.append(drone)
        return landed

    def _move_waiting_drones(self, links: Counter[frozenset[str]],
                             landed: set[int]) -> list[str]:
        """Move the drones that can, the closest to the goal first."""
        waiting = [d for d in self._drones if not self._delivered(d)
                   and d.zone != self._end and d.flying_to is None
                   and d.drone_id not in landed]
        waiting.sort(key=lambda d: (self._dist.to_end(d.zone) or 0,
                                    d.drone_id))
        moves: list[str] = []
        for drone in waiting:
            target = self._choose(drone, links)
            if target is not None:
                moves.append(self._move(drone, target, links))
        return moves

    def _score(self, src: str, nxt: str,
               dist: int) -> tuple[int, int, int, str]:
        """Rank a candidate move (lower is better).

        Order: turns to the goal, priority zone first, wider capacity,
        then the zone name to stay deterministic.
        """
        kind = self._data.zones[nxt].zone_type
        capacity = self._link_cap[frozenset((src, nxt))]
        if self._is_limited(nxt):
            capacity = min(capacity, self._data.zones[nxt].max_drones)
        return (ENTRY_COST[kind] + dist,
                0 if kind == "priority" else 1, -capacity, nxt)

    def _choose(self, drone: Drone,
                links: Counter[frozenset[str]]) -> str | None:
        """Best neighbor that is closer to the end and has room."""
        here = self._dist.to_end(drone.zone)
        if here is None:
            return None
        best: tuple[int, int, int, str] | None = None
        for nxt in self._neighbors[drone.zone]:
            dist = self._dist.to_end(nxt)
            if dist is None or dist >= here:
                continue
            key = frozenset((drone.zone, nxt))
            if links[key] >= self._link_cap[key] or not self._can_enter(nxt):
                continue
            score = self._score(drone.zone, nxt, dist)
            if best is None or score < best:
                best = score
        return None if best is None else best[3]

    def _move(self, drone: Drone, target: str,
              links: Counter[frozenset[str]]) -> str:
        """Apply a move and return its text."""
        key = frozenset((drone.zone, target))
        links[key] += 1
        if self._is_limited(drone.zone):
            self._inside[drone.zone] -= 1
        if self._data.zones[target].zone_type == "restricted":
            drone.flying_from, drone.flying_to = drone.zone, target
            if self._is_limited(target):
                self._incoming[target] += 1
            return f"D{drone.drone_id}-{self._link_name[key]}"
        if self._is_limited(target):
            self._inside[target] += 1
        drone.zone = target

        return f"D{drone.drone_id}-{target}"
