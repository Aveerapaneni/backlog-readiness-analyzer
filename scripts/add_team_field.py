"""Stamp the shared `team` custom field onto cards in an existing project's data file.

Usage: python3 scripts/add_team_field.py path/to/cards.json [--teams path/to/teams.json] [--write]

Works on a JSON list of cards, or an object holding a list under "cards" / "tickets".
A card's team is found, in order, from: an existing team_id, the key prefix (ALPHA-, BRAVO-, CHAR-).
Adds `team_id` (team_alpha, ...) and `team` ("Team Alpha", ...) without touching any other field.
Prints a dry run unless --write is given. Cards whose team cannot be found are listed, never guessed.
"""
import argparse
import json
import sys

PREFIX = {"ALPHA": "team_alpha", "BRAVO": "team_bravo", "CHAR": "team_charlie"}
NAMES = {"team_alpha": "Team Alpha", "team_bravo": "Team Bravo", "team_charlie": "Team Charlie"}


def stamp(cards, names=NAMES):
    changed, unknown = 0, []
    for c in cards:
        key = c.get("card_id") or c.get("key") or ""
        tid = c.get("team_id") or PREFIX.get(key.split("-")[0].upper())
        if tid not in names:
            unknown.append(key or "?")
            continue
        before = (c.get("team_id"), c.get("team"))
        c["team_id"], c["team"] = tid, names[tid]
        changed += before != (tid, names[tid])
    return changed, unknown


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cards"); ap.add_argument("--teams"); ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    names = dict(NAMES)
    if a.teams:
        t = json.load(open(a.teams)); t = t.get("teams", t)
        names = {x["team_id"]: x["team_name"] for x in t} if isinstance(t, list) else {k: v["name"] for k, v in t.items()}
    doc = json.load(open(a.cards))
    cards = doc if isinstance(doc, list) else doc.get("cards") or doc.get("tickets")
    if not isinstance(cards, list):
        sys.exit("Could not find a list of cards in " + a.cards)
    changed, unknown = stamp(cards, names)
    print(f"{len(cards)} cards, {changed} updated, {len(unknown)} with no team found" + (": " + ", ".join(unknown) if unknown else ""))
    if a.write:
        json.dump(doc, open(a.cards, "w"), indent=2); print("Written.")
    else:
        print("Dry run. Add --write to save.")


if __name__ == "__main__":
    main()
