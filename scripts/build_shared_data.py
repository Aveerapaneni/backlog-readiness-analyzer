"""Update the shared cards.json in pm-portfolio-mock-data: keep its sprint cards, replace the backlog cards with the
current data/mock_backlog.json, and put the Team custom field on every card.

Usage: python3 scripts/build_shared_data.py
Reads/writes <shared dir>/cards.json and reads <shared dir>/teams.json (shared dir = ../pm-portfolio-mock-data, or
$BACKLOG_SHARED_DIR). Sprint cards keep their fields; backlog cards use status "backlog", sprint_id null, and add
the backlog fields (issue_type, rank, severity, blocked_by, created, updated, description, acceptance_criteria,
assignee, start_date).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
from backlog_readiness.paths import SHARED  # noqa: E402

D = os.path.join(HERE, "..", "data")


def main():
    teams = {t["team_id"]: t["team_name"] for t in json.load(open(os.path.join(SHARED, "teams.json")))["teams"]}
    src = json.load(open(os.path.join(SHARED, "cards.json")))
    sprint_cards = [c for c in src["cards"] if c.get("status") != "backlog"]
    backlog = json.load(open(os.path.join(D, "mock_backlog.json")))
    cards = [dict(c, team=teams[c["team_id"]]) for c in sprint_cards]
    for t in backlog["tickets"]:
        cards.append(dict(card_id=t["key"], team_id=t["team_id"], team=teams[t["team_id"]], sprint_id=None, title=t["summary"],
                          priority=(t["priority"] or "").lower() or None, story_points=t["story_points"], status="backlog",
                          linked_pr_id=None, linked_risk_ids=[], feature_id=t["parent"], issue_type=t["type"], rank=t["rank"],
                          severity=t["severity"], blocked_by=t["blocked_by"], created=t["created"], updated=t["updated"],
                          description=t["description"], acceptance_criteria=t["acceptance_criteria"], assignee=t["assignee"],
                          start_date=t["start_date"]))
    ids = [c["card_id"] for c in cards]
    assert len(ids) == len(set(ids)), "duplicate card ids"
    json.dump({"as_of": backlog["meta"]["as_of"], "sprints": src["sprints"], "cards": cards},
              open(os.path.join(SHARED, "cards.json"), "w"), indent=1)
    print(f"cards.json: {len(cards)} cards ({len(sprint_cards)} sprint + {len(backlog['tickets'])} backlog)")


if __name__ == "__main__":
    main()
