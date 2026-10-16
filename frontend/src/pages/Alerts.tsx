import { api, qs } from "../api/client";
import { Async, Badge, Card, Empty, Pager, statusTone, useFilters, useToast } from "../components/ui";
import { useApi } from "../hooks/useApi";
import { label } from "../utils/format";

export default function Alerts() {
  const [f, set] = useFilters({ status: "", severity: "" });
  const { data, meta, loading, error, reload } = useApi<any[]>("/alerts" + qs({ status: f.status, severity: f.severity, page: f.page, page_size: 10 }));
  const toast = useToast();
  const evaluate = async () => { try { const r = await api.post("/alerts/evaluate"); toast(r.data.created ? `${r.data.created} new alert(s) raised` : "No new alerts"); reload(); } catch (e: any) { toast(e.message, "bad"); } };
  const mark = async (id: number, status: string) => { try { await api.patch(`/alerts/${id}`, { status }); reload(); } catch (e: any) { toast(e.message, "bad"); } };
  return (
    <>
      <div className="bar"><div><h1>Alerts</h1><p className="muted">Rule-based and transparent – every alert shows the rule that fired. Thresholds are set in Settings.</p></div><button className="btn" onClick={evaluate}>Re-check now</button></div>
      <Card>
        <div className="row noprint" style={{ marginBottom: 10 }}>
          <div><label htmlFor="as">Status</label><select id="as" value={f.status} onChange={(e) => set("status", e.target.value)}><option value="">All</option><option value="NEW">New</option><option value="ACKNOWLEDGED">Acknowledged</option><option value="RESOLVED">Resolved</option></select></div>
          <div><label htmlFor="av">Severity</label><select id="av" value={f.severity} onChange={(e) => set("severity", e.target.value)}><option value="">All</option><option value="CRITICAL">Critical</option><option value="WARNING">Warning</option><option value="INFO">Info</option></select></div>
        </div>
        <Async loading={loading} error={error} reload={reload}>
          {data && data.length ? <>{data.map((a) => (
            <div key={a.id} className={`alert ${a.severity}`}>
              <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
                <div><Badge tone={statusTone(a.severity)}>{label(a.severity)}</Badge> <Badge tone={statusTone(a.status)}>{label(a.status)}</Badge> <b>{a.message}</b></div>
                <div className="row">{a.status === "NEW" && <button className="btn ghost sm" onClick={() => mark(a.id, "ACKNOWLEDGED")}>Acknowledge</button>}{a.status !== "RESOLVED" && <button className="btn ghost sm" onClick={() => mark(a.id, "RESOLVED")}>Resolve</button>}{a.status === "RESOLVED" && <button className="btn ghost sm" onClick={() => mark(a.id, "NEW")}>Reopen</button>}</div>
              </div>
              <p className="muted">Rule {a.rule_code} · {a.alert_date}{a.well_code ? ` · ${a.well_code}` : ""} — {a.trigger_reason}</p>
            </div>))}<Pager page={f.page} size={10} total={meta?.total ?? 0} onPage={(p) => set("page", p)} /></>
            : <Empty>{f.status || f.severity ? "No alerts match these filters." : "No alerts. They appear when a record breaks one of your rules."}</Empty>}
        </Async>
      </Card>
      <Card title="How alerts work" className="mt"><ul style={{ margin: 0, paddingLeft: 18 }}>
        <li><b>Low achievement:</b> a record's achievement is below your threshold (critical below 50%).</li><li><b>High downtime:</b> a record's downtime hours exceed your threshold.</li>
        <li><b>Repeated miss:</b> a well's last N records were all below plan.</li><li><b>Missing records:</b> an active well has had no record for N days.</li></ul>
        <p className="muted mt">No artificial intelligence or prediction is used – only these fixed rules applied to your data.</p></Card>
    </>
  );
}
