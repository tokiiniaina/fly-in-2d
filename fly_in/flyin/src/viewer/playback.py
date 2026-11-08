"""Playback state machine: which turn is shown, and how fast it advances.

This is a pure view concern. The speed only changes how long a turn stays
on screen, never the backend result or the number of turns.
"""

from enum import Enum

SPEEDS: tuple[float, ...] = (0.25, 0.5, 1.0, 2.0, 4.0, 8.0)
DEFAULT_SPEED_INDEX = 2
BASE_TURN_SECONDS = 1.0


class PlaybackStatus(Enum):
    """What the HUD shows as the simulation status."""

    READY = "READY"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    FINISHED = "FINISHED"


class PlaybackController:
    """Walk through the turns of a timeline."""

    def __init__(self, total_turns: int,
                 speed_index: int = DEFAULT_SPEED_INDEX) -> None:
        """Start at turn 0, not playing."""
        self.total_turns = total_turns
        self.turn = 0
        self.speed_index = speed_index
        self._playing = False
        self._started = False
        self._elapsed = 0.0

    @property
    def speed(self) -> float:
        """Current speed multiplier."""
        return SPEEDS[self.speed_index]

    @property
    def turn_seconds(self) -> float:
        """How long one turn stays on screen at the current speed."""
        return BASE_TURN_SECONDS / self.speed

    @property
    def speed_label(self) -> str:
        """Speed as shown in the HUD, for example '0.5x'."""
        return f"{self.speed:g}x"

    @property
    def status(self) -> PlaybackStatus:
        """Current status."""
        if self.turn >= self.total_turns and self._started:
            return PlaybackStatus.FINISHED
        if self._playing:
            return PlaybackStatus.PLAYING
        if self._started:
            return PlaybackStatus.PAUSED
        return PlaybackStatus.READY

    def play(self) -> None:
        """Start, resume, or replay from the beginning when finished."""
        if self.turn >= self.total_turns and self._started:
            self.turn = 0
        self._started = True
        self._playing = self.turn < self.total_turns
        self._elapsed = 0.0

    def pause(self) -> None:
        """Stop advancing, keep the current turn."""
        self._playing = False

    def toggle(self) -> None:
        """Pause when playing, play otherwise."""
        if self._playing:
            self.pause()
        else:
            self.play()

    def restart(self) -> None:
        """Go back to turn 0 and play."""
        self.turn = 0
        self._started = False
        self.play()

    def faster(self) -> None:
        """Select the next higher speed."""
        self.speed_index = min(self.speed_index + 1, len(SPEEDS) - 1)

    def slower(self) -> None:
        """Select the next lower speed."""
        self.speed_index = max(self.speed_index - 1, 0)

    def step(self, delta: int) -> bool:
        """Move by whole turns while paused; return True on change."""
        target = max(0, min(self.turn + delta, self.total_turns))
        changed = target != self.turn
        self.turn = target
        self._playing = False
        self._started = self._started or changed
        return changed

    def tick(self, dt: float) -> bool:
        """Advance with the elapsed time; return True if the turn changed."""
        if not self._playing:
            return False
        self._elapsed += dt * self.speed
        changed = False
        while self._elapsed >= BASE_TURN_SECONDS and \
                self.turn < self.total_turns:
            self._elapsed -= BASE_TURN_SECONDS
            self.turn += 1
            changed = True
        if self.turn >= self.total_turns:
            self._playing = False
        return changed
