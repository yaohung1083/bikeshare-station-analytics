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


HOURLY_URL = "/stations/31600/hourly-activity"
DAY = "2025-01-14"


def test_hourly_activity_groups_events_and_fills_all_hours(seeded_client, database_path):
    with closing(sqlite3.connect(database_path)) as db, db:
        db.executemany(
            """
            INSERT INTO trips (ride_id, started_at, ended_at, start_station_id, end_station_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("prev-day", "2025-01-13 23:59:59.999999", "2025-01-14 00:00:00.000000", "31600", "31600"),
                ("last-microsecond", "2025-01-14 23:59:59.999999", "2025-01-15 00:00:00.000000", "31600", "31600"),
                ("next-day", "2025-01-15 00:00:00.000000", "2025-01-15 00:05:00.000000", "31600", "31600"),
            ],
        )

    response = seeded_client.get(HOURLY_URL, params={"date": DAY})

    assert response.status_code == 200
    expected = {0: (0, 1), 8: (1, 1), 9: (2, 1), 10: (1, 1), 23: (1, 0)}
    assert response.json() == {
        "station_id": "31600",
        "date": DAY,
        "hours": [
            {"hour": f"{hour:02d}:00", "departures": expected.get(hour, (0, 0))[0],
             "arrivals": expected.get(hour, (0, 0))[1]}
            for hour in range(24)
        ],
    }


@pytest.mark.parametrize(
    ("station_id", "day"), [("31699", DAY), ("31600", "2025-01-16"), ("31600", "9999-12-31")]
)
def test_hourly_activity_without_records_returns_24_zeros(seeded_client, station_id, day):
    response = seeded_client.get(f"/stations/{station_id}/hourly-activity", params={"date": day})

    assert response.status_code == 200
    assert response.json() == {
        "station_id": station_id,
        "date": day,
        "hours": [
            {"hour": f"{hour:02d}:00", "departures": 0, "arrivals": 0}
            for hour in range(24)
        ],
    }


@pytest.mark.parametrize("day", ["2025-02-29", "20250114", "2025-1-14", DAY + "T00:00:00", DAY + "Z"])
def test_hourly_activity_rejects_invalid_date(client, day):
    assert client.get(HOURLY_URL, params={"date": day}).status_code == 422


def test_hourly_activity_requires_date(client):
    assert client.get(HOURLY_URL).status_code == 422


def test_hourly_activity_returns_503_for_unavailable_database(client, database_path):
    response = client.get(HOURLY_URL, params={"date": DAY})

    assert response.status_code == 503
    assert "Trip database is unavailable." in response.json()["detail"]
    assert not database_path.exists()


IMBALANCE_URL = "/stations/imbalance"


def test_station_imbalance_default_threshold_and_date_boundaries(seeded_client, database_path):
    with closing(sqlite3.connect(database_path)) as db, db:
        db.executemany(
            """
            INSERT INTO trips (ride_id, started_at, ended_at, start_station_id, end_station_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (f"threshold-{i}", f"{DAY} 00:00:00.000000", f"{DAY} 12:00:00.000000",
                 "at-20", "at-19" if i < 19 else None)
                for i in range(20)
            ] + [
                ("opening-return", "2025-01-13 23:59:59.999999", f"{DAY} 00:00:00.000000", "prior", "return"),
                ("closing-return", f"{DAY} 23:59:59.999999", "2025-01-15 00:00:00.000000", None, "at-20"),
                ("after", "2025-01-15 00:00:00.000000", "2025-01-15 00:01:00.000000", "at-20", None),
                ("missing-space", f"{DAY} 12:00:00.000000", f"{DAY} 12:01:00.000000", " \t\r\n\v\f", ""),
            ],
        )

    response = seeded_client.get(IMBALANCE_URL, params={"date": DAY})
    assert response.status_code == 200
    assert response.json() == {
        "date": DAY,
        "min_activity": 20,
        "total_stations": 1,
        "stations": [{
            "station_id": "at-20", "departures": 20, "arrivals": 0,
            "net_departures": 20, "total_activity": 20, "imbalance_rate": 100.0,
        }],
    }

    response = seeded_client.get(IMBALANCE_URL, params={"date": DAY, "min_activity": 1})
    assert response.status_code == 200
    stations = {row["station_id"]: row for row in response.json()["stations"]}
    assert set(stations) == {"at-20", "at-19", "return", "31600", "31601"}
    assert stations["at-19"]["total_activity"] == 19
    assert stations["return"]["arrivals"] == 1
    assert stations["at-20"]["arrivals"] == 0


def test_station_imbalance_sorts_by_raw_rate_absolute_net_and_station_id(seeded_client, database_path):
    counts = [
        ("z-higher-rate", 100, 99),
        ("a-lower-rate", 101, 100),
        ("only-out", 1, 0),
        ("only-in", 0, 2),
        ("a-balanced", 1, 1),
        ("z-balanced", 2, 2),
    ]
    trips = [
        (f"{station}-out-{i}", station, None)
        for station, departures, _ in counts for i in range(departures)
    ] + [
        (f"{station}-in-{i}", None, station)
        for station, _, arrivals in counts for i in range(arrivals)
    ]
    with closing(sqlite3.connect(database_path)) as db, db:
        db.executemany(
            """
            INSERT INTO trips (ride_id, start_station_id, end_station_id, started_at, ended_at)
            VALUES (?, ?, ?, '2025-01-16 12:00:00.000000', '2025-01-16 12:01:00.000000')
            """,
            trips,
        )

    response = seeded_client.get(IMBALANCE_URL, params={"date": "2025-01-16", "min_activity": 1})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_stations"] == 6
    assert [(row["station_id"], row["net_departures"], row["imbalance_rate"]) for row in payload["stations"]] == [
        ("only-in", -2, 100.0),
        ("only-out", 1, 100.0),
        ("z-higher-rate", 1, 0.50),
        ("a-lower-rate", 1, 0.50),
        ("a-balanced", 0, 0.0),
        ("z-balanced", 0, 0.0),
    ]


@pytest.mark.parametrize(("day", "threshold"), [
    ("2025-01-16", 20), ("9999-12-31", 20), (DAY, 2**63),
])
def test_station_imbalance_empty_ranking(seeded_client, day, threshold):
    response = seeded_client.get(IMBALANCE_URL, params={"date": day, "min_activity": threshold})

    assert response.status_code == 200
    assert response.json() == {
        "date": day, "min_activity": threshold, "total_stations": 0, "stations": [],
    }


@pytest.mark.parametrize("params", [
    {}, {"date": "2025-02-29"}, {"date": "2025-1-14"}, {"date": DAY + "T00:00:00"},
    {"date": DAY, "min_activity": "0"}, {"date": DAY, "min_activity": "-1"},
    {"date": DAY, "min_activity": "1.5"}, {"date": DAY, "min_activity": "20.0"},
    {"date": DAY, "min_activity": "invalid"},
])
def test_station_imbalance_rejects_invalid_query(client, params):
    assert client.get(IMBALANCE_URL, params=params).status_code == 422


def test_station_imbalance_database_unavailable(client, database_path):
    response = client.get(IMBALANCE_URL, params={"date": DAY})

    assert response.status_code == 503
    assert "Trip database is unavailable." in response.json()["detail"]
    assert not database_path.exists()


def test_imbalance_remains_a_valid_station_id_for_existing_routes(seeded_client):
    activity = seeded_client.get(
        f"{IMBALANCE_URL}/activity", params={"start": START, "end": END}
    )
    hourly = seeded_client.get(f"{IMBALANCE_URL}/hourly-activity", params={"date": DAY})

    assert activity.status_code == hourly.status_code == 200
    assert activity.json()["station_id"] == hourly.json()["station_id"] == "imbalance"
    assert activity.json()["net_departures"] == 0
    assert len(hourly.json()["hours"]) == 24
    assert all(row["departures"] == row["arrivals"] == 0 for row in hourly.json()["hours"])
