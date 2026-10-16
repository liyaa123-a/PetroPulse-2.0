import { useState } from "react";
import { useApi } from "./useApi";

/** Runs an async submit, tracking busy state, a form-level message and per-field errors from the API. */
export function useSubmit() {
  const [busy, setBusy] = useState(false), [err, setErr] = useState(""), [fields, setFields] = useState<Record<string, string>>({});
  async function run(fn: () => Promise<unknown>): Promise<boolean> {
    setBusy(true); setErr(""); setFields({});
    try { await fn(); return true; } catch (e: any) { setErr(e.message ?? "Something went wrong."); setFields(e.fields ?? {}); return false; } finally { setBusy(false); }
  }
  return { busy, err, fields, run };
}
export const useWells = () => useApi<any[]>("/wells?page_size=100&include_archived=1");
