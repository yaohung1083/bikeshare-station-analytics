import { useRef, useState } from 'react';
import { compareStationHours, comparisonAxis, indexStationHours, METRICS } from './stationComparison.js';

async function fetchStation(station, date) {
  const params = new URLSearchParams({ date });
  let response;
  try {
    response = await fetch(`/stations/${encodeURIComponent(station)}/hourly-activity?${params}`);
  } catch {
    throw new Error('無法連線，請檢查網路後重試。');
  }

  if (!response.ok) {
    if (response.status === 422) throw new Error('HTTP 422 · 請確認日期有效。');
    if (response.status === 503) throw new Error('HTTP 503 · 站點資料暫時無法取得。');
    throw new Error(`HTTP ${response.status} · 查詢失敗。`);
  }

  const data = await response.json().catch(() => {
    throw new Error('無法讀取站點資料。');
  });
  if (data?.station_id !== station || data.date !== date) {
    throw new Error('回應的站點或日期與查詢不符。');
  }
  return indexStationHours(data.hours);
}

export default function StationComparison() {
  const [query, setQuery] = useState({ status: 'idle' });
  const [metric, setMetric] = useState('departures');
  const pending = useRef(false);
  const loading = query.status === 'loading';

  async function search(event) {
    event.preventDefault();
    if (pending.current) return;

    const fields = new FormData(event.currentTarget);
    const stationIds = ['station_a', 'station_b'].map((field) => fields.get(field).trim());
    const date = fields.get('date');
    if (stationIds.some((id) => !id) || stationIds[0] === stationIds[1]) {
      setQuery({ status: 'error', messages: ['請輸入兩個不同的站點 ID。'] });
      return;
    }

    pending.current = true;
    setQuery({ status: 'loading' });
    try {
      const results = await Promise.allSettled(stationIds.map((station) => fetchStation(station, date)));
      const messages = results.flatMap((result, index) => result.status === 'rejected'
        ? [`站點 ${index === 0 ? 'A' : 'B'}（${stationIds[index]}）：${result.reason.message}`]
        : []);
      if (messages.length) {
        setQuery({ status: 'error', messages });
      } else {
        setQuery({ status: 'success', stationIds, date, stations: results.map((result) => result.value) });
      }
    } finally {
      pending.current = false;
    }
  }

  return (
    <section className="hourly station-comparison" aria-labelledby="comparison-title">
      <h2 id="comparison-title">雙站比較</h2>
      <form onSubmit={search}>
        <label>站點 A<input name="station_a" defaultValue="31600" required /></label>
        <label>站點 B<input name="station_b" defaultValue="31601" required /></label>
        <label>共同日期<input name="date" type="date" defaultValue="2025-01-14" required /></label>
        <button type="submit" disabled={loading}>{loading ? '查詢中…' : '比較站點'}</button>
      </form>
      {loading && <p role="status">正在取得兩站資料。</p>}
      {query.status === 'error' && (
        <div className="error comparison-errors" role="alert">
          {query.messages.map((message) => <p key={message}>{message}</p>)}
        </div>
      )}
      {query.status === 'success' && (
        <ComparisonChart
          date={query.date}
          stationIds={query.stationIds}
          rows={compareStationHours(...query.stations, metric)}
          metric={metric}
          setMetric={setMetric}
        />
      )}
    </section>
  );
}

function ComparisonChart({ date, stationIds, rows, metric, setMetric }) {
  const { bottom, top, ticks } = comparisonAxis(rows);
  const x = (index) => 60 + index / 23 * 540;
  const y = (value) => 188 - ((value - bottom) / (top - bottom)) * 160;
  const series = [
    { key: 'stationA', name: `A · ${stationIds[0]}`, style: 'departures-line' },
    { key: 'stationB', name: `B · ${stationIds[1]}`, style: 'arrivals-line' },
  ];

  return (
    <figure className="hourly-chart">
      <figcaption>{date} · {METRICS[metric]}（次／小時）</figcaption>
      <label className="comparison-metric">
        比較指標
        <select value={metric} onChange={(event) => setMetric(event.target.value)}>
          {Object.entries(METRICS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select>
      </label>
      <svg viewBox="0 0 640 224" role="img" aria-label={`兩站每小時${METRICS[metric]}，詳細數字見下方表格`}>
        {ticks.map((tick) => (
          <g key={tick}>
            <line className={tick === 0 ? 'comparison-zero' : 'chart-grid'} x1="60" x2="600" y1={y(tick)} y2={y(tick)} />
            <text x="52" y={y(tick)} dy=".35em" textAnchor="end">{tick}</text>
          </g>
        ))}
        {[0, 6, 12, 18, 23].map((index) => (
          <text key={index} x={x(index)} y="213" textAnchor="middle">{rows[index].hour}</text>
        ))}
        {series.map(({ key, style }) => (
          <polyline key={key} className={style} points={rows.map((row, index) => `${x(index)},${y(row[key])}`).join(' ')} />
        ))}
      </svg>
      <ul className="chart-legend">
        {series.map(({ key, name, style }) => (
          <li key={key}><span aria-hidden="true" className={style} />{name}</li>
        ))}
      </ul>
      <details>
        <summary>查看 24 小時對照表</summary>
        <table>
          <thead>
            <tr><th scope="col">時段</th>{series.map(({ key, name }) => <th key={key} scope="col">{name}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map(({ hour, stationA, stationB }) => (
              <tr key={hour}><th scope="row">{hour}</th><td>{stationA}</td><td>{stationB}</td></tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}
