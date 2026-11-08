"""Turn the real backend output into a per-turn state for the viewer.

The viewer never plans or invents a movement. It runs the existing
`Solver`, then replays the text lines it returned (the same lines the
command line prints) to know where every drone is after each turn.
"""

import re
from dataclasses import dataclass

from flyin.src.engine import FlyInError
from flyin.src.engine.checker import OutputChecker
from flyin.src.engine.solver import Solver
from flyin.src.map_data import MapData
from flyin.src.parser_function import MapParser

_TOKEN = re.compile(r"D(\d+)-(.+)")


@dataclass(frozen=True)
class DroneSnapshot:
    """Where one drone is: in a zone, or flying along a connection."""

    drone_id: int
    zone: str | None
    flight: tuple[str, str] | None = None


@dataclass(frozen=True)
class TurnState:
    """The whole fleet after a given turn (turn 0 is the start)."""

    index: int
    line: str
    drones: tuple[DroneSnapshot, ...]
    moved: frozenset[int]
    delivered: int


class Timeline:
    """All the states of a simulation, from turn 0 to the last turn."""

    def __init__(self, nb_drones: int, states: list[TurnState]) -> None:
        """Store the states (states[0] is the initial one)."""
        self.nb_drones = nb_drones
        self._states = states

    @property
    def total_turns(self) -> int:
        """Number of simulation turns."""
        return len(self._states) - 1

    def state(self, turn: int) -> TurnState:
        """Return the state after `turn` (clamped to the valid range)."""
        return self._states[max(0, min(turn, self.total_turns))]


class TimelineBuilder:
    """Replay the backend lines and record the fleet after each turn."""

    def __init__(self, data: MapData) -> None:
        """Remember the map; it must have a start and an end hub."""
        if data.start_hub is None or data.end_hub is None:
            raise ValueError("the map needs a start_hub and an end_hub")
        self._data = data
        self._start: str = data.start_hub
        self._end: str = data.end_hub

    def build(self, lines: list[str]) -> Timeline:
        """Return the timeline of a list of output lines.

        Raises:
            ValueError: If a line cannot be replayed on this map.
        """
        zones: dict[int, str | None] = {
            i: self._start for i in range(1, self._data.nb_drones + 1)}
        flights: dict[int, tuple[str, str]] = {}
        states = [self._snapshot(0, "", zones, flights, frozenset())]
        for turn, line in enumerate(lines, start=1):
            moved = self._apply(turn, line, zones, flights)
            states.append(
                self._snapshot(turn, line, zones, flights, moved))
        return Timeline(self._data.nb_drones, states)

    def _apply(self, turn: int, line: str, zones: dict[int, str | None],
               flights: dict[int, tuple[str, str]]) -> frozenset[int]:
        """Apply one output line to the drone positions."""
        moved: set[int] = set()
        for token in line.split():
            match = _TOKEN.fullmatch(token)
            if match is None:
                raise ValueError(f"turn {turn}: invalid movement '{token}'")
            drone = int(match.group(1))
            if drone not in zones or drone in moved:
                raise ValueError(f"turn {turn}: bad drone in '{token}'")
            moved.add(drone)
            self._move(turn, token, drone, match.group(2), zones, flights)
        for drone in flights:
            if drone not in moved:
                raise ValueError(
                    f"turn {turn}: D{drone} stays on a restricted link")
        return frozenset(moved)

    def _move(self, turn: int, token: str, drone: int, target: str,
              zones: dict[int, str | None],
              flights: dict[int, tuple[str, str]]) -> None:
        """Move one drone: landing, ordinary move or take-off."""
        if drone in flights:
            if target != flights[drone][1]:
                raise ValueError(f"turn {turn}: bad landing '{token}'")
            zones[drone] = target
            del flights[drone]
            return
        here = zones[drone]
        if here is None:
            raise ValueError(f"turn {turn}: D{drone} has no position")
        if target in self._data.zones:
            zones[drone] = target
            return
        ends = target.split("-")
        if (len(ends) == 2 and here in ends
                and all(end in self._data.zones for end in ends)):
            other = ends[1] if ends[0] == here else ends[0]
            flights[drone] = (here, other)
            zones[drone] = None
            return
        raise ValueError(f"turn {turn}: unknown destination '{token}'")

    def _snapshot(self, turn: int, line: str, zones: dict[int, str | None],
                  flights: dict[int, tuple[str, str]],
                  moved: frozenset[int]) -> TurnState:
        """Freeze the current fleet into a TurnState."""
        drones = tuple(
            DroneSnapshot(drone, zone, flights.get(drone))
            for drone, zone in sorted(zones.items()))
        delivered = sum(1 for d in drones if d.zone == self._end)
        return TurnState(turn, line, drones, moved, delivered)


@dataclass(frozen=True)
class SimulationResult:
    """Everything the viewer needs about one backend run."""

    data: MapData
    lines: list[str]
    timeline: Timeline
    check_error: str | None

    @property
    def valid(self) -> bool:
        """Tell whether the independent OutputChecker accepted the run."""
        return self.check_error is None


class SimulationAdapter:
    """Run the existing backend on a map file."""

    def run(self, map_path: str) -> SimulationResult:
        """Parse, simulate, validate and build the timeline.

        Raises:
            OSError: If the map file cannot be read.
            ValueError: If the map is invalid or the simulation fails.
            FlyInError: If the solver cannot produce a valid plan.
        """
        data = MapParser().parse(map_path)
        lines = Solver().solve(data)
        timeline = TimelineBuilder(data).build(lines)
        try:
            OutputChecker(data).check(lines)
        except (ValueError, FlyInError) as error:
            return SimulationResult(data, lines, timeline, str(error))
        return SimulationResult(data, lines, timeline, None)
