import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { api } from "./api";
import { Learn } from "./pages/Learn";
import { NewCourse } from "./pages/NewCourse";
import { Studio } from "./pages/Studio";
import { Home as ClassicHome } from "./pages/Home";
import { CoursePreview, Create, CreatorHome } from "./micro/Creator";
import { Journey, Practice } from "./micro/Journey";
import { Player } from "./micro/Player";
import { Setup } from "./micro/Setup";
import "./styles.css";
import "./micro/micro.css";
import { CitationProvider } from "./ui";
import { AuthProvider, RequireEducator, useAuth } from "./auth";
import { DashboardPage, Login, Signup, Welcome } from "./pages/Account";

function TopBar() {
  const [health, setHealth] = useState<{ provider: string; ai_status: { state: string; message: string } } | null>(null);
  useEffect(() => {
    const load = () => api.health().then(setHealth).catch(() => setHealth(null));
    load();
    const t = window.setInterval(load, 30000);
    return () => window.clearInterval(t);
  }, []);
  const loc = useLocation();
  if (/^\/learn\/[^/]+\/m\//.test(loc.pathname)) return null; // the module player is full-screen
  const st = health?.ai_status?.state;
  const learner = loc.pathname.startsWith("/learn/");
  const { user, logout } = useAuth();
  const nav = useNavigate();
  return (
    <header className="m-app-top">
      <Link to={user ? "/dashboard" : "/"} className="m-brand"><img src="/unboxed-mark.svg" alt="" width="30" height="30" />Unbox<em>Ed</em></Link>
      {user && <Link to="/dashboard">Dashboard</Link>}
      {user?.is_educator && !learner && <Link to="/create">Create</Link>}
      {user?.is_educator && !learner && <Link to="/courses">All courses</Link>}
      <span style={{ flex: 1 }} />
      {health && !learner && st !== "ok" && (
        <button className="m-chip" title={health.ai_status?.message} onClick={async () => { await api.healthCheck(); setHealth(await api.health()); }}>
          {health.provider === "mock" ? "Offline mode" : st === "no_credits" ? "⚠️ AI: no credits" : st === "invalid_key" ? "⚠️ AI key rejected" : "AI: checking…"}
        </button>
      )}
      {user ? (
        <span className="m-user">
          <span className="m-avatar" aria-hidden="true">{user.name.slice(0, 1).toUpperCase()}</span>
          <span className="m-user-name">{user.name}<small>{user.is_educator ? "Educator" : "Learner"}</small></span>
          <button className="m-btn ghost sm" onClick={async () => { await logout(); nav("/login"); }}>Log out</button>
        </span>
      ) : (
        <span className="m-row"><Link to="/login">Log in</Link><Link className="m-btn sm" to="/signup">Sign up</Link></span>
      )}
    </header>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
      <CitationProvider>
        <TopBar />
        <Routes>
          <Route path="/" element={<Welcome />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/courses" element={<RequireEducator><CreatorHome /></RequireEducator>} />
          <Route path="/create" element={<RequireEducator><Create /></RequireEducator>} />
          <Route path="/create/:cid" element={<RequireEducator><Setup /></RequireEducator>} />
          <Route path="/course/:cid" element={<RequireEducator><CoursePreview /></RequireEducator>} />
          <Route path="/learn/:cid" element={<Journey />} />
          <Route path="/learn/:cid/m/:mid" element={<Player />} />
          <Route path="/learn/:cid/practice" element={<Practice />} />
          <Route path="/studio/:id" element={<RequireEducator><Studio /></RequireEducator>} />
          <Route path="/classic" element={<RequireEducator><ClassicHome /></RequireEducator>} />
          <Route path="/classic/new" element={<RequireEducator><NewCourse /></RequireEducator>} />
          <Route path="/classic/learn/:id" element={<Learn />} />
        </Routes>
      </CitationProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
