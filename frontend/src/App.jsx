import { useState } from 'react';

function describeHttpError(status, detail) {
  if (status === 422) return '請確認起訖時間格式正確，且起始時間早於結束時間。';
  if (status === 503) return '站點資料暫時無法取得，請稍後重試。';
  return typeof detail === 'string' ? detail : '查詢失敗，請稍後重試。';
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

    setQuery({ status: 'loading' });
    let response;
    try {
      response = await fetch(`/stations/${station}/activity?${params}`);
    } catch {
      setQuery({ status: 'error', message: '無法連線，請檢查網路後重試。' });
      return;
    }

    if (!response.ok) {
      const body = await response.json().catch(() => null);
      setQuery({
        status: 'error',
        message: `HTTP ${response.status} · ${describeHttpError(response.status, body?.detail)}`,
      });
      return;
    }

    try {
      setQuery({ status: 'success', data: await response.json() });
    } catch {
      setQuery({ status: 'error', message: '無法讀取查詢結果，請重試。' });
    }
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
    </main>
  );
}
