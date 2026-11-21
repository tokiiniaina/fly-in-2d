"""Drones of the 3D scene, driven by the real backend simulation.

The positions come from the Timeline built from the lines the existing
Simulator printed. This module only shows them: smooth flights (reusing
the tested DroneAnimator) and procedural poses (DroneRig). Speed changes
how long a turn stays on screen, never the result.
"""

import math

from flyin.src.viewer.adapters.simulation_adapter import (
    SimulationResult,
    TurnState,
)
from flyin.src.viewer.animation import DroneAnimator
from flyin.src.viewer.playback import PlaybackController
from flyin.src.viewer3d.drone_actor import DroneActor, DroneParts
from flyin.src.viewer3d.drone_layout import (
    PAD_TOP,
    drone_scale,
    ground_height,
    targets_for_state,
)
from flyin.src.viewer3d.drone_rig import DroneRig
from flyin.src.viewer3d.pad_pulse import (
    GOAL_AMPLITUDE,
    LANDING_AMPLITUDE,
    PadPulser,
)
from flyin.src.viewer3d.scene import MapScene

FLIGHT_SHARE = 0.75
INTRO_DELAY = 0.3
CELEBRATE_AT = 0.85


class Simulation3D:
    """Plays a backend result with 3D drones on a MapScene."""

    def __init__(self, scene: MapScene, result: SimulationResult) -> None:
        """Create one actor and one rig per drone, and start playing."""
        self.scene = scene
        self.result = result
        plan = scene.plan
        data = result.data
        self._pads = {pad.name: pad for pad in plan.pads}
        self._end = data.end_hub or ""
        self.scale = drone_scale(plan.pads[0].half)
        start, end = self._pads[data.start_hub or ""], self._pads[self._end]
        heading = math.degrees(math.atan2(end.x - start.x, end.z - start.z))
        parts = DroneParts(scene.colors)
        self.controller = PlaybackController(result.timeline.total_turns)
        self.controller.play()
        self.animator = DroneAnimator()
        self.rigs: dict[int, DroneRig] = {}
        self.actors: dict[int, DroneActor] = {}
        self._ground: dict[int, float] = {}
        self._cheer: dict[int, float] = {}
        self._at_end: set[int] = set()
        self.pulser = PadPulser()
        self._pulsing: set[str] = set()
        for drone_id in range(1, data.nb_drones + 1):
            self.rigs[drone_id] = DroneRig(drone_id, self.scale, heading)
            self.actors[drone_id] = DroneActor(scene.root, parts,
                                               self.scale)
            self._ground[drone_id] = PAD_TOP
        self._first = True
        self._clock = 0.0
        self.show(self.state(), 0.0)

    def state(self) -> TurnState:
        """The real backend state of the current turn."""
        return self.result.timeline.state(self.controller.turn)

    def show(self, state: TurnState, duration: float) -> None:
        """Send every drone to where the backend says it is."""
        targets = targets_for_state(self.scene.plan, state, self.scale)
        if self._first:
            self.animator.go(targets, 0.0, INTRO_DELAY)
            self._first = False
        else:
            self.animator.go(targets, duration)
        arrived: set[int] = set()
        for drone in state.drones:
            pad = self._pads.get(drone.zone) if drone.zone else None
            self._ground[drone.drone_id] = (PAD_TOP if pad is None
                                            else ground_height(pad))
            if drone.zone == self._end:
                arrived.add(drone.drone_id)
        for drone_id in arrived - self._at_end:
            if duration > 0:
                self._cheer[drone_id] = self._clock + duration * CELEBRATE_AT
        self._at_end = arrived
        if duration > 0:
            for drone in state.drones:
                if drone.zone is not None and drone.drone_id in state.moved:
                    amplitude = (GOAL_AMPLITUDE if drone.zone == self._end
                                 else LANDING_AMPLITUDE)
                    self.pulser.schedule(
                        drone.zone, self._clock + duration * CELEBRATE_AT,
                        amplitude)

    def refresh(self, animate: bool) -> None:
        """Show the current turn (animated, or by a jump)."""
        duration = 0.0
        if animate:
            duration = max(0.06, self.controller.turn_seconds
                           * FLIGHT_SHARE)
        self.show(self.state(), duration)

    def tick(self, dt: float) -> bool:
        """Advance playback and animation; True if the turn changed."""
        changed = self.controller.tick(dt)
        if changed:
            self.refresh(animate=True)
        self._clock += dt
        self._apply_pulses()
        self.animator.tick(dt)
        for drone_id, rig in self.rigs.items():
            due = self._cheer.get(drone_id)
            if due is not None and self._clock >= due:
                rig.celebrate()
                del self._cheer[drone_id]
            sample = self.animator.sample(drone_id)
            pop = math.sqrt(sample.scale_x * sample.scale_y)
            pose = rig.update(dt, sample.x, sample.y,
                              self._ground[drone_id],
                              self.animator.flight_progress(drone_id))
            self.actors[drone_id].apply(pose, sample.visible, pop)
        return changed

    def _apply_pulses(self) -> None:
        """Scale the pads that are pulsing (and settle the finished)."""
        live = set(self.pulser.active(self._clock))
        for name in live | self._pulsing:
            entity = self.scene.pad_entities.get(name)
            if entity is None:
                continue
            wide, high = self.pulser.scale(name, self._clock)
            entity.scale = (wide, high, wide)
        self._pulsing = live

    def destroy(self) -> None:
        """Remove every drone and restore the pads."""
        for name in self._pulsing:
            entity = self.scene.pad_entities.get(name)
            if entity is not None:
                entity.scale = (1, 1, 1)
        for actor in self.actors.values():
            actor.destroy()
