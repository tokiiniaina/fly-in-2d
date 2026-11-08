"""Parse connection declarations."""

import re

from flyin.src.connection import Connection


class ConnectionParser:
    """Parse connection declarations."""

    def parse(self, line: str, line_number: int) -> Connection:
        """Parse a connection declaration and return its data."""
        endpoints, metadata = self._parse_endpoints(line, line_number)
        max_link_capacity = self._parse_metadata(metadata, line_number)
        return Connection(*endpoints, max_link_capacity)

    @staticmethod
    def _parse_endpoints(
        line: str, line_number: int
    ) -> tuple[tuple[str, str], str | None]:
        """Parse connection endpoints and return optional metadata."""
        match = re.fullmatch(
            r"connection:\s*([^\s\-]+)-([^\s\-]+)"
            r"(?:\s+(.*))?",
            line.strip(),
        )
        if match is None:
            raise ValueError(
                f"Line {line_number}: invalid connection declaration"
            )
        zone1, zone2, metadata = match.groups()
        if zone1 == zone2:
            raise ValueError(
                f"Line {line_number}: a connection must link two "
                "different zones"
            )
        return (zone1, zone2), metadata

    @staticmethod
    def _parse_metadata(
        metadata_block: str | None, line_number: int
    ) -> int:
        """Parse the optional connection capacity."""
        if metadata_block is None:
            return 1
        if not (
            metadata_block.startswith("[")
            and metadata_block.endswith("]")
        ):
            raise ValueError(
                f"Line {line_number}: invalid metadata block"
            )
        metadata_text = metadata_block[1:-1].strip()
        metadata_match = re.fullmatch(
            r"max_link_capacity\s*=\s*([^\s=\[\]]+)",
            metadata_text,
        )
        if metadata_match is None:
            raise ValueError(
                f"Line {line_number}: invalid connection metadata"
            )
        value = metadata_match.group(1)
        if not value.isascii() or not value.isdigit():
            raise ValueError(
                f"Line {line_number}: max_link_capacity must be "
                "a positive integer"
            )
        max_link_capacity = int(value)
        if max_link_capacity <= 0:
            raise ValueError(
                f"Line {line_number}: max_link_capacity must be "
                "positive"
            )
        return max_link_capacity
