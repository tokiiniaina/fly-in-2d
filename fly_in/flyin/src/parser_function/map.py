"""Parse complete map files."""

from flyin.src.map_data import MapData
from flyin.src.parser_function.connection import ConnectionParser
from flyin.src.parser_function.lines import LineReader
from flyin.src.parser_function.nb_drones import NbDronesParser
from flyin.src.parser_function.zone import ZoneParser


class MapParser:
    """Parse a map file into a MapData object."""

    def __init__(
        self,
        line_reader: LineReader | None = None,
        nb_drones_parser: NbDronesParser | None = None,
        zone_parser: ZoneParser | None = None,
        connection_parser: ConnectionParser | None = None,
    ) -> None:
        """Store the component parsers used by this parser."""
        self._line_reader = line_reader or LineReader()
        self._nb_drones_parser = nb_drones_parser or NbDronesParser()
        self._zone_parser = zone_parser or ZoneParser()
        self._connection_parser = (
            connection_parser or ConnectionParser()
        )
        self._nb_drones_found = False
        self._seen_connections: set[tuple[str, str]] = set()

    def parse(self, file_path: str) -> MapData:
        """Parse the drone count, zones and connections in a map file."""
        self._nb_drones_found = False
        self._seen_connections = set()
        lines = self._line_reader.read(file_path)
        self._check_first_line(lines)
        map_data = MapData()
        for line_number, line in lines:
            if line.startswith("nb_drones"):
                self._handle_nb_drones(map_data, line, line_number)
            elif line.startswith(("hub:", "start_hub:", "end_hub:")):
                self._handle_zone(map_data, line, line_number)
            elif line.startswith("connection:"):
                self._handle_connection(map_data, line, line_number)
            else:
                raise ValueError(
                    f"Line {line_number}: unknown declaration '{line}'"
                )
        self._check_required_declarations(map_data)
        return map_data

    @staticmethod
    def _check_first_line(lines: list[tuple[int, str]]) -> None:
        """Ensure the first declaration is ``nb_drones``."""
        if not lines:
            raise ValueError("Empty map file")
        first_line_number, first_line = lines[0]
        if not first_line.startswith("nb_drones"):
            if not any(line.startswith("nb_drones") for _, line in lines):
                raise ValueError("Missing 'nb_drones' declaration")
            raise ValueError(
                f"Line {first_line_number}: "
                "'nb_drones' must be the first declaration"
            )

    def _handle_nb_drones(
        self, map_data: MapData, line: str, line_number: int
    ) -> None:
        """Parse and store the drone count."""
        if self._nb_drones_found:
            raise ValueError(
                f"Line {line_number}: duplicate nb_drones declaration"
            )
        map_data.nb_drones = self._nb_drones_parser.parse(
            line, line_number
        )
        self._nb_drones_found = True

    def _handle_zone(
        self, map_data: MapData, line: str, line_number: int
    ) -> None:
        """Parse and store one zone declaration."""
        kind, zone = self._zone_parser.parse(line, line_number)
        if zone.name in map_data.zones:
            raise ValueError(
                f"Line {line_number}: duplicate zone name '{zone.name}'"
            )
        map_data.zones[zone.name] = zone
        if kind == "start_hub":
            if map_data.start_hub is not None:
                raise ValueError(
                    f"Line {line_number}: "
                    "duplicate start_hub declaration"
                )
            map_data.start_hub = zone.name
        elif kind == "end_hub":
            if map_data.end_hub is not None:
                raise ValueError(
                    f"Line {line_number}: duplicate end_hub declaration"
                )
            map_data.end_hub = zone.name

    def _handle_connection(
        self, map_data: MapData, line: str, line_number: int
    ) -> None:
        """Parse and store one connection declaration."""
        connection = self._connection_parser.parse(line, line_number)
        if connection.zone1 not in map_data.zones:
            raise ValueError(
                f"Line {line_number}: unknown zone "
                f"'{connection.zone1}'"
            )
        if connection.zone2 not in map_data.zones:
            raise ValueError(
                f"Line {line_number}: unknown zone "
                f"'{connection.zone2}'"
            )
        first, second = sorted((connection.zone1, connection.zone2))
        connection_key = (first, second)
        if connection_key in self._seen_connections:
            raise ValueError(
                f"Line {line_number}: duplicate connection "
                f"'{connection.zone1}-{connection.zone2}'"
            )
        self._seen_connections.add(connection_key)
        map_data.connections.append(connection)

    def _check_required_declarations(self, map_data: MapData) -> None:
        """Ensure all required map declarations were found."""
        if not self._nb_drones_found:
            raise ValueError("Missing 'nb_drones' declaration")
        if map_data.start_hub is None:
            raise ValueError("Missing 'start_hub' declaration")
        if map_data.end_hub is None:
            raise ValueError("Missing 'end_hub' declaration")
