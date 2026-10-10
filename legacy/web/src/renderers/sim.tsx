import { useMemo, useState } from "react";
import type { Json } from "../api";
import { Md } from "../ui";
import { Choices, Feedback, SubmitBar, type RProps } from "./common";

// ------------------------------------------------------------------ safe expression evaluator
// Grammar: numbers, identifiers (variables), + - * / ^, unary -, parentheses, whitelisted functions.
// No property access, no strings, no eval — generated models can never run code.

const FUNCS: Record<string, (...a: number[]) => number> = {
  sqrt: Math.sqrt, log: Math.log, ln: Math.log, log10: Math.log10, exp: Math.exp, sin: Math.sin, cos: Math.cos,
  tan: Math.tan, abs: Math.abs, min: Math.min, max: Math.max, pow: Math.pow, floor: Math.floor, ceil: Math.ceil,
  round: Math.round,
};
const CONSTS: Record<string, number> = { pi: Math.PI, e: Math.E };

type Tok = { t: "num" | "id" | "op" | "(" | ")" | ","; v: string };

function lex(src: string): Tok[] {
  const out: Tok[] = [];
  const re = /\s*(?:(\d+\.?\d*(?:[eE][-+]?\d+)?|\.\d+)|([A-Za-z_][A-Za-z0-9_]*)|(\*\*|[-+*/^])|([(),]))/y;
  let i = 0;
  while (i < src.length) {
    re.lastIndex = i;
    const m = re.exec(src);
    if (!m) { if (/\s/.test(src[i])) { i++; continue; } throw new Error(`Unexpected '${src[i]}'`); }
    if (m[1]) out.push({ t: "num", v: m[1] });
    else if (m[2]) out.push({ t: "id", v: m[2] });
    else if (m[3]) out.push({ t: "op", v: m[3] === "**" ? "^" : m[3] });
    else if (m[4]) out.push({ t: m[4] as "(" | ")" | ",", v: m[4] });
    i = re.lastIndex;
  }
  return out;
}

export function compile(src: string): (vars: Record<string, number>) => number {
  const toks = lex(src);
  let k = 0;
  const peek = () => toks[k];
  const eat = (t?: string) => { const x = toks[k++]; if (!x || (t && x.v !== t && x.t !== t)) throw new Error("Syntax error"); return x; };
  type Node = (v: Record<string, number>) => number;
  function expr(): Node { let l = term(); while (peek()?.t === "op" && "+-".includes(peek().v)) { const op = eat().v; const r = term(); const a = l; l = op === "+" ? (v) => a(v) + r(v) : (v) => a(v) - r(v); } return l; }
  function term(): Node { let l = power(); while (peek()?.t === "op" && "*/".includes(peek().v)) { const op = eat().v; const r = power(); const a = l; l = op === "*" ? (v) => a(v) * r(v) : (v) => a(v) / r(v); } return l; }
  function power(): Node { const b = unary(); if (peek()?.t === "op" && peek().v === "^") { eat(); const e = power(); return (v) => Math.pow(b(v), e(v)); } return b; }
  function unary(): Node { if (peek()?.t === "op" && peek().v === "-") { eat(); const x = unary(); return (v) => -x(v); } if (peek()?.t === "op" && peek().v === "+") { eat(); return unary(); } return atom(); }
  function atom(): Node {
    const x = eat();
    if (x.t === "num") { const n = parseFloat(x.v); return () => n; }
    if (x.t === "(") { const e = expr(); eat(")"); return e; }
    if (x.t === "id") {
      if (peek()?.t === "(") {
        const f = FUNCS[x.v.toLowerCase()];
        if (!f) throw new Error(`Unknown function ${x.v}`);
        eat("(");
        const args: Node[] = [];
        if (peek()?.t !== ")") { args.push(expr()); while (peek()?.t === ",") { eat(","); args.push(expr()); } }
        eat(")");
        return (v) => f(...args.map((a) => a(v)));
      }
      const name = x.v;
      return (v) => (name in v ? v[name] : name.toLowerCase() in CONSTS ? CONSTS[name.toLowerCase()] : NaN);
    }
    throw new Error("Syntax error");
  }
  const tree = expr();
  if (k !== toks.length) throw new Error("Unexpected trailing input");
  return tree;
}

// ------------------------------------------------------------------ chart

const COLORS = ["#4b3fe0", "#13a38a", "#c2334d", "#b26a00"];

function Chart({ series, xLabel, marker }: { series: { name: string; pts: [number, number][] }[]; xLabel: string; marker: number }) {
  const W = 560, H = 260, P = 44;
  const all = series.flatMap((s) => s.pts).filter(([, y]) => isFinite(y));
  if (!all.length) return <div className="notice warn">This model produces no finite values in the chosen range.</div>;
  const xs = all.map((p) => p[0]), ys = all.map((p) => p[1]);
  const [x0, x1] = [Math.min(...xs), Math.max(...xs)];
  let [y0, y1] = [Math.min(...ys), Math.max(...ys)];
  if (y0 === y1) { y0 -= 1; y1 += 1; }
  const sx = (x: number) => P + ((x - x0) / (x1 - x0 || 1)) * (W - P - 12);
  const sy = (y: number) => H - P + 10 - ((y - y0) / (y1 - y0)) * (H - P - 10);
  const fmt = (n: number) => (Math.abs(n) >= 1000 || (Math.abs(n) < 0.01 && n !== 0) ? n.toExponential(1) : +n.toFixed(2));
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 10 }} role="img" aria-label="Model output chart">
      <line x1={P} y1={H - P + 10} x2={W - 12} y2={H - P + 10} stroke="#c9cedb" />
      <line x1={P} y1={10} x2={P} y2={H - P + 10} stroke="#c9cedb" />
      <text x={P} y={H - 12} fontSize={11} fill="#5d6475">{fmt(x0)}</text>
      <text x={W - 12} y={H - 12} fontSize={11} fill="#5d6475" textAnchor="end">{fmt(x1)}</text>
      <text x={(W + P) / 2} y={H - 4} fontSize={12} fill="#5d6475" textAnchor="middle">{xLabel}</text>
      <text x={P - 6} y={16} fontSize={11} fill="#5d6475" textAnchor="end">{fmt(y1)}</text>
      <text x={P - 6} y={H - P + 10} fontSize={11} fill="#5d6475" textAnchor="end">{fmt(y0)}</text>
      <line x1={sx(marker)} x2={sx(marker)} y1={10} y2={H - P + 10} stroke="#f0b429" strokeDasharray="4 3" />
      {series.map((s, i) => (
        <polyline key={s.name} fill="none" stroke={COLORS[i % 4]} strokeWidth={2.2}
          points={s.pts.filter(([, y]) => isFinite(y)).map(([x, y]) => `${sx(x)},${sy(y)}`).join(" ")} />
      ))}
      {series.map((s, i) => <text key={s.name} x={W - 16} y={22 + i * 16} fontSize={12} textAnchor="end" fill={COLORS[i % 4]}>{s.name}</text>)}
    </svg>
  );
}

export function ParameterExplorer({ a, reveal, result, locked, submit, busy }: RProps) {
  const p = a.data.payload;
  const vars = p.variables as { name: string; symbol: string; min: number; max: number; step: number; default: number; unit: string }[];
  const outs = p.outputs as { name: string; symbol: string; expression: string; unit: string }[];
  const [vals, setVals] = useState<Record<string, number>>(Object.fromEntries(vars.map((v) => [v.symbol, v.default])));
  const [answers, setAnswers] = useState<Record<string, number[]>>({});
  const compiled = useMemo(() => outs.map((o) => { try { return { o, f: compile(o.expression), err: "" }; } catch (e) { return { o, f: null, err: String(e) }; } }), [outs]);
  const xv = vars.find((v) => v.symbol === p.x_variable) ?? vars[0];
  const series = compiled.filter((c) => c.f).map(({ o, f }) => {
    const pts: [number, number][] = [];
    for (let i = 0; i <= 60; i++) {
      const x = xv.min + ((xv.max - xv.min) * i) / 60;
      pts.push([x, f!({ ...vals, [xv.symbol]: x })]);
    }
    return { name: o.name, pts };
  });
  const qs = (p.questions ?? []) as { prompt: string; options: Json[] }[];
  return (
    <div className="stack">
      <Md text={p.intro} />
      <div className="grid2" style={{ alignItems: "start" }}>
        <div className="stack">
          {vars.map((v) => (
            <div key={v.symbol}>
              <label htmlFor={`v-${v.symbol}`}>{v.name} <span className="mono faint">({v.symbol})</span>: <strong>{vals[v.symbol]}</strong> {v.unit}</label>
              <input id={`v-${v.symbol}`} type="range" min={v.min} max={v.max} step={v.step || (v.max - v.min) / 100}
                value={vals[v.symbol]} onChange={(e) => setVals({ ...vals, [v.symbol]: parseFloat(e.target.value) })} style={{ padding: 0 }} />
            </div>
          ))}
          <div className="card flat">
            {compiled.map(({ o, f, err }) => (
              <div key={o.symbol} className="spread">
                <span>{o.name}</span>
                <strong className="mono">{err ? "—" : (() => { const y = f!(vals); return isFinite(y) ? +y.toPrecision(4) : "undefined"; })()} {o.unit}</strong>
              </div>
            ))}
          </div>
        </div>
        <Chart series={series} xLabel={`${xv.name} (${xv.unit})`} marker={vals[xv.symbol]} />
      </div>
      {p.caveat && <div className="small muted"><strong>Model limits: </strong>{p.caveat}</div>}
      {qs.map((q, i) => (
        <div key={i}>
          <strong><Md text={q.prompt} inline /></strong>
          <Choices options={q.options} selected={answers[String(i)] ?? []} multiple={false} locked={locked}
            setSelected={(s) => setAnswers({ ...answers, [String(i)]: s })} reveal={reveal?.questions?.[i]?.options ?? null} />
          {reveal?.questions?.[i]?.explanation && <div className="rationale"><Md text={reveal.questions[i].explanation} inline /></div>}
        </div>
      ))}
      {!locked && <SubmitBar onClick={() => submit({ answers })} disabled={qs.some((_, i) => !answers[String(i)])} busy={busy} />}
      <Feedback result={result} />
    </div>
  );
}
