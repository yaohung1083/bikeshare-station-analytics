const PREVIEW_SIZE = 10;

export function rankingView(stations, expanded) {
  return {
    visibleStations: expanded ? stations : stations.slice(0, PREVIEW_SIZE),
    canExpand: stations.length > PREVIEW_SIZE,
    highestRate: stations[0]?.imbalance_rate ?? null,
  };
}

export function describeNetDepartures(net) {
  if (net > 0) return { value: `+${net}`, label: '借出較多' };
  if (net < 0) return { value: String(net), label: '歸還較多' };
  return { value: '0', label: '借還相等' };
}

export function formatImbalanceRate(rate) {
  return `${rate.toFixed(2)}%`;
}
