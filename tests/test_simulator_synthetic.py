"""Synthetic small-map tests for the base greedy simulator."""

import unittest

from flyin.src.connection import Connection
from flyin.src.engine.checker import OutputChecker
from flyin.src.engine.simulator import Simulator
from flyin.src.map_data import MapData
from flyin.src.zone import Zone


def line_map(zone_count: int, restricted_index: int) -> MapData:
    """Build a four-drone corridor with a restricted zone in the middle."""
    zones = {
        f"z{index}": Zone(
            name=f"z{index}",
            x=index,
            y=0,
            zone_type=("restricted" if index == restricted_index
                       else "normal"),
            max_drones=2,
        )
        for index in range(zone_count)
    }
    links = [
        Connection(f"z{index}", f"z{index + 1}", max_link_capacity=2)
        for index in range(zone_count - 1)
    ]
    return MapData(
        nb_drones=4,
        zones=zones,
        connections=links,
        start_hub="z0",
        end_hub=f"z{zone_count - 1}",
    )


class SyntheticSimulatorTests(unittest.TestCase):
    """Check correctness and routing priorities on controlled maps."""

    def test_restricted_corridors_from_three_to_ten_zones(self) -> None:
        """All four drones are delivered without exceeding capacities."""
        for zone_count in range(3, 11):
            with self.subTest(zone_count=zone_count):
                restricted_index = zone_count // 2
                data = line_map(zone_count, restricted_index)
                lines = Simulator(data).run()

                OutputChecker(data).check(lines)
                self.assertEqual(len(lines), zone_count + 2)

    def test_restricted_zone_capacity_reservation(self) -> None:
        """Two approaches cannot overfill a capacity-one zone."""
        zones = {
            "start": Zone("start", 0, 0),
            "alpha": Zone("alpha", 1, 1),
            "beta": Zone("beta", 1, -1),
            "restricted": Zone(
                "restricted", 2, 0, zone_type="restricted", max_drones=1
            ),
            "end": Zone("end", 3, 0),
        }
        links = [
            Connection("start", "alpha", 1),
            Connection("start", "beta", 1),
            Connection(
                "alpha", "restricted", 1
            ),
            Connection("beta", "restricted", 1),
            Connection("restricted", "end", 2),
        ]
        data = MapData(2, zones, links, "start", "end")

        lines = Simulator(data).run()

        OutputChecker(data).check(lines)
        takeoffs = [
            token for line in lines for token in line.split()
            if (token.endswith("-alpha-restricted")
                or token.endswith("-beta-restricted"))
        ]
        self.assertEqual(len(takeoffs), 2)

    def test_priority_zone_wins_when_route_costs_tie(self) -> None:
        """A priority zone breaks a tie between equal-length routes."""
        zones = {
            "start": Zone("start", 0, 0),
            "priority": Zone("priority", 1, 1, zone_type="priority"),
            "normal": Zone("normal", 1, -1),
            "merge": Zone("merge", 2, 0),
            "end": Zone("end", 3, 0),
        }
        links = [
            Connection("start", "priority", max_link_capacity=1),
            Connection("start", "normal", max_link_capacity=1),
            Connection("priority", "merge", max_link_capacity=1),
            Connection("normal", "merge", max_link_capacity=1),
            Connection("merge", "end", max_link_capacity=1),
        ]
        data = MapData(1, zones, links, "start", "end")

        lines = Simulator(data).run()

        OutputChecker(data).check(lines)
        self.assertEqual(lines[0], "D1-priority")

    def test_shorter_normal_route_wins_over_priority_detour(self) -> None:
        """Priority does not outweigh a route that takes fewer turns."""
        zones = {
            "start": Zone("start", 0, 0),
            "priority": Zone("priority", 1, 1, zone_type="priority"),
            "detour": Zone("detour", 2, 1),
            "normal": Zone("normal", 1, -1),
            "end": Zone("end", 2, -1),
        }
        links = [
            Connection("start", "priority"),
            Connection("priority", "detour"),
            Connection("detour", "end"),
            Connection("start", "normal"),
            Connection("normal", "end"),
        ]
        data = MapData(1, zones, links, "start", "end")

        lines = Simulator(data).run()

        OutputChecker(data).check(lines)
        self.assertEqual(lines[0], "D1-normal")
        self.assertEqual(len(lines), 2)
