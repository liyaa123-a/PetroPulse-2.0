export const fmt = (n: number | null | undefined, d = 0) => (n === null || n === undefined ? "–" : n.toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d }));
export const usd = (n: number | null | undefined) => (n === null || n === undefined ? "–" : (n < 0 ? "-$" : "$") + Math.abs(n).toLocaleString(undefined, { maximumFractionDigits: 0 }));
export const pct = (n: number | null | undefined) => (n === null || n === undefined ? "–" : fmt(n, 1) + "%");
export const label = (s: string | null | undefined) => (s ? s.charAt(0) + s.slice(1).toLowerCase().replace(/_/g, " ") : "–");
export const achTone = (a: number | null | undefined, threshold = 85) => (a == null ? "" : a >= 100 ? "ok" : a >= threshold ? "warn" : "bad");
export const today = () => new Date().toISOString().slice(0, 10);
