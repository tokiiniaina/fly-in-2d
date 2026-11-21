"""The checker must accept a flight whose link is written in reverse."""

import tempfile
import unittest
from pathlib import Path

from flyin.src.engine.checker import OutputChecker
from flyin.src.engine.simulator import Simulator
from flyin.src.parser_function import MapParser

MAP = """nb_drones: 1
start_hub: s 0 0
end_hub: e 4 0
hub: r 2 0 [zone=restricted]
connection: r-s
connection: r-e
"""


class LinkLabelOrderTest(unittest.TestCase):
    """The connection is written r-s but the drone flies s to r."""

    def test_output_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "map.txt"
            path.write_text(MAP, encoding="utf-8")
            data = MapParser().parse(str(path))
        lines = Simulator(data).run()
        OutputChecker(data).check(lines)
