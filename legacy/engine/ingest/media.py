"""YouTube, audio/video and image sources."""
import re
from pathlib import Path
from typing import Literal

import httpx
from pydantic import BaseModel

from ..llm import gateway
from .base import DocBuilder, save_media

YT = re.compile(r"(?:youtube\.com/(?:watch\?v=|shorts/|embed/|live/)|youtu\.be/)([\w-]{11})")


def youtube_id(url: str) -> str | None:
    m = YT.search(url)
    return m.group(1) if m else None


def _clock(sec: float) -> str:
    sec = int(sec)
    return f"{sec // 3600:02d}:{sec % 3600 // 60:02d}:{sec % 60:02d}" if sec >= 3600 else f"{sec // 60:02d}:{sec % 60:02d}"


def segments_to_builder(title: str, segs: list[dict], origin: str) -> DocBuilder:
    """Group timed segments into ~60s paragraphs under 5-minute sections."""
    b = DocBuilder(title)
    buf, start, section = [], None, -1
    for s in segs:
        if start is None:
            start = s["start"]
        if int(s["start"] // 300) != section:
            if buf:
                b.add("transcript", " ".join(buf), meta={"start": start, "origin": origin})
                buf, start = [], s["start"]
            section = int(s["start"] // 300)
            b.heading(f"{_clock(section * 300)}–{_clock(section * 300 + 300)}", 2, meta={"start": section * 300})
        buf.append(s["text"].strip())
        if s["start"] - start >= 60:
            b.add("transcript", " ".join(buf), meta={"start": start, "origin": origin})
            buf, start = [], None
    if buf:
        b.add("transcript", " ".join(buf), meta={"start": start or 0, "origin": origin})
    return b


def parse_youtube(url: str) -> DocBuilder:
    vid = youtube_id(url)
    from youtube_transcript_api import YouTubeTranscriptApi
    api = YouTubeTranscriptApi()
    fetched = api.fetch(vid, languages=["en", "hi", "en-US", "en-GB"]) if hasattr(api, "fetch") \
        else YouTubeTranscriptApi.get_transcript(vid)
    segs = [{"start": getattr(s, "start", None) if not isinstance(s, dict) else s["start"],
             "text": getattr(s, "text", None) if not isinstance(s, dict) else s["text"]} for s in fetched]
    title = f"YouTube {vid}"
    try:
        title = httpx.get("https://www.youtube.com/oembed", params={"url": url, "format": "json"},
                          timeout=15).json().get("title", title)
    except Exception:  # noqa: BLE001
        pass
    b = segments_to_builder(title, segs, url)
    b.notes.append("text is the video's caption track; timestamps link back to the video")
    return b


def parse_audio(path: Path, title: str | None = None) -> DocBuilder:
    segs = gateway.transcribe(path)
    b = segments_to_builder(title or path.stem, segs, str(path))
    b.notes.append(f"transcribed with speech-to-text")
    return b


class OcrEl(BaseModel):
    kind: Literal["heading", "paragraph", "list_item", "table", "equation", "code", "caption"]
    text: str
    level: int


class OcrOut(BaseModel):
    elements: list[OcrEl]
    figure_description: str


def vision_ocr(media_name: str, _page=None):
    """Transcribe an image-only page with a vision model; returns [(kind, text, level)] or None."""
    if gateway.provider == "mock":
        return None
    from ..config import settings
    out = gateway.structured(
        OcrOut, "You transcribe document page images faithfully, preserving reading order and structure. "
                "Tables as Markdown tables. Do not summarise.",
        "Transcribe this page. Also describe any diagram or figure in figure_description (empty if none).",
        tier="fast", purpose="ocr", images=[settings.media_dir / media_name])
    items = [(e.kind, e.text, e.level or None) for e in out.elements]
    if out.figure_description:
        items.append(("caption", f"Figure: {out.figure_description}", None))
    return items


def parse_image(path: Path, title: str | None = None) -> DocBuilder:
    b = DocBuilder(title or path.stem)
    name = save_media(path.read_bytes(), path.suffix or ".png")
    items = vision_ocr(name)
    b.add("figure", title or path.stem, media_path=name)
    for kind, text, level in items or []:
        if kind == "heading":
            b.heading(text, level or 2)
        else:
            b.add(kind, text, confidence=0.75)
    if not items:
        b.notes.append("image stored; text/diagram reading needs a vision-capable provider")
    return b
