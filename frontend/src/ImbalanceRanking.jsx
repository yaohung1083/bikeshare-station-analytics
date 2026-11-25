import { useRef, useState } from 'react';
import { describeNetDepartures, formatImbalanceRate, rankingView } from './imbalanceRanking.js';

export default function ImbalanceRanking({ requestActivity }) {
  const [query, setQuery] = useState({ status: 'idle' });
  const [expanded, setExpanded] = useState(false);
  const pending = useRef(false);
  const loading = query.status === 'loading';

  async function search(event) {
    event.preventDefault();
    if (pending.current) return;

    const fields = new FormData(event.currentTarget);
    const date = fields.get('date');
    const minActivity = fields.get('min_activity');
    const parsedDate = new Date(`${date}T00:00:00Z`);
    if (!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(date) || date.startsWith('0000-')
        || Number.isNaN(parsedDate.getTime()) || parsedDate.toISOString().slice(0, 10) !== date) {
      setQuery({ status: 'error', message: '請輸入有效日期（YYYY-MM-DD）。' });
      return;
    }
    if (!/^[0-9]+$/.test(minActivity) || !/[1-9]/.test(minActivity)) {
      setQuery({ status: 'error', message: '最低活動量須為大於或等於 1 的整數。' });
      return;
    }

    const params = new URLSearchParams({ date, min_activity: minActivity });
    pending.current = true;
    setExpanded(false);
    try {
      await requestActivity(
        `/stations/imbalance?${params}`,
        setQuery,
        '請確認日期有效，且最低活動量為大於或等於 1 的整數。',
      );
    } finally {
      pending.current = false;
    }
  }

  return (
    <section className="hourly imbalance-ranking" aria-labelledby="imbalance-title">
      <h2 id="imbalance-title">站點失衡排行榜</h2>
      <form onSubmit={search}>
        <label>
          日期
          <input name="date" type="date" min="0001-01-01" max="9999-12-31" defaultValue="2025-01-14" required />
        </label>
        <label>
          最低活動量
          <input name="min_activity" inputMode="numeric" defaultValue="20" required />
        </label>
        <button type="submit" disabled={loading}>{loading ? '查詢中…' : '查詢排行榜'}</button>
      </form>
      {loading && <p role="status">正在取得站點失衡排行榜。</p>}
      {query.status === 'error' && <p className="error" role="alert">{query.message}</p>}
      {query.status === 'success' && (
        <RankingResults data={query.data} expanded={expanded} onToggle={() => setExpanded((value) => !value)} />
      )}
    </section>
  );
}

function RankingResults({ data, expanded, onToggle }) {
  const { visibleStations, canExpand, highestRate } = rankingView(data.stations, expanded);

  return (
    <div className="ranking-results">
      <p role="status">
        <strong>{data.date}</strong> · 最低活動量 {data.min_activity} 次 · 共 {data.total_stations} 站
        {highestRate !== null && <> · 最高失衡率 {formatImbalanceRate(highestRate)}</>}
      </p>
      {data.total_stations === 0 ? <p>查無符合條件的站點</p> : (
        <>
          <div className="ranking-scroll" role="region" aria-label="站點失衡排行榜表格" tabIndex={0}>
            <table>
              <thead>
                <tr>
                  <th scope="col">排名</th>
                  <th scope="col">站點 ID</th>
                  <th scope="col">借出量</th>
                  <th scope="col">歸還量</th>
                  <th scope="col">淨借出量</th>
                  <th scope="col">總活動量</th>
                  <th scope="col">失衡率</th>
                </tr>
              </thead>
              <tbody>
                {visibleStations.map((station, index) => {
                  const net = describeNetDepartures(station.net_departures);
                  return (
                    <tr key={station.station_id}>
                      <td>{index + 1}</td>
                      <th scope="row">{station.station_id}</th>
                      <td>{station.departures}</td>
                      <td>{station.arrivals}</td>
                      <td>{net.value}<small>{net.label}</small></td>
                      <td>{station.total_activity}</td>
                      <td>{formatImbalanceRate(station.imbalance_rate)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {canExpand && (
            <button type="button" aria-expanded={expanded} onClick={onToggle}>
              {expanded ? '收起為前 10 站' : `顯示全部 ${data.total_stations} 站`}
            </button>
          )}
        </>
      )}
    </div>
  );
}
