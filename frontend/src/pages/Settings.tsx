import { FormEvent, useEffect, useState } from "react";
import { api, setToken } from "../api/client";
import { Async, Card, Field, Modal, useToast } from "../components/ui";
import { useAuth } from "../hooks/auth";
import { useApi } from "../hooks/useApi";
import { useSubmit } from "../hooks/form";

export default function Settings() {
  const { data, loading, error, reload } = useApi<any>("/settings");
  const { refresh, logout } = useAuth();
  const toast = useToast();
  const [v, setV] = useState<any>(null), [pw, setPw] = useState({ current_password: "", new_password: "" }), [del, setDel] = useState<any>(null);
  const prof = useSubmit(), pass = useSubmit(), rm = useSubmit();
  useEffect(() => { if (data) setV({ full_name: data.profile.full_name, ...data.thresholds }); }, [data]);
  const setN = (k: string) => (e: any) => setV({ ...v, [k]: e.target.value });
  const saveProfile = async (e: FormEvent) => { e.preventDefault(); if (await prof.run(() => api.put("/settings", v))) { toast("Settings saved"); reload(); void refresh(); } };
  const savePw = async (e: FormEvent) => { e.preventDefault(); if (await pass.run(async () => { const r = await api.post("/auth/password", pw); setToken(r.data.token); })) { toast("Password changed"); setPw({ current_password: "", new_password: "" }); } };
  const num = (id: string, lab: string, k: string, step = "any") => <Field id={id} label={lab} error={prof.fields[k]}><input id={id} type="number" step={step} value={v[k]} onChange={setN(k)} /></Field>;
  return (
    <>
      <div className="bar"><div><h1>Profile &amp; settings</h1></div></div>
      <Async loading={loading} error={error} reload={reload}>
        {data && v && (
          <div className="grid two">
            <Card title="Profile and alert thresholds">
              <form onSubmit={saveProfile}>
                <p className="muted" style={{ marginBottom: 8 }}>Signed in as {data.profile.email}</p>
                <Field id="fn" label="Full name" error={prof.fields.full_name}><input id="fn" value={v.full_name} onChange={setN("full_name")} /></Field>
                <div className="grid form">{num("t1", "Alert below achievement (%)", "achievement_threshold")}{num("t2", "Alert above downtime (hours)", "downtime_threshold_hours")}{num("t3", "Repeated-miss count (records)", "repeat_miss_count", "1")}{num("t4", "Missing-record days", "missing_record_days", "1")}{num("t5", "Target at-risk from (%)", "target_at_risk_pct")}</div>
                <p className="formerr" role="alert">{prof.err}</p><button className="btn" disabled={prof.busy}>{prof.busy ? "Saving…" : "Save settings"}</button>
              </form>
            </Card>
            <div className="grid">
              <Card title="Change password"><form onSubmit={savePw}>
                <Field id="cp" label="Current password" error={pass.fields.current_password}><input id="cp" type="password" autoComplete="current-password" value={pw.current_password} onChange={(e) => setPw({ ...pw, current_password: e.target.value })} /></Field>
                <Field id="np" label="New password (8+ characters, letters and a number)" error={pass.fields.new_password}><input id="np" type="password" autoComplete="new-password" value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} /></Field>
                <p className="formerr" role="alert">{pass.err}</p><button className="btn" disabled={pass.busy}>Change password</button></form></Card>
              <Card title="Measurement units"><table><tbody>{Object.entries(data.units).map(([k, val]) => <tr key={k}><td className="l muted">{k.replace("_", " ")}</td><td className="l">{String(val)}</td></tr>)}</tbody></table></Card>
              <Card title="Your data"><p className="muted" style={{ marginBottom: 10 }}>Download everything stored for your account, or delete it permanently.</p>
                <div className="row"><button className="btn ghost" onClick={() => api.download("/settings/export", "petropulse_export.json").then(() => toast("Export downloaded"), (e) => toast(e.message, "bad"))}>Export my data (JSON)</button><button className="btn danger" onClick={() => setDel({ password: "", confirm: "" })}>Delete account…</button></div></Card>
            </div>
          </div>
        )}
      </Async>
      {del && <Modal title="Delete account" onClose={() => setDel(null)}>
        <p>This permanently deletes your account, wells, production records, targets and alerts. It cannot be undone.</p>
        <div className="mt"><Field id="dp" label="Your password" error={rm.fields.password}><input id="dp" type="password" value={del.password} onChange={(e) => setDel({ ...del, password: e.target.value })} /></Field>
          <Field id="dc" label="Type DELETE to confirm" error={rm.fields.confirm}><input id="dc" value={del.confirm} onChange={(e) => setDel({ ...del, confirm: e.target.value })} /></Field></div>
        <p className="formerr" role="alert">{rm.err}</p>
        <div className="row" style={{ justifyContent: "flex-end" }}><button className="btn ghost" onClick={() => setDel(null)}>Cancel</button>
          <button className="btn danger" disabled={rm.busy || del.confirm !== "DELETE"} onClick={async () => { if (await rm.run(() => api.del("/account", del))) { toast("Account deleted"); await logout(); } }}>Delete everything</button></div>
      </Modal>}
    </>
  );
}
