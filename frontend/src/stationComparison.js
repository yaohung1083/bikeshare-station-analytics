const HOURS = Array.from({ length: 24 }, (_, index) => `${String(index).padStart(2, '0')}:00`);

export const METRICS = {
  departures: '借出量',
  arrivals: '歸還量',
  net_departures: '淨借出量',
};

export function indexStationHours(hours) {
  if (!Array.isArray(hours) || hours.length !== HOURS.length) {
    throw new Error('回應缺少完整的 24 小時資料。');
  }
  const indexed = new Map(hours.map((row) => [row?.hour, row]));
  for (const hour of HOURS) {
    const row = indexed.get(hour);
    if (!row || ![row.departures, row.arrivals].every((count) => Number.isInteger(count) && count >= 0)) {
      throw new Error('回應含有無效的時段或計數。');
    }
  }
  return indexed;
}

export function compareStationHours(stationA, stationB, metric) {
  function value(row) {
    return metric === 'net_departures' ? row.departures - row.arrivals : row[metric];
  }

  return HOURS.map((hour) => ({
    hour,
    stationA: value(stationA.get(hour)),
    stationB: value(stationB.get(hour)),
  }));
}

export function comparisonAxis(rows) {
  const values = rows.flatMap(({ stationA, stationB }) => [stationA, stationB]);
  const minimum = Math.min(0, ...values);
  const maximum = Math.max(1, ...values);
  const step = Math.max(1, Math.ceil((maximum - minimum) / 4));
  const bottom = Math.floor(minimum / step) * step;
  const top = Math.ceil(maximum / step) * step;
  const ticks = Array.from({ length: (top - bottom) / step + 1 }, (_, index) => bottom + index * step);
  return { bottom, top, ticks };
}
