import { useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/auth";
import { useApi } from "../hooks/useApi";

const icon = (d: string) => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={d} /></svg>;
const NAV: [string, string, string][] = [
  ["/", "Dashboard", "M3 12l9-8 9 8M5 10v10h14V10"], ["/wells", "Wells", "M12 3v18M8 7h8M7 21h10"], ["/production", "Production records", "M4 5h16M4 12h16M4 19h10"],
  ["/loss", "Loss analysis", "M3 17l6-6 4 4 8-9M15 6h6v6"], ["/analytics", "Analytics & reports", "M5 20V10M12 20V4M19 20v-7"], ["/targets", "Targets", "M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0-18 0M12 12m-4 0a4 4 0 1 0 8 0a4 4 0 1 0-8 0"],
  ["/alerts", "Alerts", "M6 8a6 6 0 0 1 12 0c0 7 3 8 3 8H3s3-1 3-8M10 21h4"], ["/settings", "Settings", "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19 12l2-1-2-4-2 1-2-1V5h-4v2l-2 1-2-1-2 4 2 1v2l-2 1 2 4 2-1 2 1v2h4v-2l2-1 2 1 2-4-2-1z"],
];

export default function AppLayout() {
  const { user, logout } = useAuth();
  const nav = useNavigate(), loc = useLocation();
  const [menu, setMenu] = useState(false);
  const alerts = useApi<{ new: number; critical_new: number }>("/alerts/summary");
  const title = NAV.find(([p]) => (p === "/" ? loc.pathname === "/" : loc.pathname.startsWith(p)))?.[1] ?? "PetroPulse";
  return (
    <div className="app">
      <nav aria-label="Main navigation">
        <div className="brand">PetroPulse<small>Production &amp; loss intelligence</small></div>
        {NAV.map(([to, name, d]) => <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => (isActive ? "on" : "")}>{icon(d)}<span>{name}</span></NavLink>)}
      </nav>
      <div className="body">
        <header className="top noprint">
          <div className="crumbs"><Link to="/">PetroPulse</Link> / <b>{title}</b></div>
          <div className="row">
            <Link to="/alerts" className="bell" aria-label={`Alerts: ${alerts.data?.new ?? 0} new`} title="Open alerts">
              {icon("M6 8a6 6 0 0 1 12 0c0 7 3 8 3 8H3s3-1 3-8M10 21h4")}{!!alerts.data?.new && <span className={`dot ${alerts.data.critical_new ? "bad" : ""}`}>{alerts.data.new}</span>}
            </Link>
            <div className="usermenu">
              <button className="btn ghost sm" aria-haspopup="menu" aria-expanded={menu} onClick={() => setMenu(!menu)}>{user?.full_name}</button>
              {menu && <div className="menu" role="menu" onMouseLeave={() => setMenu(false)}>
                <div className="muted">{user?.email}</div>
                <button role="menuitem" onClick={() => { setMenu(false); nav("/settings"); }}>Profile &amp; settings</button>
                <button role="menuitem" onClick={logout}>Sign out</button>
              </div>}
            </div>
          </div>
        </header>
        <main><Outlet /></main>
      </div>
    </div>
  );
}
