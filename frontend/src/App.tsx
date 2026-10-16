import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./hooks/auth";
import { apiConfigured } from "./api/client";
import { Loading } from "./components/ui";
import AppLayout from "./layouts/AppLayout";
import AuthPage from "./pages/AuthPage";
import Dashboard from "./pages/Dashboard";
import Wells from "./pages/Wells";
import WellDetail from "./pages/WellDetail";
import Records from "./pages/Records";
import Loss from "./pages/Loss";
import Analytics from "./pages/Analytics";
import Targets from "./pages/Targets";
import Alerts from "./pages/Alerts";
import Settings from "./pages/Settings";

export default function App() {
  const { user, ready } = useAuth();
  if (!ready) return <Loading text="Starting PetroPulse…" />;
  return (
    <>
      {!apiConfigured && <div className="errbox" role="alert" style={{ margin: 12 }}>VITE_API_BASE_URL is not set, so the app cannot reach the API. Set it in your hosting environment and rebuild.</div>}
      <Routes>
        {!user ? (
          <Route path="*" element={<AuthPage />} />
        ) : (
          <Route element={<AppLayout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/wells" element={<Wells />} />
            <Route path="/wells/:id" element={<WellDetail />} />
            <Route path="/production" element={<Records />} />
            <Route path="/loss" element={<Loss />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/targets" element={<Targets />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        )}
      </Routes>
    </>
  );
}
