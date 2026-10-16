import { useState } from "react";
import { api } from "../api/client";
import { Async, Badge, Card, Confirm, Empty, Field, Modal, statusTone, useToast } from "../components/ui";
import { useApi } from "../hooks/useApi";
import { useSubmit, useWells } from "../hooks/form";
import { fmt, label, pct, today } from "../utils/format";

function TargetForm({ t, wells, onClose, onSaved }: { t?: any; wells: any[]; onClose: () => void; onSaved: () => void }) {
  const end = new Date(); end.setDate(end.getDate() + 30);
  const [v, setV] = useState({ well_id: t?.well_id ?? wells[0]?.id ?? "", daily_target_oil: t?.daily_target_oil ?? "", start_date: t?.start_date ?? today(), end_date: t?.end_date ?? end.toISOString().slice(0, 10), notes: t?.notes ?? "" });
  const s = useSubmit(), toast = useToast();
  const set = (k: string) => (e: any) => setV({ ...v, [k]: e.target.value });
  const save = async () => { if (await s.run(() => (t ? api.put(`/targets/${t.id}`, v) : api.post("/targets", v)))) { toast(t ? "Target updated" : "Target created"); onSaved(); onClose(); } };
  return (
    <Modal title={t ? "Edit target" : "New production target"} onClose={onClose}>
      <div className="grid form">
        <Field id="tw" label="Well" error={s.fields.well_id}><select id="tw" value={v.well_id} onChange={set("well_id")}>{wells.map((w) => <option key={w.id} value={w.id}>{w.well_code}</option>)}</select></Field>
        <Field id="tv" label="Daily target (bbl/day)" error={s.fields.daily_target_oil}><input id="tv" type="number" min="0" step="any" value={v.daily_target_oil} onChange={set("daily_target_oil")} /></Field>
        <Field id="ts" label="Start date" error={s.fields.start_date}><input id="ts" type="date" value={v.start_date} onChange={set("start_date")} /></Field>
        <Field id="te" label="End date" error={s.fields.end_date}><input id="te" type="date" value={v.end_date} onChange={set("end_date")} /></Field>
      </div>
      <Field id="tn" label="Notes (optional)" error={s.fields.notes}><input id="tn" value={v.notes} onChange={set("notes")} /></Field>
      <p className="formerr" role="alert">{s.err}</p>
      <div className="row" style={{ justifyContent: "flex-end" }}><button className="btn ghost" onClick={onClose}>Cancel</button><button className="btn" disabled={s.busy} onClick={save}>{s.busy ? "Saving…" : "Save target"}</button></div>
    </Modal>
  );
}

export default function Targets() {
  const { data, loading, error, reload } = useApi<any[]>("/targets");
  const wells = useWells();
  const active = (wells.data ?? []).filter((w) => w.status !== "ARCHIVED");
  const [form, setForm] = useState<any>(null), [del, setDel] = useState<any>(null);
  const toast = useToast();
  return (
    <>
      <div className="bar"><div><h1>Production targets</h1><p className="muted">Status compares the average daily actual output (days with records) with the daily target. A well cannot have overlapping target periods.</p></div><button className="btn" disabled={!active.length} onClick={() => setForm({})}>New target</button></div>
      <Card>
        <Async loading={loading} error={error} reload={reload}>
          {data && data.length ? <div className="tw"><table><thead><tr><th>Well</th><th>Target (bbl/day)</th><th className="l">Period</th><th>Avg actual (bbl/day)</th><th>Achievement</th><th>Days</th><th className="l">Status</th><th></th></tr></thead>
            <tbody>{data.map((t) => <tr key={t.id}><td>{t.well_code}</td><td>{fmt(t.daily_target_oil)}</td><td className="l">{t.start_date} → {t.end_date}</td><td>{fmt(t.avg_daily_actual, 1)}</td><td>{pct(t.achievement_pct)}</td><td>{t.days_with_records}</td>
              <td className="l"><Badge tone={statusTone(t.status)}>{label(t.status)}</Badge></td><td><div className="row" style={{ justifyContent: "flex-end", flexWrap: "nowrap" }}><button className="btn ghost sm" onClick={() => setForm(t)}>Edit</button><button className="btn ghost sm" onClick={() => setDel(t)}>Delete</button></div></td></tr>)}</tbody></table></div>
            : <Empty action={active.length ? <button className="btn" onClick={() => setForm({})}>Create a target</button> : undefined}>{active.length ? "No targets yet." : "Add a well first, then set its production target."}</Empty>}
        </Async>
      </Card>
      {form && <TargetForm t={form.id ? form : undefined} wells={form.id ? wells.data ?? [] : active} onClose={() => setForm(null)} onSaved={reload} />}
      {del && <Confirm danger title="Delete target" message={<>Delete the {del.well_code} target for {del.start_date} → {del.end_date}?</>} confirmLabel="Delete target" onClose={() => setDel(null)}
        onConfirm={async () => { try { await api.del(`/targets/${del.id}`); toast("Target deleted"); setDel(null); reload(); } catch (e: any) { toast(e.message, "bad"); } }} />}
    </>
  );
}
