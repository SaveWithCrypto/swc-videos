// Run inside the built-in browser on any https://nioctib.live page (javascript_tool). Returns one JSON object.
(async () => {
  const g = async u => { for (let k = 0; k < 4; k++) { try { const r = await fetch(u); if (r.ok) { const j = await r.json(); if (!j.candles || j.candles.length) return j } } catch (e) { } await new Promise(r => setTimeout(r, 3000)) } return null };
  const now = Date.now(), out = { generatedAt: new Date(now).toISOString(), pressure: {}, notes: [] };
  // Spot vs futures pressure over Jordan's usual windows, from 15m candles
  for (const mk of ['spot', 'perp']) {
    const d = await g(`/api/flow/candles?asset=BTC&market=${mk}&interval=900&limit=96`);
    const c = d ? d.candles : [];
    if (c.length < 90) out.notes.push(`${mk}: only ${c.length}/96 15m candles (feed gaps)`);
    for (const [lab, mins] of [['30m', 30], ['1h', 60], ['4h', 240], ['12h', 720], ['24h', 1440]]) {
      const w = c.filter(x => x.time >= now - mins * 60000);
      const b = w.reduce((a, x) => a + x.buyUsd, 0), s = w.reduce((a, x) => a + x.sellUsd, 0);
      out.pressure[`${mk}_${lab}`] = b + s ? { buyPct: +(100 * b / (b + s)).toFixed(1), netM: +((b - s) / 1e6).toFixed(1) } : null;
    }
  }
  // Hourly price (perp) + aggregated OI
  const pc = ((await g('/api/flow/candles?asset=BTC&market=perp&interval=3600&limit=26')) || { candles: [] }).candles.slice(-25);
  const oiP = ((await g('/api/onchain/metric?id=derivatives.oi-aggregate&asset=BTC')) || { points: [] }).points;
  const oiM = Object.fromEntries(oiP.map(p => [p.t, p.v]));
  const hm = t => new Date(t).toLocaleTimeString('en-GB', { timeZone: 'Europe/London', hour: '2-digit', minute: '2-digit' });
  const last24 = pc.slice(-24);
  out.price = {
    last: pc.length ? pc.at(-1).priceClose : null, open24: last24.length ? last24[0].priceOpen : null,
    high24: Math.max(...last24.map(c => c.priceHigh)), low24: Math.min(...last24.map(c => c.priceLow)),
    startLabel: last24.length ? hm(last24[0].time) : ''
  };
  out.price.chg24Pct = out.price.open24 ? +((out.price.last / out.price.open24 - 1) * 100).toFixed(2) : null;
  // hourly rows: [label(London), close, oiB, high, low]
  out.hourly = last24.map(c => [hm(Math.min(c.time + 3600000, now)), c.priceClose, oiM[c.time] ? +(oiM[c.time] / 1e9).toFixed(3) : null, c.priceHigh, c.priceLow]);
  // fill missing OI with previous value
  for (let i = 0; i < out.hourly.length; i++) if (out.hourly[i][2] == null) out.hourly[i][2] = i ? out.hourly[i - 1][2] : (oiP.length ? +(oiP.at(-1).v / 1e9).toFixed(3) : 0);
  if (oiP.length > 170) {
    const L = oiP.length - 1, ch = h => +((oiP[L].v / oiP[L - h].v - 1) * 100).toFixed(2);
    out.oi = { lastB: +(oiP[L].v / 1e9).toFixed(2), asOf: new Date(oiP[L].t).toISOString(), chg4h: ch(4), chg12h: ch(12), chg24h: ch(24), chg7d: ch(168) };
  }
  const f = ((await g('/api/onchain/metric?id=derivatives.funding-weighted&asset=BTC')) || { points: [] }).points;
  if (f.length > 168) {
    const w = f.slice(-168).map(p => p.v);
    out.funding = { last: +f.at(-1).v.toFixed(4), avg24: +(f.slice(-24).reduce((a, p) => a + p.v, 0) / 24).toFixed(4), min7d: +Math.min(...w).toFixed(4), max7d: +Math.max(...w).toFixed(4) };
  }
  // Spot share of volume (30d rolling)
  const vd = await g('/api/flow/volume-distribution?window=2592000&range=2592000');
  try { const lp = vd.points.at(-1); out.spotSharePct = +lp.spotSharePercent.toFixed(1); out.spotSharePrevPct = vd.comparisonSpotSharePercent != null ? +vd.comparisonSpotSharePercent.toFixed(1) : null } catch (e) { out.spotSharePct = null }
  // ETF daily totals (last 6 sessions) + per-ticker for the latest days
  const e = await g('/api/etf/summary');
  if (e) {
    const dates = e.recentDates, n = dates.length;
    out.etf = dates.slice(-6).map((d, k) => {
      const i = n - 6 + k; let tot = 0, missing = [];
      for (const t of e.tickers) { const v = t.recentFlows[i]; if (v == null) missing.push(t.ticker); else tot += v }
      return { date: d, totalM: +tot.toFixed(1), missing, pending: missing.length === e.tickers.length, ibit: e.tickers.find(t => t.ticker === 'IBIT')?.recentFlows[i] ?? null };
    });
    out.etfCumulativeM = +e.totalCumulativeUsdM.toFixed(0);
  }
  return out;
})()
