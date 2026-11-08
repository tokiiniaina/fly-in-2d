"""Plan, replay and format a whole simulation."""

from flyin.src.engine.checker import OutputChecker
from flyin.src.engine.formatter import OutputFormatter
from flyin.src.engine.network import Network
from flyin.src.engine.scheduler import Scheduler, SpaceTimeScheduler
from flyin.src.engine.simulation import Simulation
from flyin.src.map_data import MapData


class Solver:
    """Turn a parsed map into the output lines of the subject."""

    def __init__(self, scheduler: Scheduler | None = None) -> None:
        """Use the given scheduler, or the space-time A* by default."""
        self._scheduler = scheduler or SpaceTimeScheduler()

    def solve(self, data: MapData) -> list[str]:
        """Return one text line per turn, checked against the rules."""
        network = Network(data)
        network.validate()
        plan = self._scheduler.plan(network)
        records = Simulation(network, plan).run()
        lines = OutputFormatter().lines(records)
        OutputChecker(data).check(lines)
        return lines
