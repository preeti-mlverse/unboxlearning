import type { ReactElement } from "react";
import type { Visual as V } from "./mapi";

/** Draws a card's visual. Diagrams come from data (free, exact, accessible); pictures are generated or from the source. */
export function Visual({ v, big = true }: { v: V; big?: boolean }) {
  if (!v || v.kind === "none") return null;
  if ((v.kind === "illustration" || v.kind === "figure") && v.media)
    return <img className={`mv-img ${big ? "" : "sm"}`} src={`/media/${v.media}`} alt={v.prompt || "illustration"} loading="lazy" />;
  if (v.kind === "flow") return <Flow items={v.items} />;
  if (v.kind === "cycle") return <Cycle items={v.items} />;
  if (v.kind === "timeline") return <TimelineV items={v.items} />;
  if (v.kind === "compare") return <Compare items={v.items} />;
  if (v.kind === "hierarchy") return <Tree items={v.items} />;
  if (v.kind === "code") return <pre className="mv-code"><code>{v.code}</code></pre>;
  if (v.kind === "formula") return <div className="mv-formula">{v.code}</div>;
  return null;
}

function Flow({ items }: { items: string[] }) {
  return (
    <div className="mv-flow" role="list" aria-label="Steps">
      {items.map((t, i) => (
        <div key={i} className="mv-flow-step" role="listitem" style={{ animationDelay: `${i * 0.12}s` }}>
          <span className="mv-num">{i + 1}</span><span>{t}</span>
          {i < items.length - 1 && <span className="mv-arrow" aria-hidden>→</span>}
        </div>
      ))}
    </div>
  );
}

function Cycle({ items }: { items: string[] }) {
  const n = items.length, R = 118, cx = 170, cy = 150;
  return (
    <svg viewBox="0 0 340 300" className="mv-svg" role="img" aria-label={`Cycle: ${items.join(" → ")}`}>
      <circle cx={cx} cy={cy} r={R} fill="none" stroke="var(--m-line)" strokeWidth={2} strokeDasharray="6 6" />
      {items.map((t, i) => {
        const a = (i / n) * Math.PI * 2 - Math.PI / 2;
        const x = cx + R * Math.cos(a), y = cy + R * Math.sin(a);
        return (
          <g key={i}>
            <rect x={x - 62} y={y - 20} width={124} height={40} rx={12} fill="var(--m-soft)" stroke="var(--m-primary)" />
            <foreignObject x={x - 58} y={y - 18} width={116} height={36}>
              <div className="mv-cycle-label">{t}</div>
            </foreignObject>
          </g>
        );
      })}
      <text x={cx} y={cy + 6} textAnchor="middle" fontSize={26} fill="var(--m-primary)">⟳</text>
    </svg>
  );
}

function TimelineV({ items }: { items: string[] }) {
  return (
    <ol className="mv-timeline">
      {items.map((t, i) => {
        const [when, ...rest] = t.split(":");
        const has = rest.length > 0 && when.length < 28;
        return (
          <li key={i} style={{ animationDelay: `${i * 0.12}s` }}>
            {has && <span className="mv-when">{when.trim()}</span>}
            <span>{has ? rest.join(":").trim() : t}</span>
          </li>
        );
      })}
    </ol>
  );
}

function Compare({ items }: { items: string[] }) {
  const rows = items.map((r) => r.split("|").map((x) => x.trim()));
  const [head, ...body] = rows;
  return (
    <table className="mv-compare">
      <thead><tr>{head.map((h, i) => <th key={i}>{h}</th>)}</tr></thead>
      <tbody>{body.map((r, i) => <tr key={i}>{r.map((c, j) => (j === 0 ? <th key={j}>{c}</th> : <td key={j}>{c}</td>))}</tr>)}</tbody>
    </table>
  );
}

function Tree({ items }: { items: string[] }) {
  const children: Record<string, string[]> = {};
  const parents = new Set<string>(), kids = new Set<string>();
  items.forEach((l) => {
    const [p, c] = l.split(">").map((x) => x.trim());
    if (p && c) { (children[p] ??= []).push(c); parents.add(p); kids.add(c); }
  });
  const roots = [...parents].filter((p) => !kids.has(p));
  const node = (n: string, d = 0): ReactElement => (
    <li key={n + d}><span className="mv-node">{n}</span>{children[n] && <ul>{children[n].map((c) => node(c, d + 1))}</ul>}</li>
  );
  return <ul className="mv-tree">{(roots.length ? roots : [items[0]]).map((r) => node(r))}</ul>;
}
