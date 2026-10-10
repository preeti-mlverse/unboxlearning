"""Extract the Deep Agents (Python) sidebar order from a docs page's embedded Next.js data."""
import json
import re
import sys

html = open(sys.argv[1], encoding="utf8").read()
chunks = re.findall(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)', html)
s = "".join(json.loads('"' + c + '"') for c in chunks)

anchor = s.find('"href":"/oss/python/deepagents/overview"')
start = s.rfind('{"tab":', 0, anchor)
depth = 0
for end in range(start, len(s)):
    if s[end] == "{":
        depth += 1
    elif s[end] == "}":
        depth -= 1
        if depth == 0:
            break
tab = json.loads(s[start:end + 1])

out = []  # (section path, title, href)


def walk(node, path):
    if isinstance(node, list):
        for n in node:
            walk(n, path)
    elif isinstance(node, dict):
        if "group" in node:
            walk(node.get("pages", []), path + [node["group"]])
        elif "href" in node and "pages" not in node:
            out.append((path, node.get("title") or node.get("sidebarTitle"), node["href"]))
        else:
            for k in ("groups", "pages", "menu", "anchors"):
                if k in node:
                    walk(node[k], path)


walk(tab, [])
json.dump([{"section": p, "title": t, "href": h} for p, t, h in out],
          open(sys.argv[2], "w", encoding="utf8"), indent=1)
for p, t, h in out:
    print(" > ".join(p), "|", t, "|", h)
