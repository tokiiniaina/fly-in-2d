"""Validate Solver output on the current valid test maps."""

import unittest
from pathlib import Path

from flyin.src.engine.checker import OutputChecker
from flyin.src.engine.solver import Solver
from flyin.src.parser_function import MapParser

ROOT = Path(__file__).resolve().parents[1]
MAP_DIRECTORIES = (ROOT / "maps", ROOT / "tests" / "maps")
INVALID_MAPS = {"00_restricted_zone_check.txt"}


class SolverMapTests(unittest.TestCase):
    """Check that Solver produces valid output for every current map."""

    def test_solver_output_is_valid_for_current_maps(self) -> None:
        """Parse, solve and validate each current valid map."""
        paths = [
            path
            for directory in MAP_DIRECTORIES
            for path in sorted(directory.glob("*.txt"))
            if path.name not in INVALID_MAPS
        ]
        for path in paths:
            data = MapParser().parse(str(path))
            lines = Solver().solve(data)
            OutputChecker(data).check(lines)


if __name__ == "__main__":
    unittest.main()
