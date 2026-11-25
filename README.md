*This project has been created as part of the 42 curriculum by <login>.*

# Fly-in

## Description

Fly-in routes a fleet of drones from a start hub to an end hub through a
network of zones, in as few simulation turns as possible, while respecting
zone capacities (`max_drones`), connection capacities
(`max_link_capacity`), blocked zones and the 2-turn flight to restricted
zones.

The project has two parts:

- a **backend** (parser + simulation engine), usable from the command line,
  which prints one line per turn as required by the subject;
- a **2D viewer** (Ursina) that replays the *real* backend output: menu,
  network drawing, drone sprites and a textual HUD.

## Instructions

```bash
make install     # Ursina, Pillow, flake8, mypy
make run         # opens the 2D graphical menu
make cli MAP=maps/02_simple_fork.txt   # terminal output only
make test        # unit + viewer smoke tests
make lint        # flake8 + mypy (flags required by the subject)
make debug       # pdb
make clean
```

Direct use:

```bash
python3 fly_in.py                          # graphical menu
python3 fly_in.py maps/02_simple_fork.txt  # terminal output (unchanged)
python3 fly_in.py maps/02_simple_fork.txt --gui   # output, then viewer
```

Python 3.10+ is required.

### Controls

| Where | Control | Action |
|-------|---------|--------|
| Menu | `< >` next to MAP / DRONE | choose a map file / a drone sprite |
| Menu | PLAY / QUIT | start the simulation / quit |
| HUD | PLAY, PAUSE | start or resume / freeze on the current turn |
| HUD | RESTART | run the backend again, replay from turn 0 |
| HUD | SPEED `-` `+` | 0.25x to 8x, display pace only |
| HUD | MAP: NAME | back to the menu |
| HUD | QUIT | close the application |
| Keys | space, R, esc | play/pause, restart, back to the menu |
| Keys | left/right, up/down | step a turn (animated), speed (sim) / map, drone (menu) |
| Map | W / A / S / D | move the map up / left / down / right (HUD stays fixed) |
| Map | mouse wheel up / down | zoom in / out on the map |

## Example

Input (`maps/02_simple_fork.txt`, 4 drones) and the output printed by
`make cli MAP=maps/02_simple_fork.txt` (5 turns):

```
D1-junction D2-junction
D1-path_a D2-junction-path_b D3-junction D4-junction
D2-path_b D1-goal D3-path_a
D2-goal D3-goal D4-path_a
D4-goal
```

`D2-junction-path_b` is a drone in flight toward a restricted zone: it must
land on the next turn.

## Algorithm (backend, unchanged)

`CliApplication` runs `MapParser` then `Simulator`.

1. **Parsing** (`parser_function/`): strict, with line-numbered errors
   (types, capacities, duplicates, unknown zones...).
2. **Distances** (`engine/distances.py`): one reverse Dijkstra from the end
   hub gives every zone its cost to the goal (normal/priority 1, restricted
   2, blocked excluded). Complexity O((V+E) log V), computed once.
3. **Turn by turn** (`engine/simulator.py`): landings of drones in flight
   are applied first. Then waiting drones, closest to the goal first
   (ties by id), each pick the reachable neighbor that is strictly closer,
   preferring priority zones then wider capacities, if the zone and the
   link still have room. Drones that cannot move wait.
4. **Validation**: `engine/checker.py` (`OutputChecker`) replays an output
   independently and checks every rule.

Limit: a drone only moves to a neighbor strictly closer to the goal, so
it follows shortest-path edges and never takes a longer parallel route,
even when the short one is saturated. It also never deadlocks, because
distances to the goal strictly decrease along every move.

Measured turns with the provided maps:

| Map | Drones | Turns | Subject target |
|-----|--------|-------|----------------|
| linear_path | 2 | 3 | <= 6 |
| simple_fork | 4 | 5 | <= 8 |
| basic_capacity | 4 | 4 | <= 6 |
| circular_loop | 6 | 15 | <= 15 |
| priority_puzzle | 5 | 7 | <= 12 |
| maze_nightmare | 8 | 13 | <= 30 |
| capacity_hell | 12 | 16 | <= 35 |
| ultimate_challenge | 15 | 26 | <= 45 |
| impossible_dream | 25 | 43 | record 45 |

`dead_end_trap` and `restricted_zone_check` contain a duplicate connection
(`start-r1` / `r1-start`) and are rejected by the parser, as the subject
requires. The menu lists them as INVALID with the parser error.

## Viewer

```
flyin/src/viewer/
├── app.py                      Ursina window, background, screen switching
├── catalog.py                  discovers maps/ and assets/drones/
├── layout.py                   map -> screen fitting (pure Python)
├── playback.py                 turn/speed/status state machine (pure)
├── session.py, shapes.py, theme.py, paths.py
├── adapters/simulation_adapter.py   backend output -> per-turn states
├── entities/ (zone, connection, drone, network)
├── screens/  (base, menu, simulation)
└── ui/       (controls, hud)
```

- **Adapter**: `SimulationAdapter` runs the existing parser and
  `Simulator`, replays the returned lines (the same lines the CLI prints)
  to know where each drone is after each turn, and also runs
  `OutputChecker` (shown as `OUTPUT: VALID` in the HUD). The viewer never
  plans or invents a movement.
- **Network**: zones and connections are drawn from the parsed map. The
  fit centers the map, keeps proportions, scales to the free area and
  rebuilds when the window is resized. Zone types have their own color
  (start green, end violet, normal blue, priority amber with a `+`,
  restricted grey with `x2`, blocked red with a cross); the zone `color=`
  metadata is shown as the zone rim; capacities > 1 appear as small
  badges; roads touching blocked zones are dimmed.
- **Drones**: sprites are placed at their real zone, or at the middle of
  the connection while flying to a restricted zone. Groups are fanned out;
  larger groups show `xN`. The end hub lights up once drones arrive.
- Everything is drawn in Ursina's 2D orthographic `camera.ui` space.
- Zone blocks are rounded squares with a dark border, a drop shadow and a
  gloss band; roads are round-ended. Every shape is a flat mesh generated
  in `geometry.py`.

### Animations

All animation code is pure Python (`animation.py`) and only changes how
the backend moves are *shown*; speed never changes the result.

- **Flight**: a drone eases out of its zone and into the next one
  (ease-in-out cubic) along the real connection, within 75% of the time a
  turn stays on screen, with a slight start stagger, a stretch while
  flying and a small bounce on landing. Retargeting mid-flight starts from
  the current position (no teleport).
- **Idle**: drones hover gently over a soft ground shadow.
- **Intro** (new map, RESTART, menu preview): roads grow from the center,
  zones pop in as a wave from the middle outward, then the drones appear.
  A window resize rebuilds the layout without replaying it.
- **Feedback**: a zone pulses when a drone lands in it; the end hub rim
  lights up once drones are delivered.

### Assets

`assets/background/background.png` (desert) and
`assets/drones/drone_{sphere,spider,rover,cube}.png` (transparent PNG,
trimmed, 256 px high). Any `drone_*.png` added to the folder is offered in
the menu; any `.txt` map under `maps/` is listed (a parent folder named
easy/medium/hard/challenger, or a `# Easy ...` header, gives its tag).

## Resources

- Ursina Engine documentation: https://www.ursinaengine.org/
- Dijkstra's algorithm articles.
- Python `typing`, PEP 257, flake8 and mypy documentation.

**AI usage**: the viewer (`flyin/src/viewer`), the tests, the Makefile and
this README were produced with Claude (Anthropic) under the author's
direction; the sprites and background were AI-generated images supplied by
the author. The backend was left untouched. Every generated part must be
reviewed and understood by the author before submission.
