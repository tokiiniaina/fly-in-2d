
"""Distance of every zone to the end zone using reverse Dijkstra."""

import heapq

from flyin.src.map_data import MapData
from flyin.src.zone import ENTRY_COST


def build_neighbors(data: MapData) -> dict[str, list[str]]:
    """Build adjacency lists while preserving connection order."""
    neighbors: dict[str, list[str]] = {
        name: [] for name in data.zones
    }

    for connection in data.connections:
        neighbors[connection.zone1].append(connection.zone2)
        neighbors[connection.zone2].append(connection.zone1)

    return neighbors


class DistanceMap:
    """Store the shortest distance from every zone to the end."""

    def __init__(self, data: MapData) -> None:
        """Build the reverse Dijkstra distance table."""
        self._dist: dict[str, int] = self._build(data)

    @staticmethod
    def _build(data: MapData) -> dict[str, int]:
        """Return the distance to the end for every reachable zone."""
        if data.end_hub is None:
            return {}

        end = data.end_hub

        if data.zones[end].zone_type not in ENTRY_COST:
            return {}

        neighbors = build_neighbors(data)

        distances: dict[str, int] = {end: 0}
        queue: list[tuple[int, str]] = [(0, end)]

        while queue:
            distance, zone = heapq.heappop(queue)

            if distance > distances[zone]:
                continue

            cost = ENTRY_COST[data.zones[zone].zone_type]

            for previous in neighbors[zone]:
                if data.zones[previous].zone_type not in ENTRY_COST:
                    continue

                candidate = distance + cost

                if candidate < distances.get(previous, candidate + 1):
                    distances[previous] = candidate
                    heapq.heappush(queue, (candidate, previous))

        return distances

    def to_end(self, zone: str) -> int | None:
        """Return the distance to the end, or None if unreachable."""
        return self._dist.get(zone)
