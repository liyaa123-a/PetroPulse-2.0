import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";

export function useApi<T = any>(path: string | null) {
  const [s, setS] = useState<{ data: T | null; meta: any; loading: boolean; error: string | null }>({ data: null, meta: null, loading: true, error: null });
  const [n, setN] = useState(0);
  useEffect(() => {
    if (!path) return;
    let cancel = false;
    setS((x) => ({ ...x, loading: true, error: null }));
    api.get<T>(path).then((r) => !cancel && setS({ data: r.data, meta: r.meta, loading: false, error: null }))
      .catch((e) => !cancel && setS((x) => ({ ...x, loading: false, error: e.message })));
    return () => { cancel = true; };
  }, [path, n]);
  const reload = useCallback(() => setN((x) => x + 1), []);
  return { ...s, reload };
}
