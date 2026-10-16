import { useState } from "react";
import { api, qs } from "../api/client";
import { Async, Card, Confirm, Empty, Field, FilterBar, Modal, Pager, useFilters, useToast } from "../components/ui";
import { useApi } from "../hooks/useApi";
import { useSubmit, useWells } from "../hooks/form";
import { LOSS_CATEGORIES } from "../types";
import { achTone, fmt, label, pct, today, usd } from "../utils/format";

function RecordForm({ rec, wells, onClose, onSaved }: { rec?: any; wells: any[]; onClose: () => void; onSaved: () => void }) {
  const usable = wells.filter((w) => w.status !== "ARCHIVED" || w.id === rec?.well_id);
  const [v, setV] = useState({ well_id: rec?.well_id ?? usable[0]?.id ?? "", production_date: rec?.production_date ?? today(), planned_oil: rec?.planned_oil ?? "", actual_oil: rec?.actual_oil ?? "",
    oil_price: rec?.oil_price ?? "70", operating_cost: rec?.operating_cost ?? "0", downtime_hours: rec?.downtime_hours ?? "0", loss_category: rec?.loss_category ?? "", notes: rec?.notes ?? "" });
  const s = useSubmit(), toast = useToast();
  const set = (k: string) => (e: any) => setV({ ...v, [k]: e.target.value });
  const save = async () => { if (await s.run(() => (rec ? api.put(`/production/${rec.id}`, v) : api.post("/production", v)))) { toast(rec ? "Record updated" : "Record saved"); onSaved(); onClose(); } };
  const num = (id: string, lab: string, k: keyof typeof v, step = "any") => <Field id={id} label={lab} error={s.fields[k]}><input id={id} type="number" min="0" step={step} value={v[k]} onChange={set(k)} /></Field>;
  return (
    <Modal title={rec ? "Edit production record" : "Add production record"} onClose={onClose}>
      <div className="grid form">
        <Field id="rw" label="Well" error={s.fields.well_id}><select id="rw" value={v.well_id} onChange={set("well_id")}>{usable.map((w) => <option key={w.id} value={w.id}>{w.well_code} – {w.well_name}</option>)}</select></Field>
        <Field id="rd" label="Date" error={s.fields.production_date}><input id="rd" type="date" value={v.production_date} onChange={set("production_date")} /></Field>
        {num("rp", "Planned oil (bbl)", "planned_oil")}{num("ra", "Actual oil (bbl)", "actual_oil")}{num("rpr", "Oil price (USD/bbl)", "oil_price")}{num("rc", "Operating cost (USD)", "operating_cost")}{num("rdt", "Downtime (hours)", "downtime_hours")}
        <Field id="rl" label="Recorded loss cause (optional)" error={s.fields.loss_category}><select id="rl" value={v.loss_category} onChange={set("loss_category")}><option value="">None recorded</option>{LOSS_CATEGORIES.map((c) => <option key={c} value={c}>{label(c)}</option>)}</select></Field>
      </div>
      <Field id="rn" label="Notes (optional)" error={s.fields.notes}><textarea id="rn" rows={2} value={v.notes} onChange={set("notes")} /></Field>
      <p className="formerr" role="alert">{s.err}</p>
      <div className="row" style={{ justifyContent: "flex-end" }}><button className="btn ghost" onClick={onClose}>Cancel</button><button className="btn" disabled={s.busy || !usable.length} onClick={save}>{s.busy ? "Saving…" : "Save record"}</button></div>
    </Modal>
  );
}

export default function Records() {
  const [f, set] = useFilters({ q: "", sort: "production_date", dir: "desc" });
  const wells = useWells();
  const query = { q: f.q, well_id: f.well_id, from: f.from, to: f.to, loss_category: f.loss_category };
  const { data, meta, loading, error, reload } = useApi<any[]>("/production" + qs({ ...query, sort: f.sort, dir: f.dir, page: f.page, page_size: 10 }));
  const [form, setForm] = useState<any>(null), [view, setView] = useState<any>(null), [del, setDel] = useState<any>(null);
  const toast = useToast();
  const sort = (k: string) => { set("dir", f.sort === k && f.dir === "desc" ? "asc" : "desc"); set("sort", k); };
  const Th = ({ k, children }: { k: string; children: string }) => <th className="sort" tabIndex={0} aria-sort={f.sort === k ? (f.dir === "asc" ? "ascending" : "descending") : "none"} onClick={() => sort(k)} onKeyDown={(e) => e.key === "Enter" && sort(k)}>{children}{f.sort === k ? (f.dir === "asc" ? " ▲" : " ▼") : ""}</th>;
  return (
    <>
      <div className="bar"><div><h1>Production records</h1><p className="muted">Oil in barrels (bbl) · price in USD per bbl · cost in USD · downtime in hours</p></div>
        <div className="row"><button className="btn ghost" onClick={() => api.download("/production/export.csv" + qs(query), "petropulse_production.csv").then(() => toast("CSV exported"), (e) => toast(e.message, "bad"))}>Export CSV</button>
          <button className="btn" disabled={!wells.data?.length} onClick={() => setForm({})}>Add record</button></div></div>
      <Card>
        <FilterBar f={f} set={set} wells={wells.data ?? []} extra={<>
          <div><label htmlFor="q">Search</label><input id="q" placeholder="Well or notes" value={f.q} onChange={(e) => set("q", e.target.value)} /></div>
          <div><label htmlFor="lc">Loss cause</label><select id="lc" value={f.loss_category ?? ""} onChange={(e) => set("loss_category", e.target.value)}><option value="">Any</option>{LOSS_CATEGORIES.map((c) => <option key={c} value={c}>{label(c)}</option>)}</select></div></>} />
        <div style={{ height: 10 }} />
        <Async loading={loading} error={error} reload={reload}>
          {data && data.length ? <>
            <div className="tw"><table><thead><tr><Th k="production_date">Date</Th><Th k="well">Well</Th><Th k="planned_oil">Planned</Th><Th k="actual_oil">Actual</Th><th>Achv.</th><Th k="shortfall">Shortfall</Th><th>Revenue</th><th>Rev. loss</th><th></th></tr></thead>
              <tbody>{data.map((r) => <tr key={r.id}><td>{r.production_date}</td><td className="l">{r.well_code}</td><td>{fmt(r.planned_oil)}</td><td>{fmt(r.actual_oil)}</td><td className={achTone(r.achievement_pct)}>{pct(r.achievement_pct)}</td><td>{fmt(r.shortfall)}</td><td>{usd(r.revenue)}</td><td>{usd(r.revenue_loss)}</td>
                <td><div className="row" style={{ justifyContent: "flex-end", flexWrap: "nowrap" }}><button className="btn ghost sm" onClick={() => setView(r)}>View</button><button className="btn ghost sm" onClick={() => setForm(r)}>Edit</button><button className="btn ghost sm" onClick={() => setDel(r)}>Delete</button></div></td></tr>)}</tbody></table></div>
            <Pager page={f.page} size={10} total={meta?.total ?? 0} onPage={(p) => set("page", p)} /></>
            : <Empty action={wells.data?.length ? <button className="btn" onClick={() => setForm({})}>Add a record</button> : undefined}>{wells.data?.length ? "No records match these filters." : "Add a well first, then record its production."}</Empty>}
        </Async>
      </Card>
      {form && <RecordForm rec={form.id ? form : undefined} wells={wells.data ?? []} onClose={() => setForm(null)} onSaved={reload} />}
      {view && <Modal title={`${view.well_code} · ${view.production_date}`} onClose={() => setView(null)}>
        <table><tbody>{([["Planned oil", `${fmt(view.planned_oil, 2)} bbl`], ["Actual oil", `${fmt(view.actual_oil, 2)} bbl`], ["Achievement", pct(view.achievement_pct)], ["Shortfall", `${fmt(view.shortfall, 2)} bbl`], ["Oil price", `$${fmt(view.oil_price, 2)}/bbl`],
          ["Revenue", usd(view.revenue)], ["Operating cost", usd(view.operating_cost)], ["Operating profit", usd(view.operating_profit)], ["Revenue loss", usd(view.revenue_loss)], ["Downtime", `${fmt(view.downtime_hours, 1)} h`], ["Recorded cause", label(view.loss_category)], ["Notes", view.notes ?? "–"]] as [string, string][]).map(([k, val]) => <tr key={k}><td className="l muted">{k}</td><td>{val}</td></tr>)}</tbody></table></Modal>}
      {del && <Confirm danger title="Delete record" message={<>Delete the record for <b>{del.well_code}</b> on <b>{del.production_date}</b>? This cannot be undone.</>} confirmLabel="Delete record" onClose={() => setDel(null)}
        onConfirm={async () => { try { await api.del(`/production/${del.id}`); toast("Record deleted"); setDel(null); reload(); } catch (e: any) { toast(e.message, "bad"); } }} />}
    </>
  );
}
