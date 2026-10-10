import { createElement, useEffect, useRef, useState, type ReactNode } from "react";

/** Loads Google's <model-viewer> web component on first use (keeps it out of the main bundle). */
let loading: Promise<unknown> | null = null;
export function useModelViewer() {
  const [ready, setReady] = useState(!!customElements.get("model-viewer"));
  useEffect(() => {
    if (ready) return;
    loading ??= import("@google/model-viewer");
    loading.then(() => setReady(true));
  }, [ready]);
  return ready;
}

export type Hotspot = { label: string; position: string; normal: string; note?: string };

/** Thin React wrapper; `onPick` receives a surface point when the model is clicked (teacher hotspot editor). */
export function ModelView({ src, hotspots, active, onHotspot, onPick, height = 380, children }: {
  src: string; hotspots: Hotspot[]; active?: number; onHotspot?: (i: number) => void;
  onPick?: (p: { position: string; normal: string }) => void; height?: number; children?: ReactNode;
}) {
  const ready = useModelViewer();
  const ref = useRef<HTMLElement & { positionAndNormalFromPoint?: (x: number, y: number) => { position: { toString(): string }; normal: { toString(): string } } | null; cameraTarget?: string }>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || active == null || !hotspots[active]) return;
    el.setAttribute("camera-target", hotspots[active].position);
  }, [active, hotspots, ready]);

  if (!ready) return <div className="notice">Loading 3D viewer…</div>;
  const click = (e: React.MouseEvent) => {
    if (!onPick || !ref.current?.positionAndNormalFromPoint) return;
    if ((e.target as HTMLElement).dataset?.hotspot) return;
    const hit = ref.current.positionAndNormalFromPoint(e.clientX, e.clientY);
    if (hit) onPick({ position: hit.position.toString(), normal: hit.normal.toString() });
  };
  return createElement(
    "model-viewer",
    {
      ref, src, "camera-controls": true, "touch-action": "pan-y", ar: true, "ar-modes": "webxr scene-viewer quick-look",
      "shadow-intensity": "1", "interaction-prompt": "auto", onClick: click,
      style: { width: "100%", height, background: "linear-gradient(180deg,#f7f7fb,#e9ebf3)", borderRadius: 12 },
    },
    ...hotspots.map((h, i) => (
      <button key={i} slot={`hotspot-${i}`} data-hotspot="1" data-position={h.position} data-normal={h.normal}
        onClick={(e) => { e.stopPropagation(); onHotspot?.(i); }}
        style={{ border: "none", borderRadius: 99, padding: "3px 9px", fontSize: 12, fontWeight: 600, cursor: "pointer",
          background: active === i ? "#4b3fe0" : "#fff", color: active === i ? "#fff" : "#151821", boxShadow: "0 2px 6px rgba(0,0,0,.25)" }}>
        {i + 1}. {h.label}
      </button>
    )),
    children,
  );
}
