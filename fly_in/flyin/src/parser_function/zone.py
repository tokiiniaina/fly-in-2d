"""Parse zone declarations."""

import re

from flyin.src.zone import Zone


class ZoneParser:
    """Parse zone declarations."""

    def parse(self, line: str, line_number: int) -> tuple[str, Zone]:
        """Parse a zone declaration and return its kind and data."""
        prefix, content = self._split_prefix(line, line_number)
        name, x, y, metadata_text = self._parse_name_and_coordinates(
            content, line_number
        )
        metadata = self._parse_metadata(metadata_text, line_number)
        zone_type = metadata.get("zone", "normal")
        color = metadata.get("color", "none")
        if zone_type not in (
            "normal", "blocked", "restricted", "priority"
        ):
            raise ValueError(
                f"Line {line_number}: invalid zone type '{zone_type}'"
            )
        max_drones = self._parse_max_drones(
            prefix, metadata, line_number
        )
        zone = Zone(name, x, y, zone_type, color, max_drones)
        return prefix, zone

    @staticmethod
    def _split_prefix(line: str, line_number: int) -> tuple[str, str]:
        """Split and validate the declaration prefix."""
        if ":" not in line:
            raise ValueError(
                f"Line {line_number}: invalid zone declaration"
            )
        prefix, content = line.split(":", 1)
        prefix = prefix.strip()
        if prefix not in ("hub", "start_hub", "end_hub"):
            raise ValueError(
                f"Line {line_number}: unknown zone declaration '{prefix}'"
            )
        return prefix, content.strip()

    @staticmethod
    def _parse_name_and_coordinates(
        content: str, line_number: int
    ) -> tuple[str, int, int, str]:
        """Parse the name, coordinates and remaining metadata text."""
        parts = content.split()
        if len(parts) < 3:
            raise ValueError(
                f"Line {line_number}: expected a name and two coordinates"
            )
        name = parts[0]
        if "-" in name:
            raise ValueError(
                f"Line {line_number}: zone names cannot contain dashes"
            )
        if not (re.fullmatch(r"-?[0-9]+", parts[1])
                and re.fullmatch(r"-?[0-9]+", parts[2])):
            raise ValueError(
                f"Line {line_number}: coordinates must be integers"
            )
        x = int(parts[1])
        y = int(parts[2])
        return name, x, y, " ".join(parts[3:])

    @staticmethod
    def _parse_metadata(
        metadata_text: str, line_number: int
    ) -> dict[str, str]:
        """Parse optional zone metadata."""
        if not metadata_text:
            return {}
        if not (
            metadata_text.startswith("[")
            and metadata_text.endswith("]")
        ):
            raise ValueError(
                f"Line {line_number}: invalid metadata block"
            )
        text = metadata_text[1:-1].strip()
        if not text:
            raise ValueError(
                f"Line {line_number}: metadata block cannot be empty"
            )
        metadata: dict[str, str] = {}
        for item in text.split():
            if not re.fullmatch(r"[a-z_]+=[^\s=\[\]]+", item):
                raise ValueError(
                    f"Line {line_number}: invalid metadata item '{item}'"
                )
            key, value = item.split("=", 1)
            if key not in ("zone", "color", "max_drones"):
                raise ValueError(
                    f"Line {line_number}: unknown zone metadata '{key}'"
                )
            if key in metadata:
                raise ValueError(
                    f"Line {line_number}: duplicate metadata '{key}'"
                )
            metadata[key] = value
        return metadata

    @staticmethod
    def _parse_max_drones(
        prefix: str, metadata: dict[str, str], line_number: int
    ) -> int:
        """Parse the optional hub capacity."""
        if prefix != "hub" or "max_drones" not in metadata:
            return 1
        value = metadata["max_drones"]
        if not value.isascii() or not value.isdigit():
            raise ValueError(
                f"Line {line_number}: max_drones must "
                "be a positive integer"
            )
        max_drones = int(value)
        if max_drones <= 0:
            raise ValueError(
                f"Line {line_number}: max_drones must be positive"
            )
        return max_drones
