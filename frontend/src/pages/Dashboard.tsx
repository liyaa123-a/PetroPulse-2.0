import { Link } from "react-router-dom";
import { Async, Card, Empty, FilterBar, Kpi, useFilters } from "../components/ui";
import { LineChart } from "../components/charts";
import { useApi } from "../hooks/useApi";
import { qs } from "../api/client";
import { achTone, fmt, pct, usd } from "../utils/format";

export default function Dashboard() {
  const [f, set] = useFilters();
  const { data: d, loading, error, reload } = useApi<any>("/dashboard" + qs({ from: f.from, to: f.to }));
  return (
    <>
      <div className="bar"><div><h1>Executive dashboard</h1><p className="muted">All values are calculated from your stored production records.</p></div><FilterBar f={f} set={set} /></div>
      <Async loading={loading} error={error} reload={reload}>
        {d && d.totals.record_count === 0 ? (
          <Card><Empty action={<div className="row" style={{ justifyContent: "center" }}><Link className="btn" to="/wells">Add a well</Link><Link className="btn ghost" to="/production">Add a production record</Link></div>}>
            {f.from || f.to ? "No records in this date range." : "No production data yet. Add a well, then record its first day of production."}</Empty></Card>
        ) : d && (
          <>
            <div className="grid kpis">
              <Kpi label="Actual oil (bbl)" value={fmt(d.totals.actual_oil)} /><Kpi label="Planned oil (bbl)" value={fmt(d.totals.planned_oil)} />
              <Kpi label="Production achievement" value={pct(d.totals.achievement_pct)} tone={achTone(d.totals.achievement_pct, d.achievement_threshold)} />
              <Kpi label="Positive shortfall (bbl)" value={fmt(d.totals.positive_shortfall)} tone={d.totals.positive_shortfall ? "bad" : ""} hint="Sum of days below plan; overproduction does not offset it" />
              <Kpi label="Est. revenue" value={usd(d.totals.revenue)} /><Kpi label="Est. operating profit" value={usd(d.totals.operating_profit)} tone={d.totals.operating_profit < 0 ? "bad" : ""} />
              <Kpi label="Est. revenue loss" value={usd(d.totals.revenue_loss)} tone={d.totals.revenue_loss ? "bad" : ""} hint="Positive shortfall × recorded oil price (an estimate)" />
            </div>
            <div className="grid two mt">
              <Card title="Planned vs actual production"><LineChart data={d.trend} series={[{ key: "planned_oil", label: "Planned", color: "var(--blue)", dashed: true }, { key: "actual_oil", label: "Actual", color: "var(--teal)" }]} /></Card>
              <Card title="Well performance"><div className="tw"><table><thead><tr><th>Well</th><th>Actual (bbl)</th><th>Planned (bbl)</th><th>Achievement</th></tr></thead>
                <tbody>{d.by_well.map((w: any) => <tr key={w.well_id}><td><Link to={`/wells/${w.well_id}`}>{w.well_code}</Link></td><td>{fmt(w.actual_oil)}</td><td>{fmt(w.planned_oil)}</td><td className={achTone(w.achievement_pct, d.achievement_threshold)}>{pct(w.achievement_pct)}</td></tr>)}</tbody></table></div></Card>
            </div>
            <div className="grid two mt">
              <Card title="Needs attention" actions={<Link to="/alerts">{d.alerts.new} new alert{d.alerts.new === 1 ? "" : "s"}</Link>}>
                {d.underperforming.length ? d.underperforming.map((w: any) => <p key={w.well_id} style={{ margin: "6px 0" }}><b>{w.well_code}</b> is at <span className="bad">{pct(w.achievement_pct)}</span> of plan – {fmt(w.positive_shortfall)} bbl short ({usd(w.revenue_loss)} est. loss). <span className="muted">Rule: below {d.achievement_threshold}%.</span></p>)
                  : <p className="ok">All wells in range are at or above {d.achievement_threshold}% of plan.</p>}
              </Card>
              <Card title="Recent records" actions={<Link to="/production">View all</Link>}><div className="tw"><table><thead><tr><th>Date</th><th>Well</th><th>Actual</th><th>Planned</th></tr></thead>
                <tbody>{d.recent.map((r: any) => <tr key={r.id}><td>{r.production_date}</td><td>{r.well_code}</td><td>{fmt(r.actual_oil)}</td><td>{fmt(r.planned_oil)}</td></tr>)}</tbody></table></div></Card>
            </div>
            <Card title="Quick actions" className="mt"><div className="row"><Link className="btn" to="/production">Add record</Link><Link className="btn ghost" to="/wells">Manage wells</Link><Link className="btn ghost" to="/loss">Open loss analysis</Link><Link className="btn ghost" to="/analytics">Reports</Link></div></Card>
          </>
        )}
      </Async>
    </>
  );
}
