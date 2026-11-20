import sqlite3
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from app import app


ACTIVITY_URL = "/stations/31600/activity"
START = "2025-01-14T09:00:00"
END = "2025-01-14T10:00:00"


@pytest.fixture
def database_path(tmp_path, monkeypatch):
    path = tmp_path / "trips.sqlite3"
    monkeypatch.setenv("BIKESHARE_DB", str(path))
    return path


@pytest.fixture
def client(database_path):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def seeded_client(client, database_path):
    # Match the importer schema and its space-separated microsecond timestamps.
    trips = [
        ("out-before", "08:59:59", "09:10:00", "31600", "31601"),
        ("out-at-start", "09:00:00", "09:15:00", "31600", "31601"),
        ("out-inside", "09:30:00", "09:45:00", "31600", "31601"),
        ("out-at-end", "10:00:00", "10:15:00", "31600", "31601"),
        ("in-before", "08:45:00", "08:59:59", "31601", "31600"),
        ("in-at-start", "08:50:00", "09:00:00", "31601", "31600"),
        ("in-at-end", "09:50:00", "10:00:00", "31601", "31600"),
    ]
    with closing(sqlite3.connect(database_path)) as db, db:
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
        db.executemany(
            """
            INSERT INTO trips (
                ride_id, started_at, ended_at, start_station_id, end_station_id
            ) VALUES (?, ?, ?, ?, ?)
            """,
            [
                (ride_id, f"2025-01-14 {start}.000000", f"2025-01-14 {end}.000000", origin, destination)
                for ride_id, start, end, origin, destination in trips
            ],
        )
    return client


def test_activity_counts_in_half_open_interval(seeded_client):
    response = seeded_client.get(ACTIVITY_URL, params={"start": START, "end": END})

    assert response.status_code == 200
    assert response.json() == {
        "station_id": "31600",
        "start": START,
        "end": END,
        "departures": 2,
        "arrivals": 1,
        "net_departures": 1,
    }


def test_activity_without_records_returns_zero_counts(seeded_client):
    response = seeded_client.get(
        "/stations/31699/activity", params={"start": START, "end": END}
    )

    assert response.status_code == 200
    assert response.json() == {
        "station_id": "31699",
        "start": START,
        "end": END,
        "departures": 0,
        "arrivals": 0,
        "net_departures": 0,
    }


@pytest.mark.parametrize(
    ("start", "end", "detail"),
    [
        (START, START, "start must be earlier than end."),
        ("2025-01-14", END, "Use ISO 8601 date and time"),
        (START, END + "+08:00", "Use dataset timestamps without a timezone offset."),
    ],
    ids=["equal-times", "date-without-time", "timezone-offset"],
)
def test_invalid_activity_interval_returns_422(client, start, end, detail):
    response = client.get(ACTIVITY_URL, params={"start": start, "end": end})

    assert response.status_code == 422
    assert detail in response.json()["detail"]


def test_unavailable_database_returns_503(client, database_path):
    assert not database_path.exists()

    response = client.get(ACTIVITY_URL, params={"start": START, "end": END})

    assert response.status_code == 503
    assert "Trip database is unavailable." in response.json()["detail"]
    assert not database_path.exists()
