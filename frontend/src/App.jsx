import { useState } from 'react';

function describeHttpError(status, detail, invalidInputMessage) {
  if (status === 422) return invalidInputMessage ?? '請確認起訖時間格式正確，且起始時間早於結束時間。';
  if (status === 503) return '站點資料暫時無法取得，請稍後重試。';
  return typeof detail === 'string' ? detail : '查詢失敗，請稍後重試。';
}

async function requestActivity(url, setQuery, invalidInputMessage) {
  setQuery({ status: 'loading' });
  let response;
  try {
    response = await fetch(url);
  } catch {
    setQuery({ status: 'error', message: '無法連線，請檢查網路後重試。' });
    return;
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    setQuery({
      status: 'error',
      message: `HTTP ${response.status} · ${describeHttpError(response.status, body?.detail, invalidInputMessage)}`,
    });
    return;
  }

  try {
    setQuery({ status: 'success', data: await response.json() });
  } catch {
    setQuery({ status: 'error', message: '無法讀取查詢結果，請重試。' });
  }
}

export default function App() {
  const [query, setQuery] = useState({ status: 'idle' });
  const loading = query.status === 'loading';

  async function search(event) {
    event.preventDefault();
    const fields = new FormData(event.currentTarget);
    const station = encodeURIComponent(fields.get('station_id').trim());
    const params = new URLSearchParams({
      start: fields.get('start'),
      end: fields.get('end'),
    });

    await requestActivity(`/stations/${station}/activity?${params}`, setQuery);
  }

  return (
    <main>
      <header>
        <p className="brand">Capital Bikeshare</p>
        <h1>站點活動查詢</h1>
      </header>
      <form onSubmit={search}>
        <label>
          站點 ID
          <input name="station_id" defaultValue="31600" required />
        </label>
        <label>
          起始時間
          <input name="start" type="datetime-local" step="1" defaultValue="2025-01-14T08:00:00" required />
        </label>
        <label>
          結束時間（不含）
          <input name="end" type="datetime-local" step="1" defaultValue="2025-01-14T09:00:00" required />
        </label>
        <button type="submit" disabled={loading}>{loading ? '查詢中…' : '查詢活動'}</button>
      </form>
      <section aria-live="polite" aria-label="查詢結果">
        {loading && <p role="status">正在取得站點活動。</p>}
        {query.status === 'error' && <p className="error" role="alert">{query.message}</p>}
        {query.status === 'success' && (
          <>
            <h2>站點 {query.data.station_id}</h2>
            <p className="times">{query.data.start.replace('T', ' ')} 至 {query.data.end.replace('T', ' ')}</p>
            <dl>
              <div><dt>借出</dt><dd>{query.data.departures}</dd></div>
              <div><dt>歸還</dt><dd>{query.data.arrivals}</dd></div>
              <div><dt>淨借出</dt><dd>{query.data.net_departures}</dd></div>
            </dl>
          </>
        )}
      </section>
      <HourlyActivity />
    </main>
  );
}

function HourlyActivity() {
  const [query, setQuery] = useState({ status: 'idle' });
  const loading = query.status === 'loading';

  async function search(event) {
    event.preventDefault();
    const fields = new FormData(event.currentTarget);
    const station = encodeURIComponent(fields.get('station_id').trim());
    const params = new URLSearchParams({ date: fields.get('date') });
    await requestActivity(
      `/stations/${station}/hourly-activity?${params}`,
      setQuery,
      '請輸入有效日期（YYYY-MM-DD）。',
    );
  }

  return (
    <section className="hourly" aria-labelledby="hourly-title">
      <h2 id="hourly-title">每小時借還趨勢</h2>
      <form onSubmit={search}>
        <label>
          站點 ID
          <input name="station_id" defaultValue="31600" required />
        </label>
        <label>
          日期
          <input name="date" type="date" defaultValue="2025-01-14" required />
        </label>
        <button type="submit" disabled={loading}>{loading ? '查詢中…' : '查詢趨勢'}</button>
      </form>
      <div aria-live="polite">
        {loading && <p role="status">正在取得每小時活動。</p>}
        {query.status === 'error' && <p className="error" role="alert">{query.message}</p>}
        {query.status === 'success' && <HourlyChart data={query.data} />}
      </div>
    </section>
  );
}

const SERIES = [
  { key: 'departures', label: '借出', className: 'departures-line' },
  { key: 'arrivals', label: '歸還', className: 'arrivals-line' },
];

function HourlyChart({ data: { station_id, date, hours } }) {
  const maximum = Math.max(...hours.flatMap(({ departures, arrivals }) => [departures, arrivals]));
  const step = Math.max(1, Math.ceil(maximum / 4));
  const x = (index) => 48 + (index / 23) * 552;
  const y = (count) => 188 - (count / (4 * step)) * 160;

  return (
    <figure className="hourly-chart">
      <figcaption>站點 {station_id} · {date}</figcaption>
      <svg viewBox="0 0 640 224" role="img" aria-label="每小時借出與歸還雙折線圖，詳細數字見下方表格">
        {[0, 1, 2, 3, 4].map((tick) => (
          <g key={tick}>
            <line className="chart-grid" x1="48" x2="600" y1={y(tick * step)} y2={y(tick * step)} />
            <text x="40" y={y(tick * step)} dy=".35em" textAnchor="end">{tick * step}</text>
          </g>
        ))}
        {[0, 6, 12, 18, 23].map((index) => (
          <text key={index} x={x(index)} y="213" textAnchor="middle">{hours[index].hour}</text>
        ))}
        {SERIES.map(({ key, className }) => (
          <polyline
            key={key}
            className={className}
            points={hours.map((bucket, index) => `${x(index)},${y(bucket[key])}`).join(' ')}
          />
        ))}
      </svg>
      <ul className="chart-legend">
        {SERIES.map(({ key, label, className }) => (
          <li key={key}><span aria-hidden="true" className={className} />{label}</li>
        ))}
      </ul>
      {maximum === 0 && <p>這天的 24 個小時都沒有借還紀錄。</p>}
      <details>
        <summary>查看每小時數字</summary>
        <table>
          <thead><tr><th scope="col">時段</th><th scope="col">借出</th><th scope="col">歸還</th></tr></thead>
          <tbody>
            {hours.map(({ hour, departures, arrivals }) => (
              <tr key={hour}><th scope="row">{hour}</th><td>{departures}</td><td>{arrivals}</td></tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}
