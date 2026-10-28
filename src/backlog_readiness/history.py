"""Snapshots and run-to-run comparison, so teams can see readiness improve as they refine tickets."""
import json
import os

from .config import TIERS

_RANK = {"Not ready": 0, "Almost ready": 1, "Ready": 2}


def _diff(a, b):
    """b - a rounded to one decimal, or None when either side has no value (empty team, zero velocity)."""
    return None if a is None or b is None else round(b - a, 1)


def save_snapshot(result, directory):
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, f"{result['as_of']}.json")
    with open(path, "w") as fh:
        json.dump(result, fh, indent=1)
    return path


def list_snapshots(directory):
    if not os.path.isdir(directory):
        return []
    return sorted(f[:-5] for f in os.listdir(directory) if f.endswith(".json") and len(f) == 15)


def load_snapshot(directory, as_of):
    with open(os.path.join(directory, f"{as_of}.json")) as fh:
        return json.load(fh)


def latest_before(directory, as_of):
    """The most recent saved snapshot strictly before as_of, or None."""
    earlier = [d for d in list_snapshots(directory) if d < as_of]
    return load_snapshot(directory, earlier[-1]) if earlier else None


def compare(prev, curr):
    """What changed between two runs. Returns a plain dict (no printing)."""
    p = {t["key"]: t for t in prev["tickets"]}
    c = {t["key"]: t for t in curr["tickets"]}
    moved_up, moved_down, gaps_closed = [], [], 0
    for key in sorted(set(p) & set(c)):
        a, b = p[key]["tier"], c[key]["tier"]
        if _RANK[b] > _RANK[a]:
            moved_up.append((key, a, b))
        elif _RANK[b] < _RANK[a]:
            moved_down.append((key, a, b))
        gaps_closed += max(0, len(p[key]["gaps"]) - len(c[key]["gaps"]))
    teams = {}
    for tid, t in curr["teams"].items():
        before = prev["teams"].get(tid)
        teams[tid] = {
            "name": t["name"],
            "ready_pct": t["ready_pct"],
            "ready_pct_change": None if not before else _diff(before["ready_pct"], t["ready_pct"]),
            "runway_change": None if not before else _diff(before["runway"]["sprints"], t["runway"]["sprints"]),
            "top_ready_pct_change": None if not before else _diff(before["top_slice"]["ready_pct"], t["top_slice"]["ready_pct"]),
        }
    return {
        "from": prev["as_of"], "to": curr["as_of"],
        "program_ready_pct_change": _diff(prev["program"]["ready_pct"], curr["program"]["ready_pct"]),
        "teams": teams,
        "moved_up": moved_up, "moved_down": moved_down,
        "newly_ready": [k for k, _, b in moved_up if b == "Ready"],
        "added": sorted(set(c) - set(p)), "removed": sorted(set(p) - set(c)),
        "newly_stale": sorted(k for k in set(p) & set(c) if c[k]["stale_6m"] and not p[k]["stale_6m"]),
        "gaps_closed": gaps_closed,
    }


def trend(directory):
    out = []
    for d in list_snapshots(directory):
        s = load_snapshot(directory, d)
        out.append({"as_of": d, "program_ready_pct": s["program"]["ready_pct"],
                    "teams": {k: v["ready_pct"] for k, v in s["teams"].items()}})
    return out
