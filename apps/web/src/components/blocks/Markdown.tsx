// A deliberately small Markdown renderer for lesson text: paragraphs, **bold**, *italic*, `code`, links, and
// bulleted/numbered lists. It builds React elements (never raw HTML), so lesson text can't inject scripts.
import { Fragment } from "react";

function inline(text: string, key = 0): React.ReactNode[] {
  const out: React.ReactNode[] = [];
  const re = /(\*\*([^*]+)\*\*|\*([^*]+)\*|`([^`]+)`|\[([^\]]+)\]\((https?:\/\/[^\s)]+)\))/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const k = `${key}-${i++}`;
    if (m[2]) out.push(<strong key={k}>{m[2]}</strong>);
    else if (m[3]) out.push(<em key={k}>{m[3]}</em>);
    else if (m[4]) out.push(<code key={k}>{m[4]}</code>);
    else if (m[5]) out.push(<a key={k} href={m[6]} target="_blank" rel="noopener noreferrer">{m[5]}</a>);
    last = re.lastIndex;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

const BULLET = /^\s*[-*•]\s+/;
const NUMBER = /^\s*\d+[.)]\s+/;
type Group = { kind: "p" | "ul" | "ol"; lines: string[] };

/** Split text into paragraphs and lists: blank lines end a group, and a run of list lines is a list
 *  even when it follows a sentence directly ("Three parts:\n- one\n- two"). */
function groups(text: string): Group[] {
  const out: Group[] = [];
  for (const raw of text.replace(/\r\n/g, "\n").split("\n")) {
    const line = raw.trimEnd();
    if (!line.trim()) { out.push({ kind: "p", lines: [] }); continue; }
    const kind = BULLET.test(line) ? "ul" : NUMBER.test(line) ? "ol" : "p";
    const last = out[out.length - 1];
    if (last && last.kind === kind && last.lines.length) last.lines.push(line);
    else out.push({ kind, lines: [line] });
  }
  return out.filter((g) => g.lines.length);
}

export function Markdown({ text }: { text: string }) {
  return (
    <div className="prose-lesson">
      {groups(text).map((g, gi) => {
        if (g.kind === "ul") return <ul key={gi}>{g.lines.map((l, li) => <li key={li}>{inline(l.replace(BULLET, ""), li)}</li>)}</ul>;
        if (g.kind === "ol") return <ol key={gi}>{g.lines.map((l, li) => <li key={li}>{inline(l.replace(NUMBER, ""), li)}</li>)}</ol>;
        return <p key={gi}>{g.lines.map((l, li) => <Fragment key={li}>{li > 0 && <br />}{inline(l.trim(), li)}</Fragment>)}</p>;
      })}
    </div>
  );
}
