import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api, type Element } from "./api";

export const KT_COLOR: Record<string, string> = {
  fact: "#8a91a3", concept: "#4b3fe0", principle: "#7c3aed", process: "#0891b2", procedure: "#0f8a5f",
  structure: "#b45309", chronology: "#c2410c", argument: "#be185d", quantitative: "#1d4ed8", code: "#111827",
  language: "#0d9488", data: "#4d7c0f",
};

// ---------------------------------------------------------------- citations

const CiteCtx = createContext<(id: string) => void>(() => {});
export const useCite = () => useContext(CiteCtx);

export function CitationProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState<string | null>(null);
  return (
    <CiteCtx.Provider value={setOpen}>
      {children}
      {open && <SourceDrawer elementId={open} onClose={() => setOpen(null)} />}
    </CiteCtx.Provider>
  );
}

function SourceDrawer({ elementId, onClose }: { elementId: string; onClose: () => void }) {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.element>> | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => { api.element(elementId).then(setData).catch((e) => setErr(String(e))); }, [elementId]);
  const url = data?.source.origin?.startsWith("http") ? data.source.origin : null;
  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-label="Source evidence">
        <div className="drawer-head">
          <div>
            <div className="tiny faint">SOURCE EVIDENCE · {elementId}</div>
            <strong>{data?.source.title ?? "Loading…"}</strong>
          </div>
          <button className="btn ghost sm" onClick={onClose}>Close</button>
        </div>
        <div className="drawer-body">
          {err && <div className="notice bad">{err}</div>}
          {data && (
            <>
              <div className="small muted" style={{ marginBottom: 10 }}>
                {data.element.section_path.join(" › ") || "—"}
                {data.element.page != null && <> · {data.source.kind === "pptx" ? "slide" : "page"} {data.element.page}</>}
                {data.element.meta?.start != null && <> · at {fmtTime(data.element.meta.start)}</>}
                {url && <> · <a href={url} target="_blank" rel="noreferrer">open original</a></>}
              </div>
              {data.context.map((e) => <ElementView key={e.id} e={e} focus={e.id === elementId} />)}
            </>
          )}
        </div>
      </aside>
    </>
  );
}

export function fmtTime(s: number) {
  const m = Math.floor(s / 60);
  return `${m}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
}

export function ElementView({ e, focus }: { e: Element; focus?: boolean }) {
  let body: ReactNode;
  if (e.kind === "heading") body = <strong style={{ fontSize: e.level && e.level <= 2 ? 17 : 15 }}>{e.text}</strong>;
  else if (e.kind === "code") body = <pre><code>{e.text}</code></pre>;
  else if (e.kind === "table") body = <Md text={e.text} />;
  else if (e.kind === "figure")
    body = (
      <div>
        {e.media_path ? <img src={`/media/${e.media_path}`} alt={e.text || "figure"} style={{ maxWidth: "100%", borderRadius: 8 }} />
          : e.meta?.url ? <a href={e.meta.url} target="_blank" rel="noreferrer">[figure]</a> : <span className="faint">[figure]</span>}
        {e.text && <div className="small muted">{e.text}</div>}
      </div>
    );
  else if (e.kind === "list_item") body = <div>• {e.text}</div>;
  else body = <div>{e.text}</div>;
  return (
    <div className={`el ${focus ? "focus" : ""}`} id={`el-${e.id}`}>
      <div className="el-kind">{e.id} · {e.kind}{e.confidence < 0.6 ? " · low confidence" : ""}</div>
      {body}
    </div>
  );
}

// ---------------------------------------------------------------- markdown with [e12] citations

export function Md({ text, inline }: { text: string; inline?: boolean }) {
  const cite = useCite();
  const src = (text ?? "").replace(/\[(e\d+)\]/g, "[$1](#cite-$1)").replace(/\[(e\d+(?:\s*,\s*e\d+)+)\]/g,
    (_m, ids: string) => ids.split(/\s*,\s*/).map((i) => `[${i}](#cite-${i})`).join(""));
  return (
    <div className={inline ? "md md-inline" : "md"} style={inline ? { display: "inline" } : undefined}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) =>
            href?.startsWith("#cite-") ? (
              <button className="cite" onClick={() => cite(href.slice(6))} title="Show source">{children}</button>
            ) : <a href={href} target="_blank" rel="noreferrer">{children}</a>,
          p: ({ children }) => (inline ? <span>{children}</span> : <p>{children}</p>),
        }}>
        {src}
      </ReactMarkdown>
    </div>
  );
}

export function CiteList({ ids }: { ids: string[] }) {
  const cite = useCite();
  if (!ids?.length) return null;
  return (
    <span className="row" style={{ gap: 4, display: "inline-flex" }}>
      {ids.slice(0, 8).map((i) => <button key={i} className="cite" onClick={() => cite(i)}>{i}</button>)}
    </span>
  );
}

// ---------------------------------------------------------------- small pieces

export function Progress({ value }: { value: number }) {
  return <div className="progress"><div style={{ width: `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%` }} /></div>;
}

export function StatusBadge({ status }: { status: string }) {
  const cls = { approved: "good", ready: "good", done: "good", flagged: "bad", failed: "bad", draft: "warn",
    building: "info", analysing: "info", running: "info", analysed: "primary", verified: "good" }[status] ?? "";
  return <span className={`badge ${cls}`}>{status}</span>;
}

export function Tabs<T extends string>({ tabs, value, onChange }: { tabs: [T, string][]; value: T; onChange: (t: T) => void }) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map(([k, label]) => (
        <button key={k} role="tab" aria-selected={value === k} className={`tab ${value === k ? "on" : ""}`} onClick={() => onChange(k)}>{label}</button>
      ))}
    </div>
  );
}

export function Spinner() { return <span className="spinner" aria-label="loading" />; }

export function ErrorNote({ error }: { error: string }) {
  return error ? <div className="notice bad" role="alert">{error}</div> : null;
}

export function shortType(t: string) { return t.replace(/_/g, " "); }
