"""Reference turn targets of the subject, and the end-of-run summary."""

import re

TARGETS: dict[str, int] = {
    "linear_path": 6,
    "simple_fork": 8,
    "basic_capacity": 6,
    "dead_end_trap": 12,
    "circular_loop": 15,
    "priority_puzzle": 12,
    "maze_nightmare": 30,
    "capacity_hell": 35,
    "ultimate_challenge": 45,
    "the_impossible_dream": 45,
}


def target_for(map_name: str) -> int | None:
    """Target number of turns of a map file name, None if not listed."""
    stem = re.sub(r"\.txt$", "", map_name.lower())
    stem = re.sub(r"^\d+_", "", stem)
    return TARGETS.get(stem)


def summary_lines(delivered: int, total: int, turns: int,
                  target: int | None, valid: bool) -> list[str]:
    """The texts of the end-of-run panel."""
    done = delivered == total
    lines = ["ALL DRONES DELIVERED" if done else
             f"INCOMPLETE: {delivered} / {total} DELIVERED"]
    turn_text = f"TURNS: {turns}"
    if target is not None:
        verdict = "OK" if turns <= target else "ABOVE TARGET"
        turn_text += f"     TARGET: {target}     {verdict}"
    lines.append(turn_text)
    lines.append("OUTPUT: VALID" if valid else "OUTPUT: INVALID")
    lines.append("R: REPLAY     ESC: MAP")
    return lines
