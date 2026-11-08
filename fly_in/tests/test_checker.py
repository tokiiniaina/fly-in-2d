"""Tests of the output checker."""

import pytest

from flyin.src.engine.checker import OutputChecker
from flyin.src.parser_function import MapParser


def test_checker_rejects_two_drones_in_restricted_zone() -> None:
    """Two drones landing together in a capacity-1 zone are refused."""
    data = MapParser().parse("tests/maps/restricted_capacity.txt")
    lines = ["D1-a D2-b", "D1-a-r D2-b-r", "D1-r D2-r", "D1-e D2-e"]
    with pytest.raises(ValueError, match="zone 'r' contains 2 drones"):
        OutputChecker(data).check(lines)
