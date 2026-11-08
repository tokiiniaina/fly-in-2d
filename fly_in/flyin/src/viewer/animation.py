"""Pure animation helpers: easing curves and the drone motion planner.

Nothing here knows Ursina. Positions are in camera.ui units and time is
in seconds, so everything can be unit-tested. Animations only change how
the real backend moves are *shown*; they never decide where a drone is.
"""

import math
from dataclasses import dataclass

REVEAL_TIME = 0.35
APPEAR_TIME = 0.3
LAND_TIME = 0.22
EPSILON = 1e-9


def clamp01(value: float) -> float:
    """Limit a value to [0, 1]."""
    return max(0.0, min(1.0, value))


def ease_out_cubic(t: float) -> float:
    """Fast start, soft stop."""
    t = clamp01(t)
    return 1.0 - (1.0 - t) ** 3


def ease_in_out_cubic(t: float) -> float:
    """Soft start and soft stop (used for drone flights)."""
    t = clamp01(t)
    if t < 0.5:
        return 4.0 * t ** 3
    return 1.0 - (-2.0 * t + 2.0) ** 3 / 2.0


def ease_out_back(t: float, overshoot: float = 1.70158) -> float:
    """Reach the end with a small overshoot (pop effect)."""
    t = clamp01(t)
    c3 = overshoot + 1.0
    return 1.0 + c3 * (t - 1.0) ** 3 + overshoot * (t - 1.0) ** 2


def bump(elapsed: float, duration: float, amplitude: float) -> float:
    """Scale factor: 1, rises to 1+amplitude, back to 1 over `duration`."""
    if duration <= 0 or elapsed < 0 or elapsed > duration:
        return 1.0
    return 1.0 + amplitude * math.sin(math.pi * elapsed / duration)


def hover(clock: float, phase: float, amplitude: float,
          rate: float = 2.4) -> float:
    """Vertical offset of a floating drone."""
    return amplitude * math.sin(clock * rate + phase)


@dataclass(frozen=True)
class DroneTarget:
    """Where a drone must be shown, and whether it is shown."""

    x: float
    y: float
    visible: bool


@dataclass(frozen=True)
class DroneSample:
    """What to draw for one drone at this instant."""

    x: float
    y: float
    visible: bool
    scale_x: float
    scale_y: float


class _Track:
    """Motion state of one drone."""

    def __init__(self, target: DroneTarget) -> None:
        """Start already at the target."""
        self.x = target.x
        self.y = target.y
        self.visible = target.visible
        self.target = target
        self.from_x = target.x
        self.from_y = target.y
        self.start_at = 0.0
        self.duration = 0.0
        self.moving = False
        self.hide_at_end = False
        self.appeared_at: float | None = None
        self.landed_at: float | None = None


class DroneAnimator:
    """Smoothly move drones between the targets given by the viewer."""

    def __init__(self) -> None:
        """Start with no drone."""
        self.clock = 0.0
        self._tracks: dict[int, _Track] = {}

    @property
    def moving(self) -> bool:
        """Tell whether a drone is still flying."""
        return any(t.moving for t in self._tracks.values())

    def go(self, targets: dict[int, DroneTarget], duration: float,
           appear_delay: float | None = None) -> None:
        """Send every drone to its target.

        With `duration` <= 0 drones jump there. `appear_delay` makes the
        drones created by this call pop in after that many seconds.
        """
        order = 0
        for drone_id in sorted(targets):
            target = targets[drone_id]
            track = self._tracks.get(drone_id)
            if track is None:
                track = _Track(target)
                if appear_delay is not None and target.visible:
                    track.appeared_at = self.clock + appear_delay
                self._tracks[drone_id] = track
                continue
            if self._same(track.target, target):
                continue
            delay = duration * 0.05 * (order % 6)
            order += 1
            self._retarget(track, target, duration, delay)

    def _retarget(self, track: _Track, target: DroneTarget,
                  duration: float, delay: float) -> None:
        """Start a flight from the current position to a new target."""
        if target.visible and not track.target.visible:
            track.visible = True
            track.appeared_at = self.clock + delay
        track.target = target
        track.from_x, track.from_y = track.x, track.y
        track.hide_at_end = not target.visible
        if duration <= 0:
            track.x, track.y = target.x, target.y
            track.moving = False
            track.visible = target.visible
            return
        track.start_at = self.clock + delay
        track.duration = max(duration - delay, 0.02)
        track.moving = True

    @staticmethod
    def _same(a: DroneTarget, b: DroneTarget) -> bool:
        """Tell whether two targets are the same place."""
        return (a.visible == b.visible and abs(a.x - b.x) < EPSILON
                and abs(a.y - b.y) < EPSILON)

    def tick(self, dt: float) -> None:
        """Advance the clock and every flight."""
        self.clock += dt
        for track in self._tracks.values():
            if not track.moving:
                continue
            progress = clamp01(
                (self.clock - track.start_at) / track.duration)
            eased = ease_in_out_cubic(progress)
            track.x = track.from_x + (track.target.x - track.from_x) * eased
            track.y = track.from_y + (track.target.y - track.from_y) * eased
            if progress >= 1.0:
                track.moving = False
                track.landed_at = self.clock
                if track.hide_at_end:
                    track.visible = False

    def sample(self, drone_id: int) -> DroneSample:
        """Return what to draw for a drone now."""
        track = self._tracks[drone_id]
        scale_x = scale_y = 1.0
        visible = track.visible
        if track.appeared_at is not None:
            age = self.clock - track.appeared_at
            visible = visible and age >= 0
            pop = ease_out_back(age / APPEAR_TIME)
            scale_x = scale_y = max(pop, EPSILON)
        if track.moving:
            progress = clamp01(
                (self.clock - track.start_at) / track.duration)
            wave = math.sin(math.pi * progress)
            scale_x *= 1.0 + 0.07 * wave
            scale_y *= 1.0 - 0.05 * wave
        elif track.landed_at is not None:
            land = bump(self.clock - track.landed_at, LAND_TIME, 0.10)
            scale_x *= land
            scale_y *= land
        return DroneSample(track.x, track.y, visible, scale_x, scale_y)
