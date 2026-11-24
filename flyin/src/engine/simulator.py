"""Turn-by-turn simulation: every drone moves closer to the end."""

from collections import Counter
from dataclasses import dataclass

from flyin.src.connection import Connection
from flyin.src.engine.distances import DistanceMap
from flyin.src.map_data import MapData
from flyin.src.zone import ENTRY_COST

MAX_TURNS = 10000
UNLIMITED = 10 ** 9


@dataclass
class Drone:
    """One drone: its zone, and (origin, destination) while it flies."""

    drone_id: int
    zone: str
    flight: tuple[str, str] | None = None


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
        self._links: dict[frozenset[str], Connection] = {}
        for c in data.connections:
            self._links[frozenset((c.zone1, c.zone2))] = c
            self._neighbors[c.zone1].append(c.zone2)
            self._neighbors[c.zone2].append(c.zone1)
        self._capacity: dict[str, int] = {
            name: zone.max_drones for name, zone in data.zones.items()}
        self._capacity[self._start] = UNLIMITED
        self._capacity[self._end] = UNLIMITED
        # Slots taken per zone: drones inside it plus drones flying to it.
        self._held: Counter[str] = Counter({self._start: data.nb_drones})

    def run(self) -> list[str]:
        """Simulate until every drone is delivered."""
        if self._dist.to_end(self._start) is None:
            raise ValueError("the end zone cannot be reached")
        lines: list[str] = []
        while any(d.zone != self._end for d in self._drones):
            if len(lines) >= MAX_TURNS:
                raise ValueError("simulation does not finish")
            lines.append(" ".join(self._play_turn()))
        return lines

    def _play_turn(self) -> list[str]:
        """Play one turn: landings first, then the closest drones."""
        links: Counter[frozenset[str]] = Counter()
        flying = [d for d in self._drones if d.flight is not None]
        waiting = [d for d in self._drones
                   if d.flight is None and d.zone != self._end]
        waiting.sort(key=lambda d: (self._dist.to_end(d.zone) or 0,
                                    d.drone_id))
        moves = [self._land(d, links) for d in flying]
        for drone in waiting:
            target = self._choose(drone, links)
            if target is not None:
                moves.append(self._move(drone, target, links))
        return moves

    def _land(self, drone: Drone, links: Counter[frozenset[str]]) -> str:
        """End a flight to a restricted zone (it still uses the link)."""
        assert drone.flight is not None
        links[frozenset(drone.flight)] += 1
        drone.zone = drone.flight[1]
        drone.flight = None
        return f"D{drone.drone_id}-{drone.zone}"

    def _choose(self, drone: Drone,
                links: Counter[frozenset[str]]) -> str | None:
        """Best neighbor that is closer to the end and has room."""
        here = self._dist.to_end(drone.zone)
        options: list[tuple[int, int, int, str]] = []
        for nxt in self._neighbors[drone.zone]:
            dist = self._dist.to_end(nxt)
            if here is None or dist is None or dist >= here:
                continue
            key = frozenset((drone.zone, nxt))
            link = self._links[key]
            if (links[key] < link.max_link_capacity
                    and self._held[nxt] < self._capacity[nxt]):
                kind = self._data.zones[nxt].zone_type
                capacity = min(link.max_link_capacity, self._capacity[nxt])
                options.append((ENTRY_COST[kind] + dist,
                                0 if kind == "priority" else 1,
                                -capacity, nxt))
        return min(options)[3] if options else None

    def _move(self, drone: Drone, dst: str,
              links: Counter[frozenset[str]]) -> str:
        """Apply a move; a restricted zone starts a two-turn flight."""
        key = frozenset((drone.zone, dst))
        links[key] += 1
        self._held[drone.zone] -= 1
        self._held[dst] += 1
        if self._data.zones[dst].zone_type == "restricted":
            link = self._links[key]
            drone.flight = (drone.zone, dst)
            return f"D{drone.drone_id}-{link.zone1}-{link.zone2}"
        drone.zone = dst
        return f"D{drone.drone_id}-{dst}"
