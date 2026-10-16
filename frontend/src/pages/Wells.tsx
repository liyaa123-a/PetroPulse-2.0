import { useState } from "react";
import { Link } from "react-router-dom";
import { api, qs } from "../api/client";
import { Async, Badge, Card, Confirm, Empty, Field, Modal, Pager, statusTone, useFilters, useToast } from "../components/ui";
import { useApi } from "../hooks/useApi";
import { useSubmit } from "../hooks/form";
import { WELL_STATUSES, WELL_TYPES } from "../types";
import { label } from "../utils/format";

function WellForm({ well, onClose, onSaved }: { well?: any; onClose: () => void; onSaved: () => void }) {
  const [v, setV] = useState({ well_code: well?.well_code ?? "", well_name: well?.well_name ?? "", field_name: well?.field_name ?? "", well_type: well?.well_type ?? "VERTICAL", description: well?.description ?? "" });
  const s = useSubmit(), toast = useToast();
  const set = (k: string) => (e: any) => setV({ ...v, [k]: e.target.value });
  const save = async () => { if (await s.run(() => (well ? api.put(`/wells/${well.id}`, v) : api.post("/wells", v)))) { toast(well ? "Well updated" : "Well added"); onSaved(); onClose(); } };
  return (
    <Modal title={well ? `Edit ${well.well_code}` : "Add a well"} onClose={onClose}>
      <div className="grid form">
        <Field id="wc" label="Well code" error={s.fields.well_code}><input id="wc" value={v.well_code} onChange={set("well_code")} maxLength={20} placeholder="ALPHA-01" /></Field>
        <Field id="wn" label="Name" error={s.fields.well_name}><input id="wn" value={v.well_name} onChange={set("well_name")} /></Field>
        <Field id="wf" label="Field / location" error={s.fields.field_name}><input id="wf" value={v.field_name} onChange={set("field_name")} /></Field>
        <Field id="wt" label="Type" error={s.fields.well_type}><select id="wt" value={v.well_type} onChange={set("well_type")}>{WELL_TYPES.map((t) => <option key={t} value={t}>{label(t)}</option>)}</select></Field>
      </div>
      <Field id="wd" label="Description (optional)" error={s.fields.description}><textarea id="wd" rows={2} value={v.description} onChange={set("description")} /></Field>
      <p className="formerr" role="alert">{s.err}</p>
      <div className="row" style={{ justifyContent: "flex-end" }}><button className="btn ghost" onClick={onClose}>Cancel</button><button className="btn" disabled={s.busy} onClick={save}>{s.busy ? "Saving…" : "Save well"}</button></div>
    </Modal>
  );
}

export default function Wells() {
  const [f, set] = useFilters({ q: "", status: "" });
  const { data, meta, loading, error, reload } = useApi<any[]>("/wells" + qs({ q: f.q, status: f.status, page: f.page, page_size: 10, include_archived: f.status ? "" : f.showArchived ? "1" : "" }));
  const [form, setForm] = useState<any>(null), [archive, setArchive] = useState<any>(null);
  const toast = useToast();
  const changeStatus = async (w: any, status: string) => { try { await api.patch(`/wells/${w.id}/status`, { status }); toast(`${w.well_code} set to ${label(status)}`); reload(); } catch (e: any) { toast(e.message, "bad"); } };
  return (
    <>
      <div className="bar"><div><h1>Wells</h1><p className="muted">Archived wells keep all of their production history.</p></div><button className="btn" onClick={() => setForm({})}>Add well</button></div>
      <Card>
        <div className="row noprint" style={{ marginBottom: 10 }}>
          <div><label htmlFor="q">Search</label><input id="q" placeholder="Code, name or field" value={f.q} onChange={(e) => set("q", e.target.value)} /></div>
          <div><label htmlFor="st">Status</label><select id="st" value={f.status} onChange={(e) => set("status", e.target.value)}><option value="">Not archived</option>{WELL_STATUSES.map((s) => <option key={s} value={s}>{label(s)}</option>)}</select></div>
        </div>
        <Async loading={loading} error={error} reload={reload}>
          {data && data.length ? (
            <><div className="tw"><table><thead><tr><th>Code</th><th className="l">Name</th><th className="l">Field</th><th className="l">Type</th><th className="l">Status</th><th>Records</th><th></th></tr></thead>
              <tbody>{data.map((w) => <tr key={w.id}><td><Link to={`/wells/${w.id}`}>{w.well_code}</Link></td><td className="l">{w.well_name}</td><td className="l">{w.field_name}</td><td className="l">{label(w.well_type)}</td>
                <td className="l"><Badge tone={statusTone(w.status)}>{label(w.status)}</Badge></td><td>{w.record_count}</td>
                <td><div className="row" style={{ justifyContent: "flex-end" }}>
                  <label className="sr" htmlFor={`s${w.id}`} style={{ display: "none" }}>Status</label>
                  <select id={`s${w.id}`} style={{ width: "auto" }} value={w.status} onChange={(e) => e.target.value === "ARCHIVED" ? setArchive(w) : changeStatus(w, e.target.value)}>{WELL_STATUSES.map((s) => <option key={s} value={s}>{label(s)}</option>)}</select>
                  <button className="btn ghost sm" onClick={() => setForm(w)}>Edit</button></div></td></tr>)}</tbody></table></div>
              <Pager page={f.page} size={10} total={meta?.total ?? 0} onPage={(p) => set("page", p)} /></>
          ) : <Empty action={<button className="btn" onClick={() => setForm({})}>Add your first well</button>}>{f.q || f.status ? "No wells match these filters." : "No wells yet."}</Empty>}
        </Async>
      </Card>
      {form && <WellForm well={form.id ? form : undefined} onClose={() => setForm(null)} onSaved={reload} />}
      {archive && <Confirm title="Archive well" message={<>Archive <b>{archive.well_code}</b>? Its {archive.record_count} production records are kept, but new records cannot be added until you reactivate it.</>} confirmLabel="Archive well"
        onClose={() => setArchive(null)} onConfirm={async () => { await changeStatus(archive, "ARCHIVED"); setArchive(null); }} />}
    </>
  );
}
