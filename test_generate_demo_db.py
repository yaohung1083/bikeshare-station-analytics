import sqlite3
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from app import app
from generate_demo_db import generate_demo_db


DAY = "2025-01-14"
FIRST = f"{DAY} 00:00:00.000000"
LAST = "2025-01-15 00:00:00.000000"
EXPECTED = {"31600": (25, 10), "31601": (8, 25), "31633": (6, 4)}


@pytest.fixture
def demo_db(tmp_path):
    path = tmp_path / "demo.sqlite3"
    assert generate_demo_db(path) == 41
    return path


def daily_counts(db, station):
    return db.execute("""
        SELECT
            (SELECT COUNT(*) FROM trips WHERE start_station_id = :station
             AND started_at >= :first AND started_at < :last),
            (SELECT COUNT(*) FROM trips WHERE end_station_id = :station
             AND ended_at >= :first AND ended_at < :last)
    """, {"station": station, "first": FIRST, "last": LAST}).fetchone()


def test_demo_schema_and_reproducibility(demo_db, tmp_path):
    other = tmp_path / "second-demo.sqlite3"
    assert generate_demo_db(other) == 41
    with closing(sqlite3.connect(demo_db)) as db, closing(sqlite3.connect(other)) as repeated:
        assert [(row[1], row[2], row[3], row[5]) for row in db.execute("PRAGMA table_info(trips)")] == [
            ("ride_id", "TEXT", 1, 1),
            ("started_at", "TEXT", 1, 0),
            ("ended_at", "TEXT", 1, 0),
            ("start_station_id", "TEXT", 0, 0),
            ("end_station_id", "TEXT", 0, 0),
            ("rideable_type", "TEXT", 0, 0),
            ("member_casual", "TEXT", 0, 0),
        ]
        rows = db.execute("SELECT * FROM trips ORDER BY ride_id").fetchall()
        assert len(rows) == 41
        assert all(row[0].startswith("synthetic-demo-") for row in rows)
        assert rows == repeated.execute("SELECT * FROM trips ORDER BY ride_id").fetchall()
        assert {station: daily_counts(db, station) for station in EXPECTED} == EXPECTED


def test_demo_refuses_to_replace_files_or_links(demo_db, tmp_path):
    existing = tmp_path / "existing.sqlite3"
    existing.write_bytes(b"unrelated file")
    dangling = tmp_path / "dangling.sqlite3"
    dangling.symlink_to(tmp_path / "missing")
    for output in (demo_db, existing, dangling):
        with pytest.raises(FileExistsError):
            generate_demo_db(output)
    assert existing.read_bytes() == b"unrelated file"
    assert dangling.is_symlink()
    assert not (tmp_path / "missing").exists()
    with closing(sqlite3.connect(demo_db)) as db:
        assert db.execute("SELECT COUNT(*) FROM trips").fetchone() == (41,)


@pytest.mark.parametrize("name", ["bikeshare.sqlite3", "BIKESHARE.sqlite3", "other.txt"])
def test_demo_rejects_reserved_or_non_sqlite_paths(tmp_path, name):
    path = tmp_path / name
    with pytest.raises(ValueError):
        generate_demo_db(path)
    assert not path.exists()


def test_demo_apis_match_sql_and_expected_results(demo_db, monkeypatch):
    monkeypatch.setenv("BIKESHARE_DB", str(demo_db))
    with TestClient(app) as client, closing(sqlite3.connect(demo_db)) as db:
        for station, expected in EXPECTED.items():
            response = client.get(f"/stations/{station}/activity", params={
                "start": f"{DAY}T00:00:00", "end": "2025-01-15T00:00:00",
            })
            assert response.status_code == 200
            data = response.json()
            assert data["station_id"] == station
            assert (data["departures"], data["arrivals"]) == daily_counts(db, station) == expected
            assert data["net_departures"] == expected[0] - expected[1]

        hourly = client.get("/stations/31600/hourly-activity", params={"date": DAY})
        assert hourly.status_code == 200
        buckets = {6: (0, 1), 8: (12, 5), 9: (8, 0), 11: (4, 0), 18: (0, 3), 23: (1, 0), 0: (0, 1)}
        assert [(row["hour"], row["departures"], row["arrivals"]) for row in hourly.json()["hours"]] == [
            (f"{hour:02d}:00", *buckets.get(hour, (0, 0))) for hour in range(24)
        ]
        following = client.get("/stations/31601/hourly-activity", params={"date": "2025-01-15"})
        assert following.status_code == 200
        assert following.json()["hours"][0] == {"hour": "00:00", "departures": 1, "arrivals": 1}
        prior = client.get("/stations/31601/hourly-activity", params={"date": "2025-01-13"})
        assert prior.status_code == 200
        assert prior.json()["hours"][23] == {"hour": "23:00", "departures": 1, "arrivals": 0}

        for minimum, stations in [(20, ["31601", "31600"]), (1, ["31601", "31600", "31633"])]:
            ranking = client.get("/stations/imbalance", params={"date": DAY, "min_activity": minimum})
            assert ranking.status_code == 200
            expected_rows = []
            for station in stations:
                departures, arrivals = daily_counts(db, station)
                expected_rows.append({
                    "station_id": station,
                    "departures": departures,
                    "arrivals": arrivals,
                    "net_departures": departures - arrivals,
                    "total_activity": departures + arrivals,
                    "imbalance_rate": {"31600": 42.86, "31601": 51.52, "31633": 20.0}[station],
                })
            assert ranking.json() == {
                "date": DAY, "min_activity": minimum, "total_stations": len(stations), "stations": expected_rows,
            }
