"""Command line of Fly-in."""

import argparse
import sys
from pathlib import Path

from flyin.src.engine import FlyInError
from flyin.src.engine.solver import Solver
from flyin.src.map_data import MapData
from flyin.src.parser_function import MapParser


class Application:
    """Parse the map, simulate, print the turns."""

    @staticmethod
    def _parser() -> argparse.ArgumentParser:
        """Create the argument parser."""
        parser = argparse.ArgumentParser(prog="fly_in.py")
        parser.add_argument("map", nargs="?", default=None,
                            help="path of the map file "
                                 "(omit it to open the graphical menu)")
        parser.add_argument("--gui", action="store_true",
                            help="open the 2D graphical viewer")
        parser.add_argument("--3d", dest="three_d", action="store_true",
                            help="open the isometric 3D viewer "
                                 "(browse all maps if none is given)")
        return parser

    @staticmethod
    def _show_3d(
        data: MapData,
        lines: list[str],
        name: str,
        map_path: str,
    ) -> int:
        """Open the 3D viewer and return an exit code."""
        try:
            from flyin.src.viewer3d.launcher import show3d
            show3d(data, lines, name, map_path)
        except ImportError as error:
            print(f"Error: cannot start the 3D viewer: {error}",
                  file=sys.stderr)
            return 1
        except ValueError as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1
        return 0

    @staticmethod
    def _show_3d_browser() -> int:
        """Open the 3D viewer on the project maps and return a code."""
        try:
            from flyin.src.viewer3d.launcher import Viewer3D
            return Viewer3D().run()
        except ImportError as error:
            print(f"Error: cannot start the 3D viewer: {error}",
                  file=sys.stderr)
            return 1
        except (OSError, ValueError) as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1

    @staticmethod
    def _show_gui(map_path: str | None) -> int:
        """Open the 2D viewer and return the exit code."""
        try:
            from flyin.src.viewer.app import ViewerApp
            return ViewerApp(map_path).run()
        except ImportError as error:
            print(f"Error: cannot start the viewer: {error} "
                  "(run 'make install')", file=sys.stderr)
            return 1
        except (OSError, ValueError) as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1

    def run(self, argv: list[str] | None = None) -> int:
        """Run the program and return the exit code."""
        parser = self._parser()
        args = parser.parse_args(argv)
        if args.map is None:
            if args.three_d:
                return self._show_3d_browser()
            return self._show_gui(None)
        try:
            data = MapParser().parse(args.map)
            lines = Solver().solve(data)
        except OSError as error:
            print(f"Error: cannot read '{error.filename}'",
                  file=sys.stderr)
            return 1
        except (ValueError, FlyInError) as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1
        print("\n".join(lines))
        print(f"{len(lines)} turns", file=sys.stderr)
        if args.gui:
            return self._show_gui(args.map)
        if args.three_d:
            return self._show_3d(
                data, lines, Path(args.map).name,
                str(Path(args.map).resolve()),
            )

        return 0
