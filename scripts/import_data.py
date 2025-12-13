#!/usr/bin/env python3
"""Command-line tool for importing scheduling data."""

import argparse
import sys
from pathlib import Path
from typing import List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from edusched.utils.data_import import DataImporter, DataImportError, create_sample_csv_files


def import_data(file_path: str, data_type: str, validate_only: bool = False):
    """Import data from file."""
    try:
        importer = DataImporter()
        objects = importer.import_file(file_path, data_type)

        if validate_only:
            print(f"✓ Validation successful for {len(objects)} {data_type}")
            return True

        print(f"✓ Successfully imported {len(objects)} {data_type}:")
        for obj in objects[:10]:  # Show first 10
            if hasattr(obj, 'id'):
                print(f"  - {obj.id}: {getattr(obj, 'name', obj.__class__.__name__)}")
            else:
                print(f"  - {obj}")

        if len(objects) > 10:
            print(f"  ... and {len(objects) - 10} more")

        return True

    except DataImportError as e:
        print(f"✗ Import failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def create_templates(output_dir: str = "."):
    """Create sample CSV templates."""
    try:
        create_sample_csv_files(Path(output_dir))
        print(f"✓ Sample CSV templates created in {output_dir}")
        return True
    except Exception as e:
        print(f"✗ Failed to create templates: {e}")
        return False


def validate_files(file_paths: List[str]):
    """Validate multiple import files."""
    importer = DataImporter()
    all_valid = True

    for file_path in file_paths:
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"✗ File not found: {file_path}")
            all_valid = False
            continue

        # Try to detect data type from filename
        filename = file_path.stem.lower()
        if "building" in filename:
            data_type = "buildings"
        elif "resource" in filename or "classroom" in filename:
            data_type = "resources"
        elif "teacher" in filename or "instructor" in filename:
            data_type = "teachers"
        elif "department" in filename or "dept" in filename:
            data_type = "departments"
        elif "course" in filename or "session" in filename:
            data_type = "courses"
        elif "calendar" in filename:
            data_type = "calendars"
        else:
            print(f"? Cannot auto-detect data type for {file_path.name}")
            continue

        print(f"Validating {file_path.name} as {data_type}...")
        if not import_data(str(file_path), data_type, validate_only=True):
            all_valid = False

    if all_valid:
        print("\n✓ All files validated successfully")
    return all_valid


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Import scheduling data from CSV, JSON, or Excel files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import buildings from CSV
  python import_data.py import buildings.csv buildings

  # Validate file without importing
  python import_data.py validate teachers.csv teachers

  # Create sample templates
  python import_data.py create-templates ./templates

  # Validate multiple files
  python import_data.py batch-validate *.csv
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Import command
    import_parser = subparsers.add_parser("import", help="Import data from file")
    import_parser.add_argument("file_path", help="Path to import file")
    import_parser.add_argument("data_type",
        choices=["buildings", "resources", "teachers", "departments", "courses", "calendars"],
        help="Type of data to import")
    import_parser.add_argument("--validate-only", action="store_true",
        help="Only validate data without importing")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate data in file")
    validate_parser.add_argument("file_path", help="Path to file to validate")
    validate_parser.add_argument("data_type",
        choices=["buildings", "resources", "teachers", "departments", "courses", "calendars"],
        help="Type of data to validate")

    # Create templates command
    templates_parser = subparsers.add_parser("create-templates", help="Create sample CSV templates")
    templates_parser.add_argument("output_dir", nargs="?", default=".",
        help="Output directory for templates (default: current directory)")

    # Batch validate command
    batch_parser = subparsers.add_parser("batch-validate", help="Validate multiple files")
    batch_parser.add_argument("file_paths", nargs="+", help="Paths to files to validate")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    success = True

    if args.command == "import":
        success = import_data(args.file_path, args.data_type, args.validate_only)

    elif args.command == "validate":
        success = import_data(args.file_path, args.data_type, validate_only=True)

    elif args.command == "create-templates":
        success = create_templates(args.output_dir)

    elif args.command == "batch-validate":
        success = validate_files(args.file_paths)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())