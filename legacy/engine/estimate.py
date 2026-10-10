"""Pre-build cost/time estimate so a teacher sees what a build will cost before spending credits."""
from . import db
from .config import PRICES, settings
from .llm import gateway
from .models import Goal


def estimate(course: dict) -> dict:
    from .pipeline import QUALITY, scope_units  # local import: pipeline imports this module's callers
    profile = db.get_doc(course["id"], "profile")
    if not profile:
        return {"available": False, "reason": "Analyse the content first."}
    goal = Goal(**course["data"]["goal"])
    tiers = QUALITY[course["data"]["settings"]["quality"]]
    units = scope_units(course, profile)
    cached = set(db.list_docs(course["id"], "unit_knowledge"))
    todo = [u for u in units if u["id"] not in cached]
    objectives = max(3, min(40, round(goal.time_budget_minutes / 9)))
    activities = round(objectives * 4.4)
    # (stage, calls, input tokens per call, output tokens per call)
    plan = [
        ("extract", len(todo), None, 1800),
        ("graph", 1, 9000, 3000),
        ("curriculum", 1, 16000, 4000),
        ("plan", objectives, 1600, 500),
        ("generate", round(activities * 1.1), 4600, 1100),
        ("verify", activities, 3200, 400),
    ]
    rows, total_cost, known = [], 0.0, True
    for stage, calls, tin, tout in plan:
        model = gateway.model_for(tiers[stage])
        tin_total = sum(u["tokens"] + 900 for u in todo) if tin is None else calls * tin
        tout_total = calls * tout
        price = PRICES.get(model)
        cost = (tin_total * price[0] + tout_total * price[1]) / 1e6 if price else None
        if cost is None:
            known = False
        else:
            total_cost += cost
        rows.append({"stage": stage, "model": model, "calls": calls, "input_tokens": tin_total,
                     "output_tokens": tout_total, "usd": round(cost, 3) if cost is not None else None})
    calls = sum(r["calls"] for r in rows)
    return {"available": True, "units": len(units), "units_cached": len(units) - len(todo),
            "objectives_estimate": objectives, "activities_estimate": activities, "calls": calls,
            "usd": round(total_cost, 2) if known else None, "rows": rows,
            "minutes_estimate": max(1, round(calls * 12 / max(1, settings.max_parallel) / 60)),
            "ai_status": gateway.status}
