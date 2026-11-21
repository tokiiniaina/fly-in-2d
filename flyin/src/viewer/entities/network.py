"""The whole network: roads, zones and the pool of animated drones."""

import math
from typing import Any

from ursina import Entity, destroy

from flyin.src.map_data import MapData
from flyin.src.viewer.adapters.simulation_adapter import (
    DroneSnapshot,
    TurnState,
)
from flyin.src.viewer.animation import (
    DroneAnimator,
    DroneTarget,
    clamp01,
    ease_out_cubic,
    hover,
)
from flyin.src.viewer.catalog import DroneSkin
from flyin.src.viewer.entities.connection import ConnectionLayer
from flyin.src.viewer.entities.drone import DroneView
from flyin.src.viewer.entities.zone import ZoneView
from flyin.src.viewer.layout import (
    MAX_VISIBLE_DRONES,
    NetworkLayout,
    Rect,
    cluster_offsets,
)

REVEAL_SPAN = 0.45
ROADS_TIME = 0.5
ARRIVAL_PULSE = 0.8


class NetworkView:
    """Generate and animate the drawing of a map.

    Everything comes from the parsed map: coordinates, connections, zone
    types, colors and capacities. With `texture` set, a sprite is created
    for each drone; without it only the empty network is drawn (menu
    preview). With `intro`, the roads grow from the center and the zones
    pop in as a wave, then the drones appear.
    """

    def __init__(self, parent: Any, data: MapData, area: Rect,
                 skin: DroneSkin | None = None, texture: Any = None,
                 intro: bool = False) -> None:
        """Draw the network inside `area`."""
        self.root = Entity(parent=parent)
        self.layout = NetworkLayout(data, area)
        layout = self.layout
        self._intro = intro
        self._clock = 0.0
        blocked = {n for n, z in data.zones.items()
                   if z.zone_type == "blocked"}
        self._roads = ConnectionLayer(self.root, layout, data.connections,
                                      blocked)
        self.zones: dict[str, ZoneView] = {}
        for name, zone in data.zones.items():
            kind = zone.zone_type
            if name == data.start_hub:
                kind = "start"
            elif name == data.end_hub:
                kind = "end"
            x, y = layout.positions[name]
            self.zones[name] = ZoneView(
                self.root, name, kind, x, y, layout.node_radius,
                zone.color, zone.max_drones, layout.name_fits(name))
        if intro:
            self._start_intro()
        self.drones: dict[int, DroneView] = {}
        if skin is not None and texture is not None:
            for drone_id in range(1, data.nb_drones + 1):
                self.drones[drone_id] = DroneView(
                    self.root, drone_id, texture, skin.aspect,
                    layout.drone_height)
        self.animator = DroneAnimator()
        self._placed = False

    def _start_intro(self) -> None:
        """Schedule the wave: zones far from the center come last."""
        area = self.layout.area
        spread = {
            name: math.hypot(x - area.cx, y - area.cy)
            for name, (x, y) in self.layout.positions.items()}
        farthest = max(spread.values(), default=0.0) or 1.0
        for name, zone in self.zones.items():
            zone.reveal(REVEAL_SPAN * spread[name] / farthest)
        self._roads.set_scale(0.0)

    def show_state(self, state: TurnState, duration: float = 0.0) -> None:
        """Send every drone where the backend says it is.

        With `duration` > 0 the drones fly there smoothly; otherwise they
        jump (after a rebuild, a restart, a step back...).
        """
        targets = self._targets(state)
        if not self._placed:
            delay = REVEAL_SPAN + 0.1 if self._intro else None
            self.animator.go(targets, 0.0, delay)
            self._placed = True
        else:
            self.animator.go(targets, duration)
        by_zone: dict[str, list[DroneSnapshot]] = {}
        for drone in state.drones:
            if drone.zone is not None:
                by_zone.setdefault(drone.zone, []).append(drone)
        for name, zone in self.zones.items():
            group = by_zone.get(name, [])
            zone.set_occupancy(len(group), MAX_VISIBLE_DRONES)
            zone.set_delivered(zone.kind == "end" and len(group) > 0)
            if duration > 0 and any(d.drone_id in state.moved
                                    for d in group):
                zone.pulse(duration * ARRIVAL_PULSE)
        self._apply()

    def _targets(self, state: TurnState) -> dict[int, DroneTarget]:
        """Where each drone sprite must be shown for a state."""
        zone_groups: dict[str, list[DroneSnapshot]] = {}
        link_groups: dict[frozenset[str], list[DroneSnapshot]] = {}
        for drone in state.drones:
            if drone.zone is not None:
                zone_groups.setdefault(drone.zone, []).append(drone)
            elif drone.flight is not None:
                key = frozenset(drone.flight)
                link_groups.setdefault(key, []).append(drone)
        targets: dict[int, DroneTarget] = {}
        pos = self.layout.positions
        for name, group in zone_groups.items():
            x, y = pos[name]
            self._spread(targets, group, x, y)
        for key, group in link_groups.items():
            first, second = sorted(key)
            x = (pos[first][0] + pos[second][0]) / 2
            y = (pos[first][1] + pos[second][1]) / 2
            self._spread(targets, group, x, y)
        return targets

    def _spread(self, targets: dict[int, DroneTarget],
                group: list[DroneSnapshot], x: float, y: float) -> None:
        """Fan a group of drones around a point."""
        shown = group[:MAX_VISIBLE_DRONES]
        spread = self.layout.drone_height * 0.45
        offsets = cluster_offsets(len(shown), spread)
        for index, drone in enumerate(group):
            if index < len(shown):
                dx, dy = offsets[index]
                targets[drone.drone_id] = DroneTarget(x + dx, y + dy, True)
            else:
                targets[drone.drone_id] = DroneTarget(x, y, False)

    def update(self, dt: float) -> None:
        """Advance the intro, the zone effects and the drone flights."""
        self._clock += dt
        if self._intro:
            progress = clamp01(self._clock / ROADS_TIME)
            self._roads.set_scale(ease_out_cubic(progress))
            if progress >= 1.0:
                self._intro = False
        for zone in self.zones.values():
            zone.update(dt)
        self.animator.tick(dt)
        self._apply()

    def _apply(self) -> None:
        """Push the animator samples (plus a gentle hover) to the sprites."""
        amplitude = self.layout.drone_height * 0.05
        for drone_id, view in self.drones.items():
            if not self._placed:
                return
            sample = self.animator.sample(drone_id)
            lift = max(hover(self._clock, drone_id * 1.7, amplitude)
                       + amplitude, 0.0)
            view.apply(sample.x, sample.y, sample.visible,
                       sample.scale_x, sample.scale_y, lift)

    def destroy(self) -> None:
        """Remove every entity of the network."""
        destroy(self.root)
