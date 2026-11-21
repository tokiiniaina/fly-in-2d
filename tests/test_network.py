"""Tests for the engine's read-only network view."""

import unittest
from pathlib import Path

from flyin.src.engine.network import Network
from flyin.src.engine.scheduler import SpaceTimeScheduler
from flyin.src.parser_function import MapParser

ROOT = Path(__file__).resolve().parents[1]


class NetworkTests(unittest.TestCase):
    """The planner network exposes zone costs and supports scheduling."""

    def test_entry_cost_and_scheduler(self) -> None:
        data = MapParser().parse(str(ROOT / "maps/02_simple_fork.txt"))
        network = Network(data)

        self.assertEqual(network.entry_cost("start"), 1)
        self.assertEqual(network.entry_cost("junction"), 1)
        self.assertEqual(network.entry_cost("path_b"), 2)
        plan = SpaceTimeScheduler().plan(network)
        self.assertEqual(len(plan.trajectories), data.nb_drones)
