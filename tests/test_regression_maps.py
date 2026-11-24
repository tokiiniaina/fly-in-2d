"""Turn counts and validity of the provided maps must not regress."""

import unittest
from pathlib import Path

from flyin.src.engine.checker import OutputChecker
from flyin.src.engine.simulator import Simulator
from flyin.src.parser_function import MapParser

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TURNS: dict[str, int] = {
    "01_linear_path.txt": 4,
    "02_simple_fork.txt": 4,
    "03_basic_capacity.txt": 4,
    "01_dead_end_trap.txt": 8,
    "02_circular_loop.txt": 15,
    "03_priority_puzzle.txt": 7,
    "01_maze_nightmare.txt": 13,
    "02_capacity_hell.txt": 16,
    "03_ultimate_challenge.txt": 26,
    "01_the_impossible_dream.txt": 43,
}


class RegressionTests(unittest.TestCase):
    """Replay every map and check the turn count and the rules."""

    def test_turns_and_validity(self) -> None:
        """Each map keeps its turn count and a valid output."""
        for name, turns in EXPECTED_TURNS.items():
            with self.subTest(map=name):
                data = MapParser().parse(str(ROOT / "maps" / name))
                lines = Simulator(data).run()
                OutputChecker(data).check(lines)
                self.assertEqual(len(lines), turns)


if __name__ == "__main__":
    unittest.main()
