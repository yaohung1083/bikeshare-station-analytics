import assert from 'node:assert/strict';
import test from 'node:test';
import { describeNetDepartures, formatImbalanceRate, rankingView } from './imbalanceRanking.js';

for (const size of [0, 1, 10, 11]) {
  test(`ranking preview and expansion with ${size} stations`, () => {
    const response = {
      date: '2025-01-14',
      min_activity: 20,
      total_stations: size,
      stations: Array.from({ length: size }, (_, index) => ({
        station_id: String(100 - index),
        departures: 8,
        arrivals: 22,
        net_departures: -14,
        total_activity: 30,
        imbalance_rate: 46.67,
      })),
    };
    const originalOrder = response.stations.map(({ station_id }) => station_id);
    const collapsed = rankingView(response.stations, false);
    const expanded = rankingView(response.stations, true);
    assert.deepEqual(collapsed.visibleStations.map(({ station_id }) => station_id), originalOrder.slice(0, 10));
    assert.deepEqual(expanded.visibleStations.map(({ station_id }) => station_id), originalOrder);
    assert.deepEqual(response.stations.map(({ station_id }) => station_id), originalOrder);
    assert.equal(collapsed.canExpand, size > 10);
    assert.equal(expanded.canExpand, size > 10);
    assert.equal(collapsed.highestRate, size ? 46.67 : null);
  });
}

test('shows all three net departure signs with direction labels', () => {
  assert.deepEqual(describeNetDepartures(7), { value: '+7', label: '借出較多' });
  assert.deepEqual(describeNetDepartures(-14), { value: '-14', label: '歸還較多' });
  assert.deepEqual(describeNetDepartures(0), { value: '0', label: '借還相等' });
});

test('formats API percentages without multiplying again', () => {
  assert.equal(formatImbalanceRate(46.67), '46.67%');
  assert.equal(formatImbalanceRate(5), '5.00%');
  assert.equal(formatImbalanceRate(0), '0.00%');
  assert.equal(rankingView([{ imbalance_rate: 0 }], false).highestRate, 0);
});
