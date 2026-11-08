"""Distance of every zone to the end zone using reverse Dijkstra."""

import heapq

from flyin.src.engine.network import Network


class DistanceMap:
    """Store the shortest distance in turns from every zone to the end."""

    def __init__(self, network: Network) -> None:
        """Build the reverse Dijkstra distance table."""
        self._dist: dict[str, int] = self._build(network)

    @staticmethod
    def _build(network: Network) -> dict[str, int]:
        """Run Dijkstra from the end zone, walking the links backwards."""
        end = network.end
        if network.entry_cost(end) is None:
            return {}
        distances: dict[str, int] = {end: 0}
        queue: list[tuple[int, str]] = [(0, end)]
        while queue:
            distance, zone = heapq.heappop(queue)
            if distance > distances[zone]:
                continue
            cost = network.entry_cost(zone)
            if cost is None:
                continue
            for previous in network.neighbors(zone):
                candidate = distance + cost
                if candidate < distances.get(previous, candidate + 1):
                    distances[previous] = candidate
                    heapq.heappush(queue, (candidate, previous))
        return distances

    def to_end(self, zone: str) -> int | None:
        """Return the distance to the end, or None if unreachable."""
        return self._dist.get(zone)
