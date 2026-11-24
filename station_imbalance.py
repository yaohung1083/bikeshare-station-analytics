"""Shared SQL for the daily station imbalance ranking."""

ASCII_WHITESPACE = " \t\n\r\v\f"

IMBALANCE_SQL = """
WITH counts AS (
    SELECT start_station_id AS station_id, COUNT(*) AS departures, 0 AS arrivals
    FROM trips
    WHERE started_at >= :first AND started_at < :last
      AND start_station_id IS NOT NULL AND trim(start_station_id, :whitespace) <> ''
    GROUP BY start_station_id
    UNION ALL
    SELECT end_station_id, 0, COUNT(*)
    FROM trips
    WHERE ended_at >= :first AND ended_at < :last
      AND end_station_id IS NOT NULL AND trim(end_station_id, :whitespace) <> ''
    GROUP BY end_station_id
), totals AS (
    SELECT station_id, SUM(departures) AS departures, SUM(arrivals) AS arrivals,
           SUM(departures - arrivals) AS net_departures,
           SUM(departures + arrivals) AS total_activity
    FROM counts
    GROUP BY station_id
)
SELECT station_id, departures, arrivals, net_departures, total_activity,
       100.0 * ABS(net_departures) / total_activity AS imbalance_rate
FROM totals
WHERE total_activity >= :min_activity
ORDER BY imbalance_rate DESC, ABS(net_departures) DESC, station_id ASC
"""
