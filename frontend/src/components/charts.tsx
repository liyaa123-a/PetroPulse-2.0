import { fmt } from "../utils/format";

export interface Series { key: string; label: string; color: string; dashed?: boolean }

/** Accessible SVG line chart. Data comes from the API; axes show units; each point has a tooltip. */
export function LineChart({ data, series, xKey = "date", unit = "bbl" }: { data: any[]; series: Series[]; xKey?: string; unit?: string }) {
  if (!data.length) return null;
  const W = 640, H = 240, L = 54, B = 28, T = 10, R = 12;
  const max = Math.max(...data.flatMap((d) => series.map((s) => Number(d[s.key]) || 0)), 1) * 1.1;
  const x = (i: number) => L + (data.length === 1 ? (W - L - R) / 2 : (i * (W - L - R)) / (data.length - 1));
  const y = (v: number) => T + (H - T - B) * (1 - v / max);
  const step = Math.ceil(data.length / 7);
  return (
    <div>
      <div className="leg">{series.map((s) => <span key={s.key}><i style={{ background: s.color }} />{s.label} ({unit})</span>)}</div>
      <div className="tw">
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ minWidth: 440 }} role="img" aria-label={series.map((s) => s.label).join(" and ") + " over time"}>
          {[0, 1, 2, 3, 4].map((i) => { const v = (max * i) / 4; return <g key={i}><line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke="var(--line)" /><text x={L - 6} y={y(v) + 4} textAnchor="end">{fmt(v)}</text></g>; })}
          {data.map((d, i) => i % step === 0 && <text key={i} x={x(i)} y={H - 8} textAnchor="middle">{String(d[xKey]).slice(-5)}</text>)}
          {series.map((s) => (
            <g key={s.key}>
              <path d={data.map((d, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(Number(d[s.key]) || 0).toFixed(1)}`).join("")} fill="none" stroke={s.color} strokeWidth={s.dashed ? 2 : 2.6} strokeDasharray={s.dashed ? "5 4" : undefined} />
              {!s.dashed && data.map((d, i) => <circle key={i} cx={x(i)} cy={y(Number(d[s.key]) || 0)} r={3} fill={s.color}><title>{`${d[xKey]}: ${s.label} ${fmt(Number(d[s.key]), 1)} ${unit}`}</title></circle>)}
            </g>
          ))}
        </svg>
      </div>
    </div>
  );
}

/** Horizontal bars for ranked comparisons. */
export function BarList({ items, unit = "bbl", color = "var(--bad)" }: { items: { label: string; value: number }[]; unit?: string; color?: string }) {
  const max = Math.max(...items.map((i) => i.value), 1);
  return (
    <div role="list">
      {items.map((i) => (
        <div role="listitem" className="barrow" key={i.label}>
          <span>{i.label}</span>
          <div className="bartrack"><div style={{ width: `${(i.value / max) * 100}%`, background: color }} /></div>
          <span className="r">{fmt(i.value)} {unit}</span>
        </div>
      ))}
    </div>
  );
}
