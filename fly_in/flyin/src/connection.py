
"""Define the Connection data model."""

from dataclasses import dataclass


@dataclass
class Connection:
    """Represent a connection between two zones."""

    zone1: str
    zone2: str
    max_link_capacity: int = 1
