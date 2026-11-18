from fastapi import FastAPI, HTTPException

app = FastAPI()
VALID_STATION_IDS = {"31600", "31601"}


@app.get("/stations/{station_id}")
def get_station(station_id: str, hour: int):
    if station_id not in VALID_STATION_IDS:
        raise HTTPException(status_code=404, detail="Station not found")

    return {
        "station_id": station_id,
        "hour": hour,
        "period": "night" if hour < 7 else "day",
    }
