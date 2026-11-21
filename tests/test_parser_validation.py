"""Validation of numeric fields and whitespace in map declarations."""

import tempfile
import unittest
from pathlib import Path

from flyin.src.map_data import MapData
from flyin.src.parser_function import MapParser


class ParserValidationTests(unittest.TestCase):
    """Reject Python-only numeric syntax and accept spaced declarations."""

    def parse_text(self, text: str) -> MapData:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "map.txt"
            path.write_text(text, encoding="utf-8")
            return MapParser().parse(str(path))

    def test_drone_count_allows_spaces_before_colon(self) -> None:
        data = self.parse_text(
            "nb_drones : 2\n"
            "start_hub: s 0 0\n"
            "end_hub: e 1 0\n"
            "connection: s-e\n"
        )
        self.assertEqual(data.nb_drones, 2)

    def test_drone_count_rejects_underscores(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be an integer"):
            self.parse_text(
                "nb_drones: 1_0\n"
                "start_hub: s 0 0\n"
                "end_hub: e 1 0\n"
                "connection: s-e\n"
            )

    def test_coordinates_reject_underscores(self) -> None:
        with self.assertRaisesRegex(
                ValueError, "coordinates must be integers"):
            self.parse_text(
                "nb_drones: 1\n"
                "start_hub: s 1_0 0\n"
                "end_hub: e 1 0\n"
                "connection: s-e\n"
            )
