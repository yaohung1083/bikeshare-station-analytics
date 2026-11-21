import assert from 'node:assert/strict';
import test from 'node:test';
import { compareStationHours, comparisonAxis, indexStationHours } from './stationComparison.js';

function hours(overrides = {}) {
  return Array.from({ length: 24 }, (_, index) => {
    const [departures, arrivals] = overrides[index] ?? [0, 0];
    return { hour: `${String(index).padStart(2, '0')}:00`, departures, arrivals };
  });
}

test('aligns by hour, preserves station order, and switches metrics on the same data', () => {
  const a = indexStationHours(hours({ 8: [2, 5], 23: [7, 1] }).reverse());
  const b = indexStationHours(hours({ 8: [9, 2], 23: [0, 4] }));
  const cases = [
    ['departures', [2, 9], [7, 0]],
    ['arrivals', [5, 2], [1, 4]],
    ['net_departures', [-3, 7], [6, -4]],
  ];
  for (const [metric, atEight, atTwentyThree] of cases) {
    const rows = compareStationHours(a, b, metric);
    assert.deepEqual(rows.map(({ hour }) => hour), hours().map(({ hour }) => hour));
    assert.deepEqual(rows[8], { hour: '08:00', stationA: atEight[0], stationB: atEight[1] });
    assert.deepEqual(rows[23], { hour: '23:00', stationA: atTwentyThree[0], stationB: atTwentyThree[1] });
    assert.deepEqual(rows[9], { hour: '09:00', stationA: 0, stationB: 0 });
  }
});

test('accepts all-zero stations but rejects incomplete, duplicate or negative count data', () => {
  const zeros = hours();
  assert.equal(indexStationHours(zeros).size, 24);
  assert.throws(() => indexStationHours(zeros.slice(1)));
  assert.throws(() => indexStationHours([zeros[1], ...zeros.slice(1)]));
  assert.throws(() => indexStationHours(hours({ 2: [-1, 0] })));
});

test('axis includes negative counts, zero and positive counts', () => {
  const axis = comparisonAxis([{ stationA: -4, stationB: 7 }]);
  assert.ok(axis.bottom <= -4 && axis.top >= 7);
  assert.ok(axis.ticks.includes(0));
  const zeros = comparisonAxis([{ stationA: 0, stationB: 0 }]);
  assert.equal(zeros.bottom, 0);
  assert.ok(zeros.top > 0);
});
