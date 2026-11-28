"""Generate a new SQLite database containing only synthetic bikeshare trips."""

import argparse
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from import_trips import CREATE_TRIPS_SQL


DEFAULT_OUTPUT = Path(__file__).resolve().with_name("demo.sqlite3")


def demo_trips():
    batches = (
        ("2025-01-14 06:00", "31633", "31600", 1),
        ("2025-01-14 08:00", "31600", "31601", 12),
        ("2025-01-14 08:20", "31601", "31600", 5),
        ("2025-01-14 09:00", "31600", "31601", 8),
        ("2025-01-14 11:00", "31600", "31633", 4),
        ("2025-01-14 17:00", "31633", "31601", 5),
        ("2025-01-14 18:00", "31601", "31600", 3),
        ("2025-01-13 23:48", "31601", "31600", 1),
        ("2025-01-14 23:48", "31600", "31601", 1),
        ("2025-01-15 00:00", "31601", "31600", 1),
    )
    ride_number = 0
    for start, origin, destination, count in batches:
        first = datetime.fromisoformat(start)
        for minute in range(count):
            started_at = first + timedelta(minutes=minute)
            ended_at = started_at + timedelta(minutes=12)
            ride_number += 1
            yield (
                f"synthetic-demo-{ride_number:03d}",
                started_at.isoformat(sep=" ", timespec="microseconds"),
                ended_at.isoformat(sep=" ", timespec="microseconds"),
                origin,
                destination,
                "classic_bike",
                "member",
            )


def generate_demo_db(output: Path) -> int:
    if output.suffix != ".sqlite3" or output.name.casefold() == "bikeshare.sqlite3":
        raise ValueError("Choose a new .sqlite3 path other than bikeshare.sqlite3.")
    if os.path.lexists(output):
        raise FileExistsError(f"Output already exists: {output}")

    # Stage on the same filesystem, then publish only if the name is still free.
    with TemporaryDirectory(dir=output.parent) as directory:
        staged = Path(directory) / "demo.sqlite3"
        with closing(sqlite3.connect(staged)) as db, db:
            db.execute(CREATE_TRIPS_SQL)
            db.executemany("INSERT INTO trips VALUES (?, ?, ?, ?, ?, ?, ?)", demo_trips())
            count = db.total_changes
        os.link(staged, output)
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="new .sqlite3 path (default: demo.sqlite3)")
    args = parser.parse_args()
    try:
        count = generate_demo_db(args.output)
    except (OSError, ValueError, sqlite3.Error) as exc:
        parser.exit(1, f"Unable to generate demo database: {exc}\n")
    print(f"Created {args.output} with {count} synthetic demo trips.")


if __name__ == "__main__":
    main()
