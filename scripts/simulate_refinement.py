"""Simulate one week of backlog refinement on top of a mock backlog, for demos and tests only.

Each team's Product Owner works top-down: the highest-ranked tickets that are not Ready get their missing
detail filled in (and an updated date). Two new, thin tickets per team are also added, because real
backlogs keep growing. Nothing here is real JIRA data.

  python3 scripts/simulate_refinement.py data/mock_backlog.json data/mock_backlog_week1.json
"""
import copy
import json
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import generate_mock_backlog as gen  # noqa: E402
from backlog_readiness.analyze import analyze  # noqa: E402


INTAKE = {
    "team_alpha": ["Review stale payment webhooks", "Add audit log for settings changes", "Confirm refund policy copy", "Retire legacy invoice template", "Check card brand icon assets", "Document password reset flow"],
    "team_bravo": ["Tune retry backoff for SMS vendor", "Add alert for queue lag", "Review unsubscribe link handling", "Trim old notification logs", "Check quiet hours across regions", "Map vendor error codes"],
    "team_charlie": ["Validate currency rounding in reports", "Add row count check to nightly load", "Review slow report queries", "Rename ambiguous dashboard tiles", "Reconcile fiscal calendar table", "Remove unused report filters"],
}


def refine(data, days=7, per_team=4, new_per_team=2):
    out = copy.deepcopy(data)
    new_as_of = date.fromisoformat(out["meta"]["as_of"]) + timedelta(days=days)
    out["meta"]["as_of"] = new_as_of.isoformat()
    out["meta"]["note"] = "SIMULATED refinement week for demo purposes. Not real JIRA data."
    scored = {t["key"]: t for t in analyze(out)["tickets"]}
    gen.rnd.seed(new_as_of.toordinal())

    for tid, team in gen.TEAMS.items():
        rows = sorted((t for t in out["tickets"] if t["team_id"] == tid), key=lambda r: r["rank"])
        todo = [t for t in rows if scored[t["key"]]["tier"] != "Ready" and not t.get("blocked_by")][:per_team]
        files = {topic: fp for topic, fp in gen.T[tid].get("Tech Debt", [])}
        for t in todo:
            fixed = gen.build_fields(t["type"], t["summary"], team, True, None, t["rank"], files.get(t["summary"]))
            t.update(fixed)
            t["updated"] = new_as_of.isoformat()

        last = max(t["rank"] for t in rows)
        nxt = max(int(t["key"].split("-")[1]) for t in rows) + 1
        for i in range(new_per_team):
            used = {t["summary"] for t in out["tickets"]}
            summary = next(s for s in INTAKE[tid] if s not in used)
            out["tickets"].append(dict(
                key=f"{team['prefix']}-{nxt + i}", team_id=tid, team=team["name"], type="Task",
                summary=summary, status="Backlog", rank=last + 1 + i,
                priority="Medium", story_points=None, parent=None, severity=None, blocked_by=None,
                created=new_as_of.isoformat(), updated=new_as_of.isoformat(), description="Follow up", acceptance_criteria="",
                assignee=None, start_date=None))
    return out


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    with open(sys.argv[1]) as fh:
        base = json.load(fh)
    result = refine(base)
    with open(sys.argv[2], "w") as fh:
        json.dump(result, fh, indent=1)
    print("Wrote", sys.argv[2], "as of", result["meta"]["as_of"], f"({len(result['tickets'])} tickets)")
