"""Tests of the pad pulse schedule (pure)."""

import unittest

from flyin.src.viewer3d.pad_pulse import PULSE_TIME, PadPulser


class PadPulserTests(unittest.TestCase):
    """A pulse rises, falls and ends."""

    def test_pulse_shape(self) -> None:
        """Scale is 1 before and after, above 1 in the middle."""
        pulser = PadPulser()
        pulser.schedule("a", 1.0, 0.2)
        self.assertEqual(pulser.scale("a", 0.5), (1.0, 1.0))
        mid = pulser.scale("a", 1.0 + PULSE_TIME / 2)
        self.assertGreater(mid[0], 1.05)
        self.assertGreater(mid[1], mid[0])
        self.assertEqual(pulser.scale("a", 1.0 + PULSE_TIME + 0.1),
                         (1.0, 1.0))
        self.assertEqual(pulser.scale("other", 1.0), (1.0, 1.0))

    def test_bigger_amplitude_bumps_more(self) -> None:
        """The goal pulse is stronger than a normal one."""
        pulser = PadPulser()
        pulser.schedule("a", 0.0, 0.1)
        pulser.schedule("b", 0.0, 0.3)
        t = PULSE_TIME / 2
        self.assertGreater(pulser.scale("b", t)[0], pulser.scale("a", t)[0])

    def test_active_and_cleanup(self) -> None:
        """Finished pulses are dropped from the active list."""
        pulser = PadPulser()
        pulser.schedule("a", 0.0, 0.1)
        pulser.schedule("b", 5.0, 0.1)
        self.assertEqual(sorted(pulser.active(0.1)), ["a", "b"])
        self.assertEqual(pulser.active(1.0), ["b"])
        self.assertEqual(pulser.active(10.0), [])


if __name__ == "__main__":
    unittest.main()
