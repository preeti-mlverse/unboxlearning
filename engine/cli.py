"""Command line: python -m engine.cli <command>

  models                         check the API key and list usable chat/embedding models
  ingest <path-or-url> [--crawl] ingest a source and print its parse summary
  course <source_id...> [--purpose apply] [--minutes 60] [--goal "..."]   analyse + build, printing progress
"""
import argparse
import json
import sys
import time

from . import db, pipeline as P
from .config import settings
from .llm import gateway


def cmd_models(_):
    print(f"provider={gateway.provider} fast={settings.model_fast} standard={settings.model_standard} "
          f"premium={settings.model_premium} embed={settings.embed_model}")
    if gateway.provider != "openai":
        print("Set OPENAI_API_KEY in .env to use OpenAI.")
        return
    ids = sorted(m.id for m in gateway.openai.models.list())
    print("available:", ", ".join(i for i in ids if i.startswith(("gpt", "o", "text-embedding", "whisper", "tts"))))
    for tier in ("fast", "standard", "premium"):
        m = gateway.model_for(tier)
        print(f"  {tier:8} {m:28} {'OK' if m in ids else 'NOT AVAILABLE — set MODEL_' + tier.upper()}")
    from pydantic import BaseModel

    class Ping(BaseModel):
        ok: bool
        note: str

    t = time.time()
    r = gateway.structured(Ping, "Reply with ok=true.", "ping", tier="fast", purpose="ping")
    print(f"structured call OK ({time.time() - t:.1f}s): {r}")


def cmd_ingest(a):
    from .ingest import ingest_file, ingest_url
    s = ingest_url(a.target, crawl=a.crawl) if a.target.startswith("http") else ingest_file(a.target)
    print(json.dumps({"id": s["id"], "title": s["title"], "kind": s["kind"], "stats": s["meta"]["stats"],
                      "notes": s["meta"]["parse_notes"]}, indent=2))


def cmd_course(a):
    goal = {"purpose": a.purpose, "time_budget_minutes": a.minutes, "specific_goals": a.goal or [],
            "audience_level": a.level}
    c = P.create_course("Untitled course", a.sources, goal, {"quality": a.quality, "auto_approve": a.auto})
    print("course", c["id"])
    for step in (P.analyse, P.build):
        step(c["id"])
        last = ""
        while True:
            j = P.latest_job(c["id"])
            if j["message"] != last:
                print(f"  [{j['stage']:10}] {j['progress']:.0%} {j['message']}")
                last = j["message"]
            if j["status"] != "running":
                break
            time.sleep(1)
        if j["status"] == "failed":
            sys.exit(1)
    rows = db.rows(db.conn().execute("SELECT type, status, count(*) n FROM activities WHERE course_id=? "
                                     "GROUP BY type, status", (c["id"],)))
    print(json.dumps(rows, indent=1))


def cmd_gallery(_):
    """Seed a QA course with one schema-valid placeholder activity of every enabled type."""
    from .activities import REGISTRY, envelope
    from .generate import save_activity
    from .ingest import ingest_text
    from .llm import mock_instance
    src = ingest_text("# Renderer gallery\n\nPlaceholder source used to exercise every activity renderer.", "Gallery")
    ctx = "[e1] retrieval augmented generation grounds answers in retrieved documents"
    c = P.create_course("Renderer gallery", [src["id"]], {"purpose": "understand"}, {"auto_approve": True})
    objs = []
    for i, (k, t) in enumerate([(k, t) for k, t in REGISTRY.items() if t.enabled], 1):
        data = mock_instance(envelope(k), ctx).model_dump()
        data["title"] = f"{t.label} ({k})"
        oid = f"obj{i}"
        objs.append({"id": oid, "module_id": "m1", "statement": f"Gallery: {t.label}", "bloom": "understand",
                     "knowledge_type": "concept", "concept_ids": [], "success_criteria": ["renders"],
                     "estimated_minutes": 2, "serves_goals": [], "units": [], "evidence": [], "candidate_ids": []})
        save_activity(c["id"], oid, {"stage": "practice" if "practice" in t.stages else t.stages[0], "activity_type": k},
                      0, data, {"checks": [], "answer_key_correct": "yes", "pedagogy_issues": [], "verdict": "verified"},
                      "approved")
    db.put_doc(c["id"], "curriculum", {"course_title": "Renderer gallery", "learner_promise": "QA every renderer",
                                       "modules": [{"id": "m1", "title": "All activity types", "why": "QA",
                                                    "objective_ids": [o["id"] for o in objs]}],
                                       "objectives": objs, "uncovered_goals": [], "excluded": []})
    db.put_doc(c["id"], "graph", {"concepts": [], "edges": []})
    P.update_course(c["id"], status="ready")
    print(f"gallery course {c['id']} with {len(objs)} activity types")


def main():
    ap = argparse.ArgumentParser(prog="engine")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("models").set_defaults(fn=cmd_models)
    sub.add_parser("gallery").set_defaults(fn=cmd_gallery)
    p = sub.add_parser("ingest")
    p.add_argument("target")
    p.add_argument("--crawl", action="store_true")
    p.set_defaults(fn=cmd_ingest)
    p = sub.add_parser("course")
    p.add_argument("sources", nargs="+")
    p.add_argument("--purpose", default="understand")
    p.add_argument("--level", default="beginner")
    p.add_argument("--minutes", type=int, default=60)
    p.add_argument("--goal", action="append")
    p.add_argument("--quality", default="balanced")
    p.add_argument("--auto", action="store_true")
    p.set_defaults(fn=cmd_course)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
