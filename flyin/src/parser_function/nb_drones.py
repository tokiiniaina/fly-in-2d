"""Parse the number of drones declaration."""

import re


def parse_nb_drones(line: str, line_number: int) -> int:
    """Parse a 'nb_drones: <positive_integer>' declaration."""

    parts = line.split(":", 1)

    if len(parts) != 2 or parts[0].strip() != "nb_drones":
        raise ValueError(
            f"Line {line_number}: expected 'nb_drones: <positive_integer>'"
        )
    value = parts[1].strip()

    if re.fullmatch(r"[0-9]+", value) is None:
        raise ValueError(
            f"Line {line_number}: number of drones must be an integer"
        )

    nb_drones = int(value)
    if nb_drones <= 0:
        raise ValueError(
            f"Line {line_number}: number of drones must be positive"
        )
    return nb_drones
