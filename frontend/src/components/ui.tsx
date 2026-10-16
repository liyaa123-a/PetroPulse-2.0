import { createContext, ReactNode, useCallback, useContext, useEffect, useRef, useState } from "react";

/* ---- toasts ---- */
const ToastCtx = createContext<(m: string, kind?: "ok" | "bad") => void>(() => {});
export const useToast = () => useContext(ToastCtx);
export function ToastProvider({ children }: { children: ReactNode }) {
  const [t, setT] = useState<{ m: string; kind: string } | null>(null);
  const show = useCallback((m: string, kind: "ok" | "bad" = "ok") => { setT({ m, kind }); setTimeout(() => setT(null), 3200); }, []);
  return <ToastCtx.Provider value={show}>{children}{t && <div className={`toast ${t.kind}`} role="status">{t.m}</div>}</ToastCtx.Provider>;
}

/* ---- layout bits ---- */
export const Card = ({ title, actions, children, className = "" }: { title?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string }) => (
  <section className={`card ${className}`}>{(title || actions) && <div className="card-h"><h2>{title}</h2><div>{actions}</div></div>}{children}</section>
);
export const Kpi = ({ label, value, tone = "", hint }: { label: string; value: ReactNode; tone?: string; hint?: string }) => (
  <div className="card kpi" title={hint}><div className="l">{label}</div><div className={`v ${tone}`}>{value}</div></div>
);
export const Loading = ({ text = "Loading…" }: { text?: string }) => <div className="empty" role="status" aria-live="polite"><span className="spin" /> {text}</div>;
export const ErrorBox = ({ message, retry }: { message: string; retry?: () => void }) => (
  <div className="errbox" role="alert"><b>Could not load data.</b> {message} {retry && <button className="btn ghost sm" onClick={retry}>Retry</button>}</div>
);
export const Empty = ({ children, action }: { children: ReactNode; action?: ReactNode }) => <div className="empty"><p>{children}</p>{action}</div>;
export const Badge = ({ tone = "", children }: { tone?: string; children: ReactNode }) => <span className={`badge ${tone}`}>{children}</span>;
export const statusTone = (s: string) => ({ MET: "ok", ACTIVE: "ok", AT_RISK: "warn", MAINTENANCE: "warn", MISSED: "bad", CRITICAL: "bad", WARNING: "warn", INFO: "", NEW: "bad", ACKNOWLEDGED: "warn", RESOLVED: "ok", SHUT_IN: "warn", ARCHIVED: "", NO_DATA: "" } as Record<string, string>)[s] ?? "";

export function Async({ loading, error, reload, children }: { loading: boolean; error: string | null; reload: () => void; children: ReactNode }) {
  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} retry={reload} />;
  return <>{children}</>;
}

export function Pager({ page, size, total, onPage }: { page: number; size: number; total: number; onPage: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / size));
  return (
    <div className="row pager noprint">
      <button className="btn ghost sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>Previous</button>
      <span>Page {page} of {pages} · {total} total</span>
      <button className="btn ghost sm" disabled={page >= pages} onClick={() => onPage(page + 1)}>Next</button>
    </div>
  );
}

export function Field({ label, error, children, id }: { label: string; error?: string; children: ReactNode; id: string }) {
  return <div className="field"><label htmlFor={id}>{label}</label>{children}{error && <p className="err" id={id + "-err"}>{error}</p>}</div>;
}

export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    ref.current?.querySelector<HTMLElement>("input,select,textarea,button")?.focus();
    const k = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k);
    return () => { window.removeEventListener("keydown", k); prev?.focus(); };
  }, [onClose]);
  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={title} ref={ref}>
        <div className="card-h"><h2>{title}</h2><button className="btn ghost sm" onClick={onClose} aria-label="Close">✕</button></div>
        {children}
      </div>
    </div>
  );
}

export function Confirm({ title, message, confirmLabel, danger, onConfirm, onClose }: { title: string; message: ReactNode; confirmLabel: string; danger?: boolean; onConfirm: () => Promise<void> | void; onClose: () => void }) {
  const [busy, setBusy] = useState(false);
  return (
    <Modal title={title} onClose={onClose}>
      <p style={{ marginBottom: 16 }}>{message}</p>
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn ghost" onClick={onClose}>Cancel</button>
        <button className={`btn ${danger ? "danger" : ""}`} disabled={busy} onClick={async () => { setBusy(true); try { await onConfirm(); } finally { setBusy(false); } }}>{busy ? "Working…" : confirmLabel}</button>
      </div>
    </Modal>
  );
}

export function FilterBar({ f, set, wells, extra }: { f: Record<string, any>; set: (k: string, v: string) => void; wells?: any[]; extra?: ReactNode }) {
  return (
    <div className="row noprint filters">
      <div><label htmlFor="f-from">From</label><input id="f-from" type="date" value={f.from ?? ""} onChange={(e) => set("from", e.target.value)} /></div>
      <div><label htmlFor="f-to">To</label><input id="f-to" type="date" value={f.to ?? ""} onChange={(e) => set("to", e.target.value)} /></div>
      {wells && <div><label htmlFor="f-well">Well</label><select id="f-well" value={f.well_id ?? ""} onChange={(e) => set("well_id", e.target.value)}><option value="">All wells</option>{wells.map((w) => <option key={w.id} value={w.id}>{w.well_code}</option>)}</select></div>}
      {extra}
      <button className="btn ghost" onClick={() => { set("from", ""); set("to", ""); set("well_id", ""); }}>Clear</button>
    </div>
  );
}

export function useFilters(initial: Record<string, any> = {}) {
  const [f, setF] = useState<Record<string, any>>({ page: 1, ...initial });
  const set = useCallback((k: string, v: any) => setF((x) => ({ ...x, [k]: v, ...(k === "page" ? {} : { page: 1 }) })), []);
  return [f, set] as const;
}
