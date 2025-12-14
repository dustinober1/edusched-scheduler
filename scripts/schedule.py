#!/usr/bin/env python3
"""EduSched Schedule Generation CLI

Command-line tool for generating academic schedules using EduSched.
Supports multiple solver backends and output formats.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from edusched.core_api import solve
from edusched.domain.problem import Problem
from edusched.utils.data_import import DataImporter
from edusched.utils.export import export_schedule


def setup_logging(verbose: bool = False) -> None:
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def load_problem(data_dir: Path) -> Problem:
    """Load scheduling problem from data directory.

    Args:
        data_dir: Directory containing CSV/JSON/Excel files

    Returns:
        Problem instance with loaded data
    """
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    importer = DataImporter()

    # Try to import data files
    data_files = {
        "teachers": ["teachers.csv", "teachers.json", "teachers.xlsx"],
        "courses": ["courses.csv", "courses.json", "courses.xlsx"],
        "resources": ["resources.csv", "resources.json", "resources.xlsx"],
        "buildings": ["buildings.csv", "buildings.json", "buildings.xlsx"],
        "departments": ["departments.csv", "departments.json", "departments.xlsx"],
        "holidays": ["holidays.csv", "holidays.json", "holidays.xlsx"],
        "time_blockers": ["time_blockers.csv", "time_blockers.json", "time_blockers.xlsx"],
    }

    problem = Problem(
        requests=[],
        resources=[],
        calendars=[],
        constraints=[],
    )

    for data_type, filenames in data_files.items():
        for filename in filenames:
            file_path = data_dir / filename
            if file_path.exists():
                logging.info(f"Loading {data_type} from {filename}")
                try:
                    if data_type == "teachers":
                        problem.teachers.extend(importer.import_teachers(file_path))
                    elif data_type == "courses":
                        problem.requests.extend(importer.import_courses(file_path))
                    elif data_type == "resources":
                        problem.resources.extend(importer.import_resources(file_path))
                    elif data_type == "buildings":
                        problem.buildings.extend(importer.import_buildings(file_path))
                    elif data_type == "departments":
                        problem.departments.extend(importer.import_departments(file_path))
                    elif data_type == "holidays":
                        problem.calendars.extend(importer.import_holidays(file_path))
                    elif data_type == "time_blockers":
                        problem.time_blockers.extend(importer.import_time_blockers(file_path))
                    break  # Use first found file for each type
                except Exception as e:
                    logging.warning(f"Failed to import {data_type} from {filename}: {e}")

    return problem


def save_result(result, output_path: Path, format: str = "auto") -> None:
    """Save scheduling result to file.

    Args:
        result: Result object from solver
        output_path: Output file path
        format: Output format ("auto", "json", "csv", "ical", "excel")
    """
    try:
        export_schedule(result, output_path, format)
        logging.info(f"Successfully exported schedule to {output_path}")
    except Exception as e:
        logging.error(f"Failed to export schedule: {e}")
        raise


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="schedule",
        description="Generate academic schedules using EduSched",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate schedule with default settings
  python scripts/schedule.py --data-dir ./data --output schedule.xlsx

  # Use specific solver and seed
  python scripts/schedule.py --data-dir ./data --solver heuristic --seed 42

  # Export to JSON with verbose logging
  python scripts/schedule.py --data-dir ./data --output schedule.json --verbose
        """,
    )

    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("./data"),
        help="Directory containing input data files (default: ./data)",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        required=True,
        help="Output file path (format inferred from extension)",
    )

    parser.add_argument(
        "--solver",
        choices=["auto", "heuristic", "ortools"],
        default="auto",
        help="Solver backend to use (default: auto)",
    )

    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducible results",
    )

    parser.add_argument(
        "--semester",
        type=str,
        help="Semester identifier for logging/reporting",
    )

    parser.add_argument(
        "--format",
        choices=["auto", "json", "csv", "ical", "excel"],
        default="auto",
        help="Output format (default: auto - inferred from file extension)",
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="EduSched 0.1.0b1",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    # Determine output format
    if args.format == "auto":
        suffix = args.output.suffix.lower()
        if suffix == ".json":
            output_format = "json"
        elif suffix == ".csv":
            output_format = "csv"
        elif suffix in [".ical", ".ics"]:
            output_format = "ical"
        elif suffix in [".xlsx", ".xls"]:
            output_format = "excel"
        else:
            output_format = "json"  # Default to JSON
    else:
        output_format = args.format

    # Log configuration
    logging.info(f"EduSched Schedule Generator")
    if args.semester:
        logging.info(f"Semester: {args.semester}")
    logging.info(f"Data directory: {args.data_dir}")
    logging.info(f"Output file: {args.output}")
    logging.info(f"Solver backend: {args.solver}")
    if args.seed:
        logging.info(f"Random seed: {args.seed}")

    try:
        # Load problem data
        logging.info("Loading problem data...")
        problem = load_problem(args.data_dir)

        if not problem.requests:
            logging.error("No course requests found in data directory")
            sys.exit(1)

        logging.info(f"Loaded {len(problem.requests)} course requests")
        logging.info(f"Loaded {len(problem.resources)} resources")
        logging.info(f"Loaded {len(problem.teachers)} teachers")

        # Solve problem
        logging.info("Scheduling...")
        result = solve(problem, backend=args.solver, seed=args.seed)

        # Report results
        if result.assignments:
            logging.info(f"Success! Scheduled {len(result.assignments)} classes")
            logging.info(f"Solver time: {result.solver_time_ms:.0f}ms")
            logging.info(f"Iterations: {result.iterations}")

            # Save results
            logging.info(f"Saving results to {args.output}...")
            save_result(result, args.output, output_format)
            logging.info("Schedule generated successfully!")

        else:
            logging.warning("No feasible schedule found")
            sys.exit(1)

    except FileNotFoundError as e:
        logging.error(f"File not found: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error generating schedule: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()