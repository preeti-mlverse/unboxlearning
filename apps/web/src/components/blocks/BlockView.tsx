// Renders a lesson block by type. The registry here mirrors the API's (apps/api/unboxed_api/services/blocks.py):
// a new block type is a schema there plus a renderer here. Unknown types degrade to a quiet placeholder.
import type { Block } from "@shared/index";

import { apiUrl } from "@/lib/api";

import { Markdown } from "./Markdown";

type TextConfig = { heading?: string | null; body?: string };
type ImageConfig = { document_id: string; alt: string; caption?: string | null; size?: "small" | "medium" | "full" };

function TextBlock({ config }: { config: TextConfig }) {
  return (
    <section className="grid gap-3">
      {config.heading && <h2 className="text-2xl font-extrabold sm:text-[28px]">{config.heading}</h2>}
      {config.body ? <div className="text-[17px] leading-relaxed sm:text-lg"><Markdown text={config.body} /></div> : null}
    </section>
  );
}

const WIDTH = { small: "max-w-xs", medium: "max-w-md", full: "max-w-full" };

function ImageBlock({ config, src }: { config: ImageConfig; src: string | null }) {
  return (
    <figure className={`grid gap-2 ${WIDTH[config.size ?? "full"]}`}>
      {src
        // eslint-disable-next-line @next/next/no-img-element
        ? <img src={apiUrl(src)} alt={config.alt} loading="lazy" className="w-full rounded-2xl border-2 border-line bg-surface object-contain" />
        : <div className="grid aspect-video place-items-center rounded-2xl bg-lavender text-muted">Image unavailable</div>}
      {config.caption && <figcaption className="text-sm text-muted">{config.caption}</figcaption>}
    </figure>
  );
}

export function BlockView({ block }: { block: Block }) {
  switch (block.block_type) {
    case "text":
      return <TextBlock config={block.config as TextConfig} />;
    case "image":
      return <ImageBlock config={block.config as unknown as ImageConfig} src={block.media_path ?? null} />;
    default:
      return <p className="rounded-xl bg-lavender px-4 py-3 text-sm text-muted">This part of the lesson ({block.block_type}) can&apos;t be shown here yet.</p>;
  }
}

export function LessonBody({ blocks }: { blocks: Block[] }) {
  const visible = blocks.filter((b) => !(b.block_type === "text" && !(b.config as TextConfig).body?.trim() && !(b.config as TextConfig).heading?.trim()));
  if (!visible.length) return <p className="text-muted">This lesson has no content yet.</p>;
  return <div className="grid gap-8">{visible.map((b) => <BlockView key={b.id} block={b} />)}</div>;
}
