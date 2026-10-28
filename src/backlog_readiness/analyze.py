"""Score every ticket and roll the results up to team and program level."""
import re
from datetime import date

from .config import Config, TIERS, TYPES
from .rules import check, tier_for, is_blocker_gap

DONE = {"done", "closed", "resolved", "released"}
STOP = {"a", "an", "the", "to", "as", "for", "in", "of", "on", "and", "with", "file", "spike"}


def _pct(n, d):
    return round(100 * n / d, 1) if d else None


def _tokens(s):
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP}


def find_duplicates(tickets, threshold):
    dups = {}
    for i, a in enumerate(tickets):
        ta = _tokens(a["summary"])
        for b in tickets[i + 1:]:
            tb = _tokens(b["summary"])
            if ta and tb and len(ta & tb) / len(ta | tb) >= threshold:
                dups.setdefault(a["key"], []).append(b["key"])
                dups.setdefault(b["key"], []).append(a["key"])
    return dups


def summarize(rows):
    c = {k: sum(1 for r in rows if r["tier"] == k) for k in TIERS}
    n = len(rows)
    return {
        "total": n, **c,
        "ready_pct": _pct(c["Ready"], n), "almost_pct": _pct(c["Almost ready"], n), "not_ready_pct": _pct(c["Not ready"], n),
        "stale_6m": sum(1 for r in rows if r["stale_6m"]),
        "stale_6m_not_ready": sum(1 for r in rows if r["stale_6m"] and r["tier"] != "Ready"),
        "untouched": sum(1 for r in rows if r["untouched"]),
        "blocked": sum(1 for r in rows if r.get("blocked")),
        "split_candidates": sum(1 for r in rows if (r.get("story_points") or 0) >= OVERSIZE[0]),
    }


OVERSIZE = [8]


def analyze(data, cfg: Config = Config(), as_of=None):
    """data: {"meta": {"as_of", "teams": {id: {"name", "velocity"}}}, "tickets": [...]}"""
    as_of = date.fromisoformat(as_of or data["meta"]["as_of"])
    OVERSIZE[0] = cfg.oversize_points
    teams_meta = data["meta"]["teams"]
    tickets = [dict(t) for t in data["tickets"]]
    dups = find_duplicates(tickets, cfg.dup_similarity)

    status = {**data["meta"].get("external_status", {}), **{t["key"]: (t.get("status") or "") for t in tickets}}
    team_of = {t["key"].split("-")[0]: t["team"] for t in tickets if t.get("team")}
    for t in tickets:
        t.setdefault("team", teams_meta.get(t["team_id"], {}).get("name", t["team_id"]))
        gaps, adv, thin = check(t, cfg)
        b = t.get("blocked_by")
        if b:
            bs = status.get(b, "unknown").replace("_", " ")
            cleared = bs.lower() in DONE
            t["blocker"] = {"key": b, "team": team_of.get(b.split("-")[0]), "status": bs.capitalize(), "open": not cleared}
            if cleared:
                gaps = [g for g in gaps if not is_blocker_gap(g)]
                adv.append(f"Was blocked by {b} (now {bs.capitalize()})")
        t["blocked"] = any(is_blocker_gap(g) for g in gaps)
        if t["key"] in dups:
            adv.append("Possible duplicate of " + ", ".join(dups[t["key"]]))
        age = (as_of - date.fromisoformat(t["created"])).days
        since = (as_of - date.fromisoformat(t["updated"])).days
        t["age_days"], t["days_since_update"] = age, since
        t["stale_6m"] = age >= cfg.stale_days
        t["untouched"] = since >= cfg.untouched_days
        t["age_tier"] = (">12 months" if age > 365 else "6-12 months" if t["stale_6m"]
                         else "3-6 months" if age >= 91 else "<3 months")
        if t["untouched"]:
            adv.append(f"Untouched {since} days")
        t["gaps"], t["advisories"], t["tier"] = gaps, adv, tier_for(gaps, thin)

    teams = {}
    for tid, meta in teams_meta.items():
        rows = sorted((t for t in tickets if t["team_id"] == tid), key=lambda r: r["rank"])
        s = summarize(rows)
        s.update(name=meta["name"], velocity=meta["velocity"])

        budget, acc, top = cfg.top_sprints * meta["velocity"], 0, []
        for r in rows:
            if acc >= budget:
                break
            top.append(r)
            acc += r["story_points"] if r.get("story_points") is not None else cfg.unpointed_for_slicing
        s["top_slice"] = {**summarize(top), "points_basis": budget, "keys": [r["key"] for r in top]}

        ready_pts = sum(r["story_points"] for r in rows if r["tier"] == "Ready" and r.get("story_points") is not None)
        s["runway"] = {"ready_points": ready_pts, "sprints": round(ready_pts / meta["velocity"], 1) if meta["velocity"] else None}
        s["next_sprint_candidates"] = {"count": sum(1 for r in rows if r["tier"] == "Almost ready" and not r["blocked"]),
                                       "points": sum(r["story_points"] or 0 for r in rows if r["tier"] == "Almost ready" and not r["blocked"])}
        s["by_type"] = {ty: summarize([r for r in rows if r["type"] == ty]) for ty in TYPES if any(r["type"] == ty for r in rows)}

        freq = {}
        for r in rows:
            for g in r["gaps"]:
                g = re.sub(r"Blocked by .*", "Blocked by another ticket", g)
                freq[g] = freq.get(g, 0) + 1
        s["top_gaps"] = sorted(freq.items(), key=lambda kv: -kv[1])[:6]
        s["oversized"] = sum(1 for r in rows if (r.get("story_points") or 0) >= cfg.oversize_points)
        teams[tid] = s

    program = summarize(tickets)
    program["by_type"] = {ty: summarize([r for r in tickets if r["type"] == ty]) for ty in TYPES}
    program["duplicates"] = sorted({tuple(sorted((k, other))) for k, v in dups.items() for other in v})
    return {"as_of": as_of.isoformat(), "split_at": cfg.oversize_points, "program": program, "teams": teams, "tickets": tickets}
