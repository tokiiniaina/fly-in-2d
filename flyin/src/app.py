"""Command line of Fly-in."""

import argparse
import sys

from flyin.src.engine.checker import OutputChecker
from flyin.src.engine.simulator import Simulator
from flyin.src.parser_function import MapParser


class CliApplication:
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
        return parser

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
            return self._show_gui(None)
        try:
            data = MapParser().parse(args.map)
            lines = Simulator(data).run()
            OutputChecker(data).check(lines)
        except OSError as error:
            print(f"Error: cannot read '{error.filename}'",
                  file=sys.stderr)
            return 1
        except ValueError as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1
        print("\n".join(lines))
        print(f"{len(lines)} turns", file=sys.stderr)
        if args.gui:
            return self._show_gui(args.map)
        return 0
