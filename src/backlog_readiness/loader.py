"""Read either input shape: the analyzer's own {"meta","tickets"} file, or the shared portfolio {"cards"} file.

Shared shape: data/cards.json (card_id, title, team_id, team_name, team, feature_id, priority, story_points,
status, ...) with data/teams.json beside it. Only cards with status "backlog" are scored; cards in a
sprint (in_progress, done) are not backlog, but their status decides whether they still block a ticket.
"""
import json
import os



def _team_meta(path):
    with open(path) as fh:
        teams = json.load(fh)["teams"]
    return {t["team_id"]: {"name": t["team_name"], "velocity": t["velocity"], "product_owner": t.get("product_owner"),
                           "engineers": t.get("engineers", []), "active_sprint_id": t.get("active_sprint_id")} for t in teams}


def load(path):
    with open(path) as fh:
        doc = json.load(fh)
    if "tickets" in doc:
        return doc
    if "cards" not in doc:
        raise KeyError("expected a 'tickets' or 'cards' list")
    meta_teams = _team_meta(os.path.join(os.path.dirname(os.path.abspath(path)), "teams.json"))
    tickets, external = [], {}
    for c in doc["cards"]:
        status = c.get("status")
        if status != "backlog":
            external[c["card_id"]] = status
            continue
        tickets.append({
            "key": c["card_id"], "team_id": c["team_id"], "team": c.get("team") or meta_teams[c["team_id"]]["name"],
            "type": c.get("issue_type", "Task"), "summary": c["title"], "status": "Backlog", "rank": c["rank"],
            "priority": c.get("priority"), "story_points": c.get("story_points"), "parent": c.get("feature_id"),
            "severity": c.get("severity"), "blocked_by": c.get("blocked_by"), "created": c["created"], "updated": c["updated"],
            "description": c.get("description"), "acceptance_criteria": c.get("acceptance_criteria"),
            "assignee": c.get("assignee"), "start_date": c.get("start_date"),
        })
    return {"meta": {"as_of": doc["as_of"], "teams": meta_teams, "external_status": external}, "tickets": tickets}
