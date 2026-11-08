"""Define the Zone data model."""

from dataclasses import dataclass


ENTRY_COST: dict[str, int] = {
    "normal": 1,
    "priority": 1,
    "restricted": 2,
}


@dataclass
class Zone:
    """Represent a zone of the drone network."""

    name:        str
    x:           int
    y:           int
    zone_type:   str = "normal"
    color:       str = "none"
    max_drones:  int = 1
