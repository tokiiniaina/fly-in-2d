"""Pulse of the pads when a drone lands on them (pure)."""

from flyin.src.viewer.animation import bump

PULSE_TIME = 0.35
LANDING_AMPLITUDE = 0.12
GOAL_AMPLITUDE = 0.22


class PadPulser:
    """Schedule pulses and tell the scale of each pad at a given time."""

    def __init__(self) -> None:
        """Start with no pulse."""
        self._events: dict[str, list[tuple[float, float]]] = {}

    def schedule(self, pad: str, start: float, amplitude: float) -> None:
        """Make a pad pulse from time `start`."""
        self._events.setdefault(pad, []).append((start, amplitude))

    def scale(self, pad: str, clock: float) -> tuple[float, float]:
        """(sideways scale, height scale) of a pad now."""
        grow = 0.0
        for start, amplitude in self._events.get(pad, []):
            grow = max(grow, bump(clock - start, PULSE_TIME, amplitude)
                       - 1.0)
        return 1.0 + 0.6 * grow, 1.0 + 2.2 * grow

    def active(self, clock: float) -> list[str]:
        """Pads with a pulse not finished yet (finished ones are dropped)."""
        names = []
        for pad in list(self._events):
            alive = [(s, a) for s, a in self._events[pad]
                     if clock <= s + PULSE_TIME]
            if alive:
                self._events[pad] = alive
                names.append(pad)
            else:
                del self._events[pad]
        return names
