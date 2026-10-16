import { useState } from "react";
import { Async, Card, Empty, FilterBar, Kpi, useFilters, useToast } from "../components/ui";
import { LineChart } from "../components/charts";
import { useApi } from "../hooks/useApi";
import { useWells } from "../hooks/form";
import { api, qs } from "../api/client";
import { achTone, fmt, pct, usd } from "../utils/format";

export default function Analytics() {
  const [f, set] = useFilters();
  const [period, setPeriod] = useState("day");
  const wells = useWells(), toast = useToast();
  const q = { from: f.from, to: f.to, well_id: f.well_id, period };
  const { data: d, loading, error, reload } = useApi<any>("/analytics/summary" + qs(q));
  return (
    <>
      <div className="bar"><div><h1>Analytics &amp; reports</h1><p className="muted">Same metric definitions as the dashboard and loss analysis.</p></div>
        <div className="row noprint"><button className="btn ghost" onClick={() => api.download("/analytics/export.csv" + qs(q), `petropulse_${period}_summary.csv`).then(() => toast("CSV exported"), (e) => toast(e.message, "bad"))}>Export CSV</button><button className="btn" onClick={() => window.print()}>Print report</button></div></div>
      <Card><FilterBar f={f} set={set} wells={wells.data ?? []} extra={<div><label htmlFor="per">Group by</label><select id="per" value={period} onChange={(e) => setPeriod(e.target.value)}><option value="day">Day</option><option value="week">Week (Mon start)</option><option value="month">Month</option></select></div>} /></Card>
      <Async loading={loading} error={error} reload={reload}>
        {d && (d.totals.record_count === 0 ? <Card className="mt"><Empty>No records for these filters.</Empty></Card> : (
          <>
            <div className="grid kpis mt"><Kpi label="Revenue" value={usd(d.totals.revenue)} /><Kpi label="Operating cost" value={usd(d.totals.operating_cost)} /><Kpi label="Operating profit" value={usd(d.totals.operating_profit)} tone={d.totals.operating_profit < 0 ? "bad" : ""} /><Kpi label="Achievement" value={pct(d.totals.achievement_pct)} tone={achTone(d.totals.achievement_pct)} /><Kpi label="Revenue loss" value={usd(d.totals.revenue_loss)} tone="bad" /></div>
            <Card title={`Planned vs actual by ${period}`} className="mt"><LineChart data={d.rows} xKey="period" series={[{ key: "planned_oil", label: "Planned", color: "var(--blue)", dashed: true }, { key: "actual_oil", label: "Actual", color: "var(--teal)" }]} /></Card>
            <Card title={`Summary by ${period}`} className="mt"><div className="tw"><table><thead><tr><th>{period[0].toUpperCase() + period.slice(1)}</th><th>Planned (bbl)</th><th>Actual (bbl)</th><th>Achv.</th><th>Shortfall (bbl)</th><th>Revenue</th><th>Cost</th><th>Profit</th><th>Rev. loss</th></tr></thead>
              <tbody>{d.rows.map((r: any) => <tr key={r.period}><td>{r.period}</td><td>{fmt(r.planned_oil)}</td><td>{fmt(r.actual_oil)}</td><td className={achTone(r.achievement_pct)}>{pct(r.achievement_pct)}</td><td>{fmt(r.positive_shortfall)}</td><td>{usd(r.revenue)}</td><td>{usd(r.operating_cost)}</td><td>{usd(r.operating_profit)}</td><td>{usd(r.revenue_loss)}</td></tr>)}</tbody></table></div></Card>
            <Card title="Well comparison" className="mt"><div className="tw"><table><thead><tr><th>Well</th><th>Planned (bbl)</th><th>Actual (bbl)</th><th>Achv.</th><th>Revenue</th><th>Profit</th><th>Rev. loss</th></tr></thead>
              <tbody>{d.by_well.map((w: any) => <tr key={w.well_id}><td>{w.well_code}</td><td>{fmt(w.planned_oil)}</td><td>{fmt(w.actual_oil)}</td><td className={achTone(w.achievement_pct)}>{pct(w.achievement_pct)}</td><td>{usd(w.revenue)}</td><td>{usd(w.operating_profit)}</td><td>{usd(w.revenue_loss)}</td></tr>)}</tbody></table></div></Card>
          </>))}
      </Async>
    </>
  );
}
