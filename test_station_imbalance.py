import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from station_imbalance import ASCII_WHITESPACE, IMBALANCE_SQL


FIRST = "2025-01-14 00:00:00.000000"
LAST = "2025-01-15 00:00:00.000000"
BEFORE = "2025-01-13 23:59:59.999999"
INSIDE = "2025-01-14 12:00:00.000000"


@pytest.fixture
def database():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "synthetic.sqlite3"
        with closing(sqlite3.connect(path)) as db:
            db.execute("""
                CREATE TABLE trips (
                    ride_id TEXT PRIMARY KEY NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT NOT NULL,
                    start_station_id TEXT,
                    end_station_id TEXT,
                    rideable_type TEXT,
                    member_casual TEXT
                )
            """)
            yield db


def ranking(db, trips, min_activity=0):
    db.executemany(
        """
        INSERT INTO trips (ride_id, started_at, ended_at, start_station_id, end_station_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        ((str(index), *trip) for index, trip in enumerate(trips)),
    )
    return db.execute(
        IMBALANCE_SQL,
        {"first": FIRST, "last": LAST, "min_activity": min_activity, "whitespace": ASCII_WHITESPACE},
    ).fetchall()


def test_opening_midnight_is_included(database):
    rows = ranking(database, [
        (FIRST, INSIDE, "starts-at-opening", None),
        (BEFORE, FIRST, "previous-day", "ends-at-opening"),
    ])

    assert rows == [
        ("ends-at-opening", 0, 1, -1, 1, 100.0),
        ("starts-at-opening", 1, 0, 1, 1, 100.0),
    ]


def test_closing_midnight_is_excluded(database):
    rows = ranking(database, [
        (INSIDE, LAST, "before-closing", "ends-at-closing"),
        (LAST, "2025-01-15 00:01:00.000000", "starts-at-closing", "next-day"),
    ])

    assert rows == [("before-closing", 1, 0, 1, 1, 100.0)]


@pytest.mark.parametrize(
    ("departures", "arrivals", "expected"),
    [
        (3, 1, ("station", 3, 1, 2, 4, 50.0)),
        (1, 3, ("station", 1, 3, -2, 4, 50.0)),
        (2, 2, ("station", 2, 2, 0, 4, 0.0)),
    ],
    ids=["positive-net", "negative-net", "balanced"],
)
def test_imbalance_metrics(database, departures, arrivals, expected):
    trips = [(INSIDE, INSIDE, "station", None)] * departures
    trips += [(INSIDE, INSIDE, None, "station")] * arrivals

    assert ranking(database, trips) == [expected]


@pytest.mark.parametrize("missing", [None, "", "   ", "\t\r\n"], ids=["null", "empty", "spaces", "tab-and-newlines"])
def test_missing_station_id_is_excluded_on_each_end(database, missing):
    rows = ranking(database, [
        (INSIDE, INSIDE, missing, "valid-arrival"),
        (INSIDE, INSIDE, "valid-departure", missing),
    ])

    assert rows == [
        ("valid-arrival", 0, 1, -1, 1, 100.0),
        ("valid-departure", 1, 0, 1, 1, 100.0),
    ]


def test_station_without_daily_activity_does_not_form_a_ranking_row(database):
    assert ranking(database, [(BEFORE, BEFORE, "inactive", "inactive")]) == []


def test_min_activity_includes_20_and_excludes_19(database):
    trips = [(INSIDE, INSIDE, "at-20", "at-19")] * 12
    trips += [(INSIDE, INSIDE, "at-19", "at-20")] * 7
    trips += [(INSIDE, INSIDE, None, "at-20")]

    assert ranking(database, trips, min_activity=0) == [
        ("at-19", 7, 12, -5, 19, 500.0 / 19),
        ("at-20", 12, 8, 4, 20, 20.0),
    ]
    assert database.execute(
        IMBALANCE_SQL,
        {"first": FIRST, "last": LAST, "min_activity": 20, "whitespace": ASCII_WHITESPACE},
    ).fetchall() == [("at-20", 12, 8, 4, 20, 20.0)]
