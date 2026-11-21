"""Tests of the subject targets and the end-of-run summary."""

import unittest

from flyin.src.viewer3d.benchmarks import (
    TARGETS,
    summary_lines,
    target_for,
)


class BenchmarkTests(unittest.TestCase):
    """Targets come from the subject; the summary tells the truth."""

    def test_targets_of_the_subject(self) -> None:
        """Every reference target of the subject is listed."""
        expected = {"01_linear_path.txt": 6, "02_simple_fork.txt": 8,
                    "03_basic_capacity.txt": 6, "01_dead_end_trap.txt": 12,
                    "02_circular_loop.txt": 15,
                    "03_priority_puzzle.txt": 12,
                    "01_maze_nightmare.txt": 30, "02_capacity_hell.txt": 35,
                    "03_ultimate_challenge.txt": 45,
                    "01_the_impossible_dream.txt": 45}
        for name, target in expected.items():
            self.assertEqual(target_for(name), target, name)
        self.assertEqual(len(TARGETS), len(expected))
        self.assertIsNone(target_for("my_own_map.txt"))

    def test_summary_ok_and_above_target(self) -> None:
        """OK when within the target, ABOVE TARGET otherwise."""
        ok = summary_lines(4, 4, 5, 8, True)
        self.assertEqual(ok[0], "ALL DRONES DELIVERED")
        self.assertIn("TURNS: 5", ok[1])
        self.assertTrue(ok[1].endswith("OK"))
        late = summary_lines(4, 4, 9, 8, True)
        self.assertTrue(late[1].endswith("ABOVE TARGET"))
        self.assertTrue(summary_lines(4, 4, 8, 8, True)[1].endswith("OK"))

    def test_summary_incomplete_and_unknown_target(self) -> None:
        """Missing drones are reported; no target means no verdict."""
        lines = summary_lines(2, 5, 12, None, False)
        self.assertEqual(lines[0], "INCOMPLETE: 2 / 5 DELIVERED")
        self.assertNotIn("TARGET", lines[1])
        self.assertEqual(lines[2], "OUTPUT: INVALID")

    def test_no_angle_brackets(self) -> None:
        """Ursina reads angle brackets as tags: none in the texts."""
        for line in summary_lines(1, 1, 1, 1, True):
            self.assertNotIn("<", line)
            self.assertNotIn(">", line)


if __name__ == "__main__":
    unittest.main()
