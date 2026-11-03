import React, { useEffect, useMemo, useState } from 'react';

const money = (n) => n == null ? '—' : new Intl.NumberFormat('en-IE', {
  style: 'currency', currency: 'EUR', maximumFractionDigits: 2
}).format(n);
const percent = (n) => n == null ? '—' : `${n > 0 ? '+' : ''}${n.toFixed(1)}%`;
const dateText = (iso) => iso == null ? '—' : new Intl.DateTimeFormat('en-GB', {
  day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC'
}).format(new Date(`${iso}T00:00:00Z`));
const promoNumber = (id) => Number(id.slice(1));

function Stat({ label, value, hint, tone }) {
  return <article className={`stat ${tone ?? ''}`}>
    <span className="stat-label">{label}</span>
    <strong className="stat-value">{value}</strong>
    <span className="stat-hint">{hint}</span>
  </article>;
}

function MoneyBar({ label, value, max, note }) {
  const width = max > 0 && value != null ? `${Math.max(0, value / max * 100)}%` : '0%';
  return <div className="bar-item">
    <div className="bar-row"><span>{label}</span><strong>{money(value)}</strong></div>
    <div className="bar-track"><div className={`bar-fill ${label === 'During promo' ? 'bar-during' : 'bar-before'}`} style={{ width }} /></div>
    {note && <div className="bar-note">{note}</div>}
  </div>;
}

function Detail({ promo }) {
  if (!promo) return <aside className="panel detail"><p>No promotion matches the current filters.</p></aside>;
  const valid = promo.status === 'measurable';
  const max = Math.max(promo.before ?? 0, promo.during ?? 0);
  return <aside className="panel detail">
    <div className="detail-top"><span className="eyebrow">PROMOTION DETAIL</span><span className="mono muted">{promo.promo_id}</span></div>
    <h2>{promo.site_name}</h2>
    <p className="detail-games">{promo.games_label === 'ALL' ? `All ${promo.games.length} games at this site` : promo.games.join(', ')}</p>
    <div className="date-line"><span>{dateText(promo.start_date)}</span><span className="dash">–</span><span>{dateText(promo.end_date)}</span></div>
    <div className={`detail-hero ${valid ? (promo.uplift >= 0 ? 'up' : 'down') : 'unavailable'}`}>
      <span>{valid ? 'Observed stake uplift' : 'Not fairly measurable'}</span>
      <strong>{percent(promo.uplift)}</strong>
      <small>{valid ? `Same ${promo.days}-day period immediately before the promo` : 'Excluded from calculated uplift figures'}</small>
    </div>
    <div className="comparison-title">Stake comparison</div>
    <MoneyBar label="Before promo" value={promo.before} max={max} note={promo.before_days_present != null && promo.before_days_present !== promo.expected_days ? `Only ${promo.before_days_present}/${promo.expected_days} days observed — incomplete baseline` : null} />
    <MoneyBar label="During promo" value={promo.during} max={max} />
    {!valid && <div className="warning"><strong>Why is uplift unavailable?</strong><p>{promo.reason}</p></div>}
    <div className="detail-meta"><span>Duration</span><strong>{promo.days == null ? '—' : `${promo.days} days`}</strong></div>
    <div className="detail-meta"><span>Games included</span><strong>{promo.games.length}</strong></div>
    {promo.expected_records != null && <div className="detail-meta"><span>Baseline coverage</span><strong>{promo.before_records}/{promo.expected_records} records</strong></div>}
    <p className="detail-disclaimer">An observed increase does not prove the promotion caused it. Seasonality, weekday effects, and other factors may influence stakes.</p>
  </aside>;
}

function App() {
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState('');
  const [site, setSite] = useState('all');
  const [status, setStatus] = useState('all');
  const [sort, setSort] = useState('id');
  const [selectedId, setSelectedId] = useState('P01');

  useEffect(() => {
    fetch('/api/report')
      .then(response => { if (!response.ok) throw Error(`API responded ${response.status}`); return response.json(); })
      .then(setReport)
      .catch(err => setError(err.message));
  }, []);

  const promos = report?.promos ?? [];
  const measured = useMemo(() => promos.filter(p => p.status === 'measurable'), [promos]);
  const positive = measured.filter(p => p.uplift > 0).length;
  const median = useMemo(() => {
    const values = measured.map(p => p.uplift).sort((a, b) => a - b);
    if (!values.length) return null;
    const middle = Math.floor(values.length / 2);
    return values.length % 2 ? values[middle] : (values[middle - 1] + values[middle]) / 2;
  }, [measured]);
  const sites = useMemo(() => [...new Map(promos.map(p => [p.site_id, p.site_name])).entries()]
    .sort((a, b) => a[1].localeCompare(b[1])), [promos]);
  const filtered = useMemo(() => promos.filter(p => {
    const matchesQuery = `${p.promo_id} ${p.site_name} ${p.games_label} ${p.games.join(' ')}`.toLowerCase().includes(query.toLowerCase());
    return matchesQuery && (site === 'all' || p.site_id === site) && (status === 'all' || p.status === status);
  }).sort((a, b) => {
    if (sort === 'uplift-high' || sort === 'uplift-low') {
      if (a.uplift == null && b.uplift == null) return promoNumber(a.promo_id) - promoNumber(b.promo_id);
      if (a.uplift == null) return 1;
      if (b.uplift == null) return -1;
      return (a.uplift - b.uplift) * (sort === 'uplift-high' ? -1 : 1);
    }
    if (sort === 'start') return a.start_date.localeCompare(b.start_date);
    return promoNumber(a.promo_id) - promoNumber(b.promo_id);
  }), [promos, query, site, status, sort]);
  const selection = filtered.find(p => p.promo_id === selectedId) ?? filtered[0];

  if (error) return <div className="load-state"><h1>Could not load data</h1><p>{error}</p><p>Start the Python API with <code>uvicorn backend.api:app --reload</code> from the project root.</p></div>;
  if (!report) return <div className="load-state"><div className="spinner"/><h1>Loading promotion data…</h1></div>;

  return <div className="app-shell">
    <header className="masthead">
      <div className="brand"><span className="brand-mark">↗</span><div><span className="brand-word">greentube</span><small>ANALYTICS WORKSPACE</small></div></div>
      <span className="masthead-right"><span className="live-dot"/> Data period: 01 Apr – 30 Sep 2026</span>
    </header>
    <main className="main">
      <div className="heading">
        <div><span className="eyebrow">KEY ACCOUNT MANAGEMENT / REPORTING</span><h1>Promotion performance<span className="title-dot">.</span></h1><p>Compare stakes before and during each campaign. Explore the results and identify promotions that cannot be evaluated fairly.</p></div>
        <a className="export-button" href="/api/results.csv" download="results.csv"><span>↓</span> Export results.csv</a>
      </div>
      <section className="stats-grid" aria-label="Overall summary">
        <Stat label="TOTAL PROMOTIONS" value={promos.length} hint="All submitted campaigns" />
        <Stat label="MEASURABLE" value={measured.length} hint="Complete, comparable periods" />
        <Stat label="MEDIAN UPLIFT" value={percent(median)} hint="Across measurable promos only" tone="highlight" />
        <Stat label="POSITIVE / UNMEASURABLE" value={`${positive} / ${promos.length - measured.length}`} hint="Positive uplift / excluded" />
      </section>
      <div className="workspace">
        <section className="panel listing">
          <div className="panel-heading"><div><span className="eyebrow">CAMPAIGN EXPLORER</span><h2>Promotion results</h2></div><span className="result-count">{filtered.length} shown</span></div>
          <div className="filters">
            <label className="search-wrap"><span className="sr-only">Search promotions</span><span className="search-icon">⌕</span><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search ID, site or game…" /></label>
            <label><span className="sr-only">Casino site</span><select value={site} onChange={e => setSite(e.target.value)}><option value="all">All sites</option>{sites.map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>
            <label><span className="sr-only">Measurement status</span><select value={status} onChange={e => setStatus(e.target.value)}><option value="all">All statuses</option><option value="measurable">Measurable</option><option value="unmeasurable">Unmeasurable</option></select></label>
            <label><span className="sr-only">Sort results</span><select value={sort} onChange={e => setSort(e.target.value)}><option value="id">Promo ID ↑</option><option value="uplift-high">Uplift ↓</option><option value="uplift-low">Uplift ↑</option><option value="start">Start date ↑</option></select></label>
          </div>
          <div className="table-scroll"><table><thead><tr><th>Promo</th><th>Site / games</th><th>Dates</th><th className="right">Before</th><th className="right">During</th><th className="right">Uplift</th><th></th></tr></thead><tbody>
            {filtered.map(p => <tr key={p.promo_id} className={selection?.promo_id === p.promo_id ? 'selected-row' : ''}>
              <td className="mono id-cell">{p.promo_id}</td>
              <td className="site-cell"><strong>{p.site_name}</strong><small title={p.games_label}>{p.games_label === 'ALL' ? `ALL (${p.games.length} games)` : p.games_label}</small></td>
              <td className="dates-cell">{p.start_date ? `${dateText(p.start_date).replace(' 2026', '')} – ${dateText(p.end_date).replace(' 2026', '')}` : '—'}</td>
              <td className="right money-cell">{money(p.before)}</td><td className="right money-cell">{money(p.during)}</td>
              <td className="right"><span title={p.reason ?? 'Complete before and during windows'} className={`uplift-chip ${p.uplift == null ? 'missing' : p.uplift >= 0 ? 'positive' : 'negative'}`}>{p.uplift == null ? 'N/A' : percent(p.uplift)}</span></td>
              <td><button className="inspect" onClick={() => setSelectedId(p.promo_id)} aria-label={`Inspect ${p.promo_id}`}>View →</button></td>
            </tr>)}
            {!filtered.length && <tr><td colSpan={7} className="empty">No promotions match these filters.</td></tr>}
          </tbody></table></div>
          <div className="table-foot"><span>Amounts in EUR · Uplift is (during − before) ÷ before</span><span>Click “View” for details</span></div>
        </section>
        <div className="side-column">
          <Detail promo={selection} />
          <section className="panel data-quality"><span className="eyebrow">DATA QUALITY</span><h2>Cleaned at import</h2><div className="quality-list">
            <div><strong>{report.quality.unquoted_comma_rows_repaired.toLocaleString()}</strong><span>CSV rows repaired</span></div>
            <div><strong>{report.quality.exact_duplicate_rows_removed}</strong><span>Exact duplicates removed</span></div>
            <div><strong>{report.quality.negative_adjustments_preserved}</strong><span>Negative corrections retained</span></div>
          </div><p>Unmeasurable promotions remain visible and have blank uplift values in the exported CSV.</p></section>
        </div>
      </div>
      <footer>Greentube take-home exercise · Fictional data · Observed uplift is not a causal estimate.</footer>
    </main>
  </div>;
}

export default App;
