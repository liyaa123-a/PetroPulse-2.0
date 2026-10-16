import { Async, Card, Empty, FilterBar, Kpi, useFilters } from "../components/ui";
import { BarList, LineChart } from "../components/charts";
import { useApi } from "../hooks/useApi";
import { useWells } from "../hooks/form";
import { qs } from "../api/client";
import { fmt, label, pct, usd } from "../utils/format";

export default function Loss() {
  const [f, set] = useFilters();
  const wells = useWells();
  const { data: d, loading, error, reload } = useApi<any>("/analytics/loss" + qs({ from: f.from, to: f.to, well_id: f.well_id }));
  return (
    <>
      <div className="bar"><div><h1>Production loss analysis</h1><p className="muted">Shortfall = planned − actual, counting only records below plan.</p></div><FilterBar f={f} set={set} wells={wells.data ?? []} /></div>
      <Async loading={loading} error={error} reload={reload}>
        {d && (d.totals.record_count === 0 ? <Card><Empty>No records to analyse for these filters.</Empty></Card> : (
          <>
            <div className="grid kpis"><Kpi label="Positive shortfall (bbl)" value={fmt(d.totals.positive_shortfall)} tone="bad" /><Kpi label="Loss percentage" value={pct(d.totals.loss_pct)} tone="bad" /><Kpi label="Est. revenue loss" value={usd(d.totals.revenue_loss)} tone="bad" hint="Shortfall × recorded oil price" /><Kpi label="Downtime logged (h)" value={fmt(d.totals.downtime_hours, 1)} /></div>
            <div className="grid two mt">
              <Card title="Loss trend"><LineChart data={d.trend} series={[{ key: "positive_shortfall", label: "Shortfall", color: "var(--bad)" }]} /></Card>
              <Card title="Shortfall by well">{d.by_well.some((w: any) => w.positive_shortfall > 0) ? <BarList items={d.by_well.map((w: any) => ({ label: w.well_code, value: w.positive_shortfall }))} /> : <p className="ok">No shortfall in this range.</p>}
                <div className="tw mt"><table><thead><tr><th>Well</th><th>Loss %</th><th>Est. revenue loss</th></tr></thead><tbody>{d.by_well.map((w: any) => <tr key={w.well_id}><td>{w.well_code}</td><td>{pct(w.loss_pct)}</td><td>{usd(w.revenue_loss)}</td></tr>)}</tbody></table></div></Card>
            </div>
            <div className="grid two mt">
              <Card title="Largest single-day shortfalls"><div className="tw"><table><thead><tr><th>Date</th><th>Well</th><th>Shortfall (bbl)</th><th>Est. loss</th></tr></thead>
                <tbody>{d.top_days.map((r: any) => <tr key={r.id}><td>{r.production_date}</td><td>{r.well_code}</td><td>{fmt(r.positive_shortfall)}</td><td>{usd(r.revenue_loss)}</td></tr>)}</tbody></table></div></Card>
              <Card title="Shortfall by recorded cause">{d.by_category.length ? <div className="tw"><table><thead><tr><th>Cause</th><th>Days</th><th>Shortfall (bbl)</th><th>Est. loss</th></tr></thead>
                <tbody>{d.by_category.map((c: any) => <tr key={c.category}><td>{label(c.category)}</td><td>{c.days}</td><td>{fmt(c.positive_shortfall)}</td><td>{usd(c.revenue_loss)}</td></tr>)}</tbody></table></div> : <p className="muted">No causes were recorded on records in this range.</p>}
                <p className="muted mt">{d.note}</p></Card>
            </div>
          </>))}
      </Async>
    </>
  );
}
