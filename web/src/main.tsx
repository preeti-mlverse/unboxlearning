import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, Route, Routes, useLocation } from "react-router-dom";
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
  return (
    <header className="m-app-top">
      <Link to="/" className="m-brand"><i />Unbox Learning</Link>
      {!learner && <Link to="/create">Create</Link>}
      <span style={{ flex: 1 }} />
      {health && !learner && st !== "ok" && (
        <button className="m-chip" title={health.ai_status?.message} onClick={async () => { await api.healthCheck(); setHealth(await api.health()); }}>
          {health.provider === "mock" ? "Offline mode" : st === "no_credits" ? "⚠️ AI: no credits" : st === "invalid_key" ? "⚠️ AI key rejected" : "AI: checking…"}
        </button>
      )}
    </header>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <CitationProvider>
        <TopBar />
        <Routes>
          <Route path="/" element={<CreatorHome />} />
          <Route path="/create" element={<Create />} />
          <Route path="/create/:cid" element={<Setup />} />
          <Route path="/course/:cid" element={<CoursePreview />} />
          <Route path="/learn/:cid" element={<Journey />} />
          <Route path="/learn/:cid/m/:mid" element={<Player />} />
          <Route path="/learn/:cid/practice" element={<Practice />} />
          <Route path="/studio/:id" element={<Studio />} />
          <Route path="/classic" element={<ClassicHome />} />
          <Route path="/classic/new" element={<NewCourse />} />
          <Route path="/classic/learn/:id" element={<Learn />} />
        </Routes>
      </CitationProvider>
    </BrowserRouter>
  </StrictMode>,
);
