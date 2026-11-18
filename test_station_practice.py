import pytest
from fastapi.testclient import TestClient

from station_practice import app

client = TestClient(app)


@pytest.mark.parametrize("station_id", ["31600", "31601"])
@pytest.mark.parametrize(
    ("hour", "period"),
    [(0, "night"), (5, "night"), (6, "night"), (7, "day"), (23, "day")],
)
def test_get_station(station_id, hour, period):
    response = client.get(f"/stations/{station_id}", params={"hour": hour})

    assert response.status_code == 200
    assert response.json() == {"station_id": station_id, "hour": hour, "period": period}


@pytest.mark.parametrize("station_id", ["31602", "031600", "unknown"])
def test_unknown_station_returns_404(station_id):
    response = client.get(f"/stations/{station_id}", params={"hour": 6})

    assert response.status_code == 404


@pytest.mark.parametrize("params", [{"hour": "5.5"}, {}], ids=["non-integer", "missing"])
def test_invalid_hour_returns_422(params):
    response = client.get("/stations/31600", params=params)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "hour"]
