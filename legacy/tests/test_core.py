"""Core engine tests that run offline (mock provider). Run: python -m pytest tests -q"""
import os
import tempfile

os.environ["LLM_PROVIDER"] = "mock"

import pytest  # noqa: E402

from engine.activities import grade_auto, structural_issues, _expr_ok  # noqa: E402
from engine.ingest.text import parse_markdown, parse_plain  # noqa: E402
from engine.planner import eligible, stages_for  # noqa: E402
from engine.models import Goal  # noqa: E402


def test_mcq_grading_single_and_multi():
    opts = [{"text": "a", "correct": True, "rationale": ""}, {"text": "b", "correct": False, "rationale": ""},
            {"text": "c", "correct": True, "rationale": ""}]
    assert grade_auto("mcq", {"options": opts}, {"selected": [0, 2]})["correct"] is True
    partial = grade_auto("mcq", {"options": opts}, {"selected": [0]})
    assert partial["correct"] is False and 0 < partial["score"] < 1
    assert grade_auto("mcq", {"options": opts}, {"selected": [1]})["score"] == 0


def test_ordering_cloze_numeric_categorize():
    assert grade_auto("ordering", {"items": ["a", "b", "c"]}, {"order": ["a", "b", "c"]})["correct"]
    cl = {"passage": "x [[1]] y [[2]]", "blanks": [{"id": 1, "answers": ["Paris"], "hint": ""},
                                                   {"id": 2, "answers": ["3.5"], "hint": ""}]}
    r = grade_auto("cloze", cl, {"blanks": {"1": " paris ", "2": "3.50"}})
    assert r["correct"], r
    assert grade_auto("numeric_problem", {"answer": 9.81, "tolerance": 0.05}, {"value": "9.8"})["correct"]
    cat = {"items": [{"text": "x", "category": "A", "why": ""}, {"text": "x", "category": "B", "why": ""}]}
    assert grade_auto("categorize", cat, {"assign": {"0": "A", "1": "B"}})["correct"]


def test_structural_checks_catch_malformed_activities():
    assert structural_issues("mcq", {"options": [{"text": "a", "correct": False, "rationale": ""},
                                                 {"text": "b", "correct": False, "rationale": ""}], "multiple": False})
    assert structural_issues("cloze", {"passage": "a [[1]]", "blanks": [{"id": 2, "answers": ["x"], "hint": ""}]})
    sc = {"context": "", "start_node": "n1", "debrief": "",
          "nodes": [{"id": "n1", "text": "", "choices": [{"text": "go", "next_node": "n9", "feedback": "", "quality": "best"}]}]}
    assert any("missing nodes" in i for i in structural_issues("scenario", sc))


def test_expression_sandbox():
    assert _expr_ok("0.5*m*v^2", {"m", "v"}) is None
    assert _expr_ok("sqrt(g*L)/(2*pi)", {"g", "L"}) is None
    assert _expr_ok('__import__("os")', set())
    assert _expr_ok("a.b", {"a"})
    assert _expr_ok("unknown*2", set())


def test_markdown_parser_structure_and_mdx_cleanup():
    md = ("> ## Documentation Index\n# Title\n\nIntro para.\n\n<Tip>\n  A tip\n</Tip>\n\n## Setup\n\n```python\nx = 1\n```\n\n"
          "- one\n- two\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\nexport const X = () => {\n  return 1;\n};\n\nAfter.")
    b = parse_markdown(md, "doc.md")
    kinds = [e.kind for e in b.elements]
    assert b.title == "Title"
    assert "code" in kinds and "table" in kinds and kinds.count("list_item") == 2
    assert not any("Documentation Index" in e.text or "export const" in e.text or "<Tip>" in e.text for e in b.elements)
    assert b.elements[-1].section_path == ["Title", "Setup"]


def test_plain_text_headings():
    b = parse_plain("THE WATER CYCLE\n\nWater evaporates.\n\n1. Evaporation\n2. Condensation", "notes")
    assert b.elements[0].kind == "heading" and b.elements[0].text == "The Water Cycle"
    assert [e.kind for e in b.elements].count("list_item") == 2


@pytest.mark.parametrize("purpose", ["understand", "apply", "exam_prep", "certification", "revision", "onboarding",
                                     "teach_others"])
def test_planner_eligibility_respects_assets(purpose):
    g = Goal(purpose=purpose)
    no_assets = {"code": False, "formula": False, "sequence": False, "events": False, "figure": False,
                 "multi_concept": False, "asset_3d": False}
    for stage in stages_for(g, 10):
        for kt in ("code", "quantitative", "chronology", "concept"):
            types = eligible(stage, kt, g, no_assets, "openai")
            assert types, (stage, kt)
            assert not {"code_walkthrough", "find_the_bug", "parameter_explorer", "numeric_problem", "timeline",
                        "diagram_label", "model_3d"} & set(types), (stage, kt, types)


def test_bkt_mastery_moves_in_the_right_direction(tmp_path, monkeypatch):
    from engine import config
    monkeypatch.setattr(config.settings, "data_dir", tmp_path)
    from engine import learner as L
    course = {"id": "c1", "data": {"goal": {"audience_level": "beginner", "purpose": "understand"}}}
    m1 = L.update_mastery("l1", course, "o1", 1.0, 0.5, 0, 4)
    m2 = L.update_mastery("l1", course, "o1", 1.0, 0.5, 0, 4)
    assert m2["p"] > m1["p"] > 0.15
    m3 = L.update_mastery("l1", course, "o1", 0.0, 0.5, 0, 4)
    assert m3["p"] < m2["p"]
    hinted = L.update_mastery("l2", course, "o1", 1.0, 0.5, 3, 4)
    assert hinted["p"] < m1["p"]  # a heavily hinted success is weaker evidence


def test_item_analysis_flags_miskeyed_item(tmp_path, monkeypatch):
    import random
    from engine import config, db
    monkeypatch.setattr(config.settings, "data_dir", tmp_path)
    db._local.conn = None  # fresh connection in the temp dir
    db._initialised = False
    from engine.analytics import item_analysis
    opts = [{"text": "right", "correct": True, "rationale": ""}, {"text": "wrong", "correct": False, "rationale": ""},
            {"text": "never", "correct": False, "rationale": ""}]
    good = {"title": "good", "payload": {"options": opts}}
    with db.tx() as c:
        for aid, data in (("a_good", good), ("a_bad", good), ("x1", good), ("x2", good), ("x3", good)):
            c.execute("INSERT INTO activities VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                      (aid, "c", "o1", "mcq", "check", 0, db.dumps(data), "approved", None, 0, 0))
        rnd = random.Random(1)
        for i in range(20):
            strong = i < 10
            c.execute("INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                      (f"g{i}", f"l{i}", "c", "a_good", "o1", db.dumps({"selected": [0 if strong else 1]}),
                       1.0 if strong else 0.0, int(strong), 0, None, i))
            for k in ("x1", "x2", "x3"):  # anchor items that define overall ability
                c.execute("INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                          (f"{k}{i}", f"l{i}", "c", k, "o1", db.dumps({"selected": [0 if strong else 1]}),
                           1.0 if strong else 0.0, int(strong), 0, None, i + 50))
            # the 'bad' item is answered 'correctly' mostly by weak learners → negative discrimination
            ok = (not strong) and rnd.random() < 0.9
            c.execute("INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                      (f"b{i}", f"l{i}", "c", "a_bad", "o1", db.dumps({"selected": [0 if ok else 1]}),
                       1.0 if ok else 0.0, int(ok), 0, None, i + 100))
    res = {r["activity_id"]: r for r in item_analysis("c")}
    assert res["a_good"]["discrimination"] > 0.5
    assert any("negative discrimination" in f for f in res["a_bad"]["flags"])
    assert any("never chosen" in f for f in res["a_good"]["flags"])
    db._local.conn = None


def test_qti_export_and_bundle_roundtrip(tmp_path, monkeypatch):
    import io
    import xml.dom.minidom
    import zipfile
    from engine import config, db
    monkeypatch.setattr(config.settings, "data_dir", tmp_path)
    (tmp_path / "media").mkdir()
    (tmp_path / "uploads").mkdir()
    db._local.conn = None
    db._initialised = False
    from engine.activities import REGISTRY, envelope
    from engine.export import export_bundle, import_bundle, qti_zip
    from engine.generate import save_activity
    from engine.ingest import ingest_text
    from engine.llm import mock_instance
    from engine import pipeline as P
    src = ingest_text("# Water\n\nWater evaporates [x]. Clouds form.\n\n## Rain\n\nRain falls.", "Water")
    eid = db.conn().execute("SELECT id FROM elements WHERE source_id=? AND kind='paragraph'", (src["id"],)).fetchone()[0]
    c = P.create_course("T", [src["id"]], {}, {})
    types = ["mcq", "ordering", "matching", "numeric_problem", "cloze", "short_answer", "predict", "explainer"]
    for i, k in enumerate(types):
        data = mock_instance(envelope(k), f"[{eid}] water").model_dump()
        if k == "cloze":
            data["payload"] = {"passage": "Water [[1]] and [[2]].", "blanks": [
                {"id": 1, "answers": ["evaporates"], "hint": ""}, {"id": 2, "answers": ["condenses"], "hint": ""}]}
        data["evidence"] = [eid]
        data["title"] = f"see [{eid}]"
        save_activity(c["id"], "obj1", {"stage": "check", "activity_type": k}, i, data, None, "approved")
    blob, n = qti_zip(c["id"])
    assert n == 7  # every type except the explainer
    z = zipfile.ZipFile(io.BytesIO(blob))
    for name in z.namelist():
        xml.dom.minidom.parseString(z.read(name))  # well-formed XML
    b = export_bundle(c["id"])
    new = import_bundle(b)
    acts = db.rows(db.conn().execute("SELECT * FROM activities WHERE course_id=?", (new,)))
    assert len(acts) == len(types)
    new_eid = acts[0]["data"]["evidence"][0]
    assert new_eid != eid and f"[{new_eid}]" in acts[0]["data"]["title"]
    assert db.conn().execute("SELECT count(*) FROM elements WHERE id=?", (new_eid,)).fetchone()[0] == 1
    db._local.conn = None


def test_every_engine_module_imports():
    import importlib
    import pkgutil
    import engine
    for m in pkgutil.walk_packages(engine.__path__, "engine."):
        importlib.import_module(m.name)


def test_translation_shape_guard():
    from engine.translate import same_shape
    a = {"question": "What is [e1]?", "options": [{"text": "x", "correct": True, "rationale": "r"}], "code": "x=1"}
    ok = {"question": "क्या है [e1]?", "options": [{"text": "य", "correct": True, "rationale": "र"}], "code": "x=1"}
    assert same_shape(a, ok)
    assert not same_shape(a, {**ok, "options": [{"text": "y", "correct": False, "rationale": "r"}]})  # answer changed
    assert not same_shape(a, {**ok, "code": "y=1"})  # code changed
    assert not same_shape(a, {**ok, "question": "What is it?"})  # citation dropped


def test_evidence_report_and_qti_import(tmp_path, monkeypatch):
    import time as _t
    from engine import config, db
    monkeypatch.setattr(config.settings, "data_dir", tmp_path)
    db._local.conn = None
    db._initialised = False
    from engine import evidence as E
    from engine.export import qti_item
    import io
    import zipfile
    # QTI import round-trip through our own exporter
    act = {"id": "a1", "type": "mcq", "data": {"title": "t", "payload": {"question": "2+2?", "options": [
        {"text": "3", "correct": False, "rationale": ""}, {"text": "4", "correct": True, "rationale": ""}]}}}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("items/a1.xml", qti_item(act))
    items = E.parse_qti_zip(buf.getvalue())
    assert items == [{"question": "2+2?", "options": [{"text": "3", "correct": False}, {"text": "4", "correct": True}]}]
    course = {"id": "c1", "data": {"settings": {"experiment": {"enabled": True}}}}
    pre = E.save_assessment("c1", {"kind": "pre", "items": items * 1})
    post = E.save_assessment("c1", {"kind": "post", "items": items})
    arms = {}
    for i in range(40):
        lid = f"l{i}"
        arm = E.arm_for(course, lid)
        arms[arm] = arms.get(arm, 0) + 1
        E.submit(course, lid, pre["id"], {"q1": [0]})  # everyone wrong at pre
        E.submit(course, lid, post["id"], {"q1": [1] if (arm == "adaptive" or i % 3 == 0) else [0]})
    assert arms["adaptive"] > 5 and arms["static"] > 5
    r = E.report("c1")
    assert r["arms"]["adaptive"]["gain_mean"] == 1.0
    assert r["arms"]["adaptive"]["gain_mean"] > r["arms"]["static"]["gain_mean"]
    assert r["effect_size_d"] > 0
    assert E.pending_assessment(course, "new_learner", False)["kind"] == "pre"
    db._local.conn = None


def test_micro_quality_rules():
    from engine.micro import check_module, reading_grade
    assert reading_grade("Tax farmers collected taxes. They kept a big share. So the king got less money.") < 8
    assert reading_grade("The fiscal apparatus of the ancien regime, characterised by venal office-holding and "
                         "privileged exemptions, systematically constrained revenue elasticity.") > 14
    vis = {"kind": "none", "prompt": "", "items": [], "code": "", "figure_id": ""}
    base = {"title": "Idea", "text": "Short text.", "narration": "", "visual": vis, "options": [], "pairs": [],
            "buckets": [], "bucket_items": [], "steps": [], "statements": [], "blank_sentence": "", "blank_answers": [],
            "question": "", "model_answer": "", "sources": []}
    flow = {**vis, "kind": "flow", "items": ["a", "b"]}
    ok_opts = [{"text": "a", "correct": True, "why": ""}, {"text": "b", "correct": False, "why": ""},
               {"text": "c", "correct": False, "why": ""}]
    cards = [dict(base, kind="hook", visual={**vis, "kind": "illustration", "prompt": "a picture of a bakery queue"}),
             dict(base, kind="concept", visual=flow), dict(base, kind="check", options=ok_opts),
             dict(base, kind="concept", visual=flow), dict(base, kind="check", options=ok_opts),
             dict(base, kind="example", visual=flow), dict(base, kind="check", options=ok_opts),
             dict(base, kind="apply", question="q", model_answer="a"), dict(base, kind="recap", steps=["x", "y"])]
    flash = [{"front": "f", "back": "b"}] * 3
    assert check_module(cards, flash, "beginner") == []
    bad = [dict(c) for c in cards]
    bad[1] = dict(bad[1], visual=vis, text=" ".join(["word"] * 60))
    bad[2] = dict(bad[2], options=[dict(o, correct=True) for o in ok_opts])
    issues = " ".join(check_module(bad, flash, "beginner"))
    assert "need a visual" in issues and "max 40" in issues and "exactly one correct" in issues
