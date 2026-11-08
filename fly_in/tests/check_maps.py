"""Run the current Fly-in output generator against test maps."""

from dataclasses import dataclass
from pathlib import Path

from flyin.src.engine import FlyInError
from flyin.src.engine.checker import OutputChecker
from flyin.src.engine.solver import Solver
from flyin.src.map_data import MapData
from flyin.src.parser_function import MapParser


@dataclass(frozen=True)
class MapCase:
    """Describe one map test case."""

    name: str
    path: Path


@dataclass
class MapResult:
    """Store the output and validation status for one map."""

    case: MapCase
    lines: list[str]
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        """Return whether the map was parsed, run and checked successfully."""
        return self.error is None


class MapRunner:
    """Parse, run and validate map cases."""

    def run_one(self, case: MapCase) -> MapResult:
        """Run one map and convert expected failures into a result."""
        lines: list[str] = []
        try:
            data = MapParser().parse(str(case.path))
            lines = self._run_current_engine(data)
            OutputChecker(data).check(lines)
        except (ValueError, FlyInError) as error:
            return MapResult(case=case, lines=lines, error=str(error))
        return MapResult(case=case, lines=lines)

    def _run_current_engine(self, data: MapData) -> list[str]:
        """Run the space-time solver."""
        return Solver().solve(data)


class Report:
    """Collect and display map results and the final summary."""

    def __init__(self) -> None:
        """Initialize an empty report."""
        self._results: list[MapResult] = []

    def add(self, result: MapResult) -> None:
        """Add a result to the report."""
        self._results.append(result)

    def display_result(self, result: MapResult) -> None:
        """Display one map result and all generated output lines."""
        status = "OK" if result.succeeded else result.error
        print(f"{result.case.name}: {len(result.lines)} tours - {status}")
        for line in result.lines:
            print(f"  {line}")

    def display_summary(self) -> int:
        """Display the summary and return the process exit code."""
        failed = sum(not result.succeeded for result in self._results)
        total = len(self._results)
        print(f"Récapitulatif: {total - failed}/{total} maps OK")
        return 1 if failed else 0


def main() -> int:
    """Run every text map in the tests/maps directory."""
    maps_directory = Path(__file__).with_name("maps")
    cases = [
        MapCase(path.name, path)
        for path in sorted(maps_directory.glob("*.txt"))
    ]
    runner = MapRunner()
    report = Report()
    for case in cases:
        result = runner.run_one(case)
        report.add(result)
        report.display_result(result)
    return report.display_summary()


if __name__ == "__main__":
    raise SystemExit(main())
