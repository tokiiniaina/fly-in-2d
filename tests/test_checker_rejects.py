"""Reject invalid simulator output with a small parsed map."""

import tempfile
import unittest
from pathlib import Path

from flyin.src.engine.checker import OutputChecker
from flyin.src.parser_function import MapParser


MAP = """nb_drones: 2
start_hub: s 0 0
end_hub: e 4 0
hub: a 1 0 [max_drones={a_capacity}]
hub: b 1 1 [zone=blocked]
hub: r 2 0 [zone=restricted]
hub: x 8 0
connection: s-a [max_link_capacity={s_a_capacity}]
connection: s-e
connection: s-b
connection: s-r
connection: r-e
"""


class CheckerRejectsTests(unittest.TestCase):
    """Cover invalid outputs rejected by OutputChecker."""

    def assert_rejected(
        self,
        lines: list[str],
        *,
        a_capacity: int = 2,
        s_a_capacity: int = 2,
    ) -> None:
        """Parse a temporary map and assert its output is rejected."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "map.txt"
            path.write_text(
                MAP.format(
                    a_capacity=a_capacity,
                    s_a_capacity=s_a_capacity,
                ),
                encoding="utf-8",
            )
            data = MapParser().parse(str(path))

        with self.assertRaises(ValueError):
            OutputChecker(data).check(lines)

    def test_unknown_drone(self) -> None:
        self.assert_rejected(["D3-a"])

    def test_drone_moves_twice(self) -> None:
        self.assert_rejected(["D1-a D1-e"])

    def test_drone_moves_after_delivery(self) -> None:
        self.assert_rejected(["D1-e", "D1-s"])

    def test_zones_must_be_connected(self) -> None:
        self.assert_rejected(["D1-x"])

    def test_blocked_zone_cannot_be_entered(self) -> None:
        self.assert_rejected(["D1-b"])

    def test_zone_capacity_cannot_be_exceeded(self) -> None:
        self.assert_rejected(
            ["D1-a D2-a"],
            a_capacity=1,
        )

    def test_link_capacity_cannot_be_exceeded(self) -> None:
        self.assert_rejected(
            ["D1-a D2-a"],
            s_a_capacity=1,
        )

    def test_restricted_zone_requires_flight_token(self) -> None:
        self.assert_rejected(["D1-r"])

    def test_restricted_flight_must_land_next_turn(self) -> None:
        self.assert_rejected(["D1-s-r", ""])

    def test_every_drone_must_be_delivered(self) -> None:
        self.assert_rejected([])
