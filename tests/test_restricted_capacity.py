"""Two drones must not overfill a restricted zone of capacity 1."""

import tempfile
import unittest
from pathlib import Path

from flyin.src.engine.checker import OutputChecker
from flyin.src.engine.simulator import Simulator
from flyin.src.parser_function import MapParser

MAP = """nb_drones: 2
start_hub: s 0 0
end_hub: e 4 0
hub: a 1 1
hub: b 1 -1
hub: r 2 0 [zone=restricted]
connection: s-a
connection: s-b
connection: a-r
connection: b-r
connection: r-e [max_link_capacity=2]
"""


class RestrictedCapacityTest(unittest.TestCase):
    """Run the simulator and replay its output with the checker."""

    def test_output_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "map.txt"
            path.write_text(MAP, encoding="utf-8")
            data = MapParser().parse(str(path))
        lines = Simulator(data).run()
        OutputChecker(data).check(lines)
