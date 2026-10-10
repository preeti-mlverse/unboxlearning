"""Interoperability: QTI 2.1 question-bank export and portable course bundles (export/import)."""
import io
import re
import time
import zipfile
from xml.sax.saxutils import escape

from . import db

QTI_NS = ('xmlns="http://www.imsglobal.org/xsd/imsqti_v2p1" '
          'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
          'xsi:schemaLocation="http://www.imsglobal.org/xsd/imsqti_v2p1 http://www.imsglobal.org/xsd/qti/qtiv2p1/imsqti_v2p1.xsd"')
MATCH = "http://www.imsglobal.org/question/qti_v2p1/rptemplates/match_correct"


def _t(s) -> str:
    """Plain text for XML: drop citation markers and markdown emphasis."""
    s = re.sub(r"\[e\d+\]", "", str(s or ""))
    s = re.sub(r"[*_`]{1,3}", "", s)
    return escape(s.strip())


def _item(ident: str, title: str, decls: str, body: str, processing: str = f'<responseProcessing template="{MATCH}"/>') -> str:
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<assessmentItem {QTI_NS} identifier="{ident}" title="{_t(title)}" '
            f'adaptive="false" timeDependent="false">\n{decls}\n'
            f'<outcomeDeclaration identifier="SCORE" cardinality="single" baseType="float"/>\n'
            f'<itemBody>\n{body}\n</itemBody>\n{processing}\n</assessmentItem>\n')


def qti_item(a: dict) -> str | None:
    t, p, ident = a["type"], a["data"]["payload"], a["id"]
    title = a["data"].get("title") or t
    if t in ("mcq", "predict"):
        opts = p["options"]
        multiple = sum(o["correct"] for o in opts) > 1
        card = "multiple" if multiple else "single"
        correct = "".join(f"<value>C{i}</value>" for i, o in enumerate(opts) if o["correct"])
        prompt = p.get("question", "")
        if t == "predict":
            prompt = f'{p["setup"]}\n\n{p["question"]}'
        choices = "".join(f'<simpleChoice identifier="C{i}">{_t(o["text"])}</simpleChoice>' for i, o in enumerate(opts))
        decl = (f'<responseDeclaration identifier="RESPONSE" cardinality="{card}" baseType="identifier">'
                f'<correctResponse>{correct}</correctResponse></responseDeclaration>')
        body = (f'<choiceInteraction responseIdentifier="RESPONSE" shuffle="true" maxChoices="{0 if multiple else 1}">'
                f'<prompt>{_t(prompt)}</prompt>{choices}</choiceInteraction>')
        return _item(ident, title, decl, body)
    if t == "ordering":
        items = p["items"]
        decl = ('<responseDeclaration identifier="RESPONSE" cardinality="ordered" baseType="identifier"><correctResponse>'
                + "".join(f"<value>O{i}</value>" for i in range(len(items))) + "</correctResponse></responseDeclaration>")
        body = (f'<orderInteraction responseIdentifier="RESPONSE" shuffle="true"><prompt>{_t(p["prompt"])}</prompt>'
                + "".join(f'<simpleChoice identifier="O{i}">{_t(x)}</simpleChoice>' for i, x in enumerate(items))
                + "</orderInteraction>")
        return _item(ident, title, decl, body)
    if t == "matching":
        pairs = p["pairs"]
        decl = ('<responseDeclaration identifier="RESPONSE" cardinality="multiple" baseType="directedPair"><correctResponse>'
                + "".join(f"<value>L{i} R{i}</value>" for i in range(len(pairs))) + "</correctResponse></responseDeclaration>")
        left = "".join(f'<simpleAssociableChoice identifier="L{i}" matchMax="1">{_t(x["left"])}</simpleAssociableChoice>'
                       for i, x in enumerate(pairs))
        right = "".join(f'<simpleAssociableChoice identifier="R{i}" matchMax="1">{_t(x["right"])}</simpleAssociableChoice>'
                        for i, x in enumerate(pairs))
        body = (f'<matchInteraction responseIdentifier="RESPONSE" shuffle="true" maxAssociations="{len(pairs)}">'
                f'<prompt>{_t(p["prompt"])}</prompt><simpleMatchSet>{left}</simpleMatchSet>'
                f'<simpleMatchSet>{right}</simpleMatchSet></matchInteraction>')
        return _item(ident, title, decl, body)
    if t == "numeric_problem":
        decl = ('<responseDeclaration identifier="RESPONSE" cardinality="single" baseType="float">'
                f'<correctResponse><value>{p["answer"]}</value></correctResponse></responseDeclaration>')
        body = (f'<p>{_t(p["question"])}</p><p><textEntryInteraction responseIdentifier="RESPONSE" expectedLength="12"/> '
                f'{_t(p["unit"])}</p>')
        proc = ('<responseProcessing><responseCondition><responseIf><equal toleranceMode="absolute" '
                f'tolerance="{p["tolerance"]} {p["tolerance"]}"><variable identifier="RESPONSE"/><correct identifier="RESPONSE"/>'
                '</equal><setOutcomeValue identifier="SCORE"><baseValue baseType="float">1</baseValue></setOutcomeValue>'
                '</responseIf></responseCondition></responseProcessing>')
        return _item(ident, title, decl, body, proc)
    if t == "cloze":
        decls, passage = [], _t(p["passage"])
        for b in p["blanks"]:
            rid = f"RESPONSE_{b['id']}"
            mapping = "".join(f'<mapEntry mapKey="{escape(x)}" mappedValue="1"/>' for x in b["answers"])
            decls.append(f'<responseDeclaration identifier="{rid}" cardinality="single" baseType="string">'
                         f'<correctResponse><value>{escape(b["answers"][0])}</value></correctResponse>'
                         f'<mapping defaultValue="0">{mapping}</mapping></responseDeclaration>')
            passage = passage.replace(f"[[{b['id']}]]", f'<textEntryInteraction responseIdentifier="{rid}" expectedLength="15"/>')
        sums = "".join(f'<mapResponse identifier="RESPONSE_{b["id"]}"/>' for b in p["blanks"])
        proc = (f'<responseProcessing><setOutcomeValue identifier="SCORE"><sum>{sums}</sum></setOutcomeValue>'
                '</responseProcessing>')
        return _item(ident, title, "\n".join(decls), f"<p>{passage}</p>", proc)
    if t in ("short_answer", "teach_back"):
        q = p.get("question") or p.get("prompt")
        rubric = "".join(f"<li>{_t(r['criterion'])} ({r['points']})</li>" for r in p["rubric"])
        model = _t(p.get("model_answer") or "; ".join(p.get("must_include", [])))
        decl = '<responseDeclaration identifier="RESPONSE" cardinality="single" baseType="string"/>'
        body = (f'<rubricBlock view="scorer"><p>Model answer: {model}</p><ul>{rubric}</ul></rubricBlock>'
                f'<extendedTextInteraction responseIdentifier="RESPONSE" expectedLines="6"><prompt>{_t(q)}</prompt>'
                f'</extendedTextInteraction>')
        return _item(ident, title, decl, body, "")
    return None


def qti_zip(course_id: str, include_unapproved: bool = False) -> tuple[bytes, int]:
    q = "SELECT * FROM activities WHERE course_id=?" + ("" if include_unapproved else " AND status='approved'")
    acts = db.rows(db.conn().execute(q + " ORDER BY objective_id, ord", (course_id,)))
    buf = io.BytesIO()
    resources, n = [], 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for a in acts:
            xml = qti_item(a)
            if not xml:
                continue
            fname = f"items/{a['id']}.xml"
            z.writestr(fname, xml)
            resources.append(f'<resource identifier="R_{a["id"]}" type="imsqti_item_xmlv2p1" href="{fname}">'
                             f'<file href="{fname}"/></resource>')
            n += 1
        z.writestr("imsmanifest.xml",
                   '<?xml version="1.0" encoding="UTF-8"?>\n<manifest xmlns="http://www.imsglobal.org/xsd/imscp_v1p1" '
                   f'identifier="MANIFEST_{course_id}"><organizations/><resources>{"".join(resources)}</resources></manifest>\n')
    return buf.getvalue(), n


# ----------------------------------------------------------------------------- course bundles

BUNDLE_VERSION = 1


def export_bundle(course_id: str) -> dict:
    c = db.row(db.conn().execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone())
    sids = c["data"]["source_ids"]
    ph = ",".join("?" * len(sids))
    return {
        "bundle_version": BUNDLE_VERSION, "exported_at": time.time(),
        "course": {"title": c["title"], "status": c["status"], "data": c["data"]},
        "docs": [{"kind": r["kind"], "key": r["key"], "data": db.loads(r["data"])} for r in db.conn().execute(
            "SELECT kind, key, data FROM course_docs WHERE course_id=?", (course_id,))],
        "activities": db.rows(db.conn().execute("SELECT * FROM activities WHERE course_id=?", (course_id,))),
        "sources": db.rows(db.conn().execute(f"SELECT * FROM sources WHERE id IN ({ph})", sids)),
        "elements": db.rows(db.conn().execute(f"SELECT * FROM elements WHERE source_id IN ({ph}) ORDER BY source_id, ord",
                                              sids)),
    }


def import_bundle(bundle: dict) -> str:
    """Recreate a course from a bundle. Element ids are global per install, so they are remapped and every
    reference (evidence lists and inline [eN] citations) is rewritten."""
    from .index import index_source
    if bundle.get("bundle_version") != BUNDLE_VERSION:
        raise ValueError("unsupported bundle version")
    els = bundle["elements"]
    first = db.reserve("element", max(len(els), 1))
    emap = {e["id"]: f"e{first + i}" for i, e in enumerate(els)}
    smap = {s["id"]: db.new_id("src") for s in bundle["sources"]}

    def remap(obj):
        s = db.dumps(obj)
        s = re.sub(r'"(e\d+)"', lambda m: f'"{emap.get(m.group(1), m.group(1))}"', s)
        s = re.sub(r"\[(e\d+)\]", lambda m: f"[{emap.get(m.group(1), m.group(1))}]", s)
        for old, new in smap.items():
            s = s.replace(old, new)
        return db.loads(s)

    now = time.time()
    with db.tx() as c:
        for s in bundle["sources"]:
            c.execute("INSERT INTO sources VALUES(?,?,?,?,?,?,?,?,?)",
                      (smap[s["id"]], s["title"], s["kind"], s["origin"], s["sha256"] + ":imported", s["language"],
                       "parsed", db.dumps(s["meta"]), now))
        for e in els:
            c.execute("INSERT INTO elements VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                      (emap[e["id"]], smap[e["source_id"]], e["ord"], e["kind"], e["level"], e["text"], e["page"],
                       db.dumps(e["section_path"]), db.dumps(e["bbox"]) if e["bbox"] else None, e["media_path"],
                       e["confidence"], db.dumps(e["meta"])))
    for sid in smap.values():
        index_source(sid)
    cid = db.new_id("crs")
    course = remap(bundle["course"])
    with db.tx() as c:
        c.execute("INSERT INTO courses VALUES(?,?,?,?,?,?)",
                  (cid, course["title"], db.dumps(course["data"]), course["status"], now, now))
        for d in bundle["docs"]:
            c.execute("INSERT INTO course_docs VALUES(?,?,?,?,?)",
                      (cid, d["kind"], remap(d["key"]) if d["key"] else "", db.dumps(remap(d["data"])), now))
        for a in bundle["activities"]:
            c.execute("INSERT INTO activities VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                      (db.new_id("act"), cid, a["objective_id"], a["type"], a["stage"], a["ord"],
                       db.dumps(remap(a["data"])), a["status"], db.dumps(a["verify"]) if a["verify"] else None, now, now))
    return cid
