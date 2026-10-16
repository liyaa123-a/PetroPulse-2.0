import { FormEvent, useState } from "react";
import { useAuth } from "../hooks/auth";
import { useSubmit } from "../hooks/form";
import { Field } from "../components/ui";

export default function AuthPage() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [v, setV] = useState({ email: "", full_name: "", password: "" });
  const [show, setShow] = useState(false);
  const s = useSubmit();
  const reg = mode === "register";
  const submit = (e: FormEvent) => { e.preventDefault(); void s.run(() => (reg ? register(v.email, v.full_name, v.password) : login(v.email, v.password))); };
  const set = (k: string) => (e: any) => setV({ ...v, [k]: e.target.value });
  return (
    <div className="auth">
      <section className="hero">
        <div className="brand">PetroPulse 2.0</div>
        <h1>See what your wells produced against plan, and what the gap cost.</h1>
        <ul>
          <li>Planned vs actual oil production by well and day</li>
          <li>Estimated revenue, operating profit and revenue loss</li>
          <li>Clear, rule-based alerts you can read and configure</li>
          <li>Every account keeps its own wells and records in the database</li>
        </ul>
      </section>
      <form className="authform" onSubmit={submit} noValidate>
        <h1>{reg ? "Create an account" : "Sign in"}</h1>
        {reg && <Field id="name" label="Full name" error={s.fields.full_name}><input id="name" autoComplete="name" value={v.full_name} onChange={set("full_name")} required /></Field>}
        <Field id="email" label="Email" error={s.fields.email}><input id="email" type="email" autoComplete="email" value={v.email} onChange={set("email")} required /></Field>
        <Field id="pw" label={reg ? "Password (8+ characters, letters and a number)" : "Password"} error={s.fields.password}>
          <div className="pw"><input id="pw" type={show ? "text" : "password"} autoComplete={reg ? "new-password" : "current-password"} value={v.password} onChange={set("password")} required />
            <button type="button" className="btn ghost sm" onClick={() => setShow(!show)} aria-pressed={show}>{show ? "Hide" : "Show"}</button></div>
        </Field>
        <p className="formerr" role="alert">{s.err}</p>
        <button className="btn" disabled={s.busy}>{s.busy ? "Please wait…" : reg ? "Create account" : "Sign in"}</button>
        <button type="button" className="btn ghost" onClick={() => { setMode(reg ? "login" : "register"); }}>{reg ? "I already have an account" : "Create a new account"}</button>
        <p className="muted">The server may take ~30 seconds to wake on the first request when hosted on a free plan.</p>
      </form>
    </div>
  );
}
