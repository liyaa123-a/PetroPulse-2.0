import { Link, useParams } from "react-router-dom";
import { Async, Badge, Card, Empty, Kpi, statusTone } from "../components/ui";
import { LineChart } from "../components/charts";
import { useApi } from "../hooks/useApi";
import { achTone, fmt, label, pct, usd } from "../utils/format";

export default function WellDetail() {
  const { id } = useParams();
  const { data: w, loading, error, reload } = useApi<any>(`/wells/${id}`);
  return (
    <Async loading={loading} error={error} reload={reload}>
      {w && (
        <>
          <div className="bar"><div><h1>{w.well_code} · {w.well_name}</h1><p className="muted">{w.field_name} · {label(w.well_type)} · <Badge tone={statusTone(w.status)}>{label(w.status)}</Badge></p></div><Link className="btn ghost" to="/wells">Back to wells</Link></div>
          {w.description && <p style={{ marginBottom: 12 }}>{w.description}</p>}
          <div className="grid kpis">
            <Kpi label="Records" value={w.summary.record_count} /><Kpi label="Actual (bbl)" value={fmt(w.summary.actual_oil)} /><Kpi label="Planned (bbl)" value={fmt(w.summary.planned_oil)} />
            <Kpi label="Achievement" value={pct(w.summary.achievement_pct)} tone={achTone(w.summary.achievement_pct)} /><Kpi label="Est. revenue" value={usd(w.summary.revenue)} /><Kpi label="Est. revenue loss" value={usd(w.summary.revenue_loss)} tone={w.summary.revenue_loss ? "bad" : ""} />
          </div>
          <Card title="Production history" className="mt">
            {w.history.length ? <>
              <LineChart data={[...w.history].reverse()} xKey="production_date" series={[{ key: "planned_oil", label: "Planned", color: "var(--blue)", dashed: true }, { key: "actual_oil", label: "Actual", color: "var(--teal)" }]} />
              <div className="tw mt"><table><thead><tr><th>Date</th><th>Planned (bbl)</th><th>Actual (bbl)</th><th>Achievement</th><th>Revenue loss</th></tr></thead>
                <tbody>{w.history.map((r: any) => <tr key={r.id}><td>{r.production_date}</td><td>{fmt(r.planned_oil)}</td><td>{fmt(r.actual_oil)}</td><td className={achTone(r.achievement_pct)}>{pct(r.achievement_pct)}</td><td>{usd(r.revenue_loss)}</td></tr>)}</tbody></table></div></>
              : <Empty action={<Link className="btn" to="/production">Add a record</Link>}>No production recorded for this well yet.</Empty>}
          </Card>
        </>
      )}
    </Async>
  );
}
