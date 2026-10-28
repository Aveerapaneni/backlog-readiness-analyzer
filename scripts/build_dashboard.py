"""Build a self-contained dashboard page (dashboard/index.html) from a backlog file. No server, no network.

Usage: python3 scripts/build_dashboard.py [input.json] [--snapshot-dir snapshots] [--as-of YYYY-MM-DD] [--out dashboard/index.html]
Default input: ../pm-portfolio-mock-data/cards.json. Open the result in any browser.
"""
import argparse
import html
import json
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
from backlog_readiness.analyze import analyze  # noqa: E402
from backlog_readiness.history import trend  # noqa: E402
from backlog_readiness.loader import load  # noqa: E402
from backlog_readiness.paths import SHARED  # noqa: E402

E = html.escape
CSS = """
:root{--bg:#faf9f5;--panel:#fff;--fg:#1f1e1d;--muted:#6b6a68;--line:#e4e2dc;--ok:#2e7d4f;--warn:#b7791f;--bad:#c0392b;--accent:#3d5a80}
@media(prefers-color-scheme:dark){:root{--bg:#1c1b1a;--panel:#262523;--fg:#f0eee8;--muted:#a3a19b;--line:#3a3835;--ok:#5fb383;--warn:#e0a84a;--bad:#e8746a;--accent:#8fb0d8}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,sans-serif}
main{max-width:1120px;margin:0 auto;padding:24px 16px 48px;display:flex;flex-direction:column;gap:28px}
h1{font:400 2rem Georgia,serif;margin:0}h2{font-size:1.1rem;margin:0 0 6px}h3{margin:0;font-size:1rem}
.muted{color:var(--muted);font-size:.85rem}.grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(230px,1fr))}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}
.big{font:400 2.2rem Georgia,serif;margin:2px 0}.big small{font-size:1rem}.label{font-size:.75rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.bar{display:flex;height:14px;border-radius:7px;overflow:hidden;margin:10px 0;background:var(--line)}.bar i{display:block}
.ok{background:var(--ok)}.warn{background:var(--warn)}.bad{background:var(--bad)}
ul.legend{list-style:none;padding:0;margin:0;display:flex;flex-wrap:wrap;gap:4px 14px}.sw{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px}
dl{margin:10px 0 0}dl div{display:flex;justify-content:space-between;gap:10px;border-top:1px solid var(--line);padding:5px 0}dt{color:var(--muted)}dd{margin:0;text-align:right}
table{border-collapse:collapse;width:100%;font-size:.85rem}th{position:sticky;top:0;background:var(--panel);text-align:left;white-space:nowrap}
th,td{padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}.box{max-height:34rem;overflow:auto;border:1px solid var(--line);border-radius:10px;background:var(--panel)}
.pill{display:inline-block;padding:1px 8px;border-radius:10px;font-size:.75rem;color:#fff}.pill.old{background:var(--accent)}
td ul{margin:0;padding-left:16px}.heat{text-align:center}.heat small{display:block;color:var(--muted)}
.controls{display:flex;flex-wrap:wrap;gap:10px;margin:8px 0}input,select{font:inherit;padding:4px 8px;border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--fg)}
.lnk{background:none;border:none;color:var(--accent);font:inherit;font-weight:600;cursor:pointer;padding:0;text-decoration:underline dotted;text-decoration-color:var(--muted)}
.lnk:hover,.lnk:focus-visible{text-decoration-style:solid;text-decoration-color:var(--accent)}
tr.detail td{background:var(--bg)}
dl.detail-dl{display:grid;grid-template-columns:140px 1fr;gap:6px 12px;margin:4px 0;align-items:start}
dl.detail-dl>div{display:contents}
dl.detail-dl dt{color:var(--muted);font-size:.78rem;text-transform:uppercase;letter-spacing:.04em;padding-top:1px}
dl.detail-dl dd{margin:0;text-align:left}
.statlink{color:inherit;text-decoration:none;cursor:pointer;border-bottom:1px dotted var(--muted)}
.statlink:hover,.statlink:focus-visible{color:var(--accent);border-bottom-color:var(--accent)}
.cmp{width:100%;border-collapse:collapse}.cmp th,.cmp td{padding:7px 10px;border-bottom:1px solid var(--line);text-align:center}
.cmp th:first-child,.cmp td:first-child{text-align:left}.cmp thead th{color:var(--muted);font-weight:400;font-size:.8rem}
"""


def pill(tier):
    c = {"Ready": "ok", "Almost ready": "warn", "Not ready": "bad"}[tier]
    return f'<span class="pill {c}">{E(tier)}</span>'


def bar(n, a, b):
    t = (n + a + b) or 1
    return f'<div class="bar"><i class="ok" style="width:{100*n/t:.1f}%"></i><i class="warn" style="width:{100*a/t:.1f}%"></i><i class="bad" style="width:{100*b/t:.1f}%"></i></div>'


def heat(p):
    return "ok" if p >= 70 else "warn" if p >= 40 else "bad"


def _card_ticket(c, team_name):
    """cards.json rows already in a sprint (in_progress / done) carry only the operational fields below --
    no description / acceptance_criteria / created / updated. Those are backlog-grooming fields that this
    shared file stops tracking once a card is picked up, so every .get() here can legitimately be None."""
    return {
        "key": c["card_id"], "team_id": c["team_id"], "team": c.get("team") or team_name,
        "type": c.get("issue_type"), "summary": c["title"], "status": c.get("status"),
        "priority": c.get("priority"), "story_points": c.get("story_points"), "parent": c.get("feature_id"),
        "severity": c.get("severity"), "blocked_by": c.get("blocked_by"), "created": c.get("created"), "updated": c.get("updated"),
        "description": c.get("description"), "acceptance_criteria": c.get("acceptance_criteria"),
        "assignee": c.get("assignee"), "start_date": c.get("start_date"),
        "sprint_id": c.get("sprint_id"), "linked_pr_id": c.get("linked_pr_id"),
    }


def sprint_card_complete(t):
    """What "full data" means for a card already in a sprint: pointed, linked to an epic, and (once in
    progress) linked to a PR. Not the backlog content rules (description/AC) -- those fields aren't
    tracked any more once a card leaves the backlog."""
    missing = []
    if t.get("story_points") is None:
        missing.append("Not pointed")
    if not t.get("parent"):
        missing.append("No epic / parent link")
    if t.get("status") == "in_progress" and not t.get("linked_pr_id"):
        missing.append("No linked PR yet")
    return missing, not missing


def non_backlog_cards(raw_doc, teams_meta):
    """Cards from the shared cards.json that aren't in the backlog (in_progress / done) -- the analyzer's own
    loader only keeps their status for blocker resolution, so we read the raw file again to get full fields."""
    if "cards" not in raw_doc:
        return [], []
    sprint_meta = {s["sprint_id"]: s for s in raw_doc.get("sprints", [])}
    active, closed = [], []
    for c in raw_doc["cards"]:
        if c.get("status") not in ("in_progress", "done"):
            continue
        team_name = teams_meta.get(c["team_id"], {}).get("name", c["team_id"])
        t = _card_ticket(c, team_name)
        t["sprint_end"] = sprint_meta.get(c.get("sprint_id"), {}).get("end_date")
        gaps, full = sprint_card_complete(t)
        t["gaps"], t["full_data"] = gaps, full
        if c.get("sprint_id"):
            active.append(t)
        if c.get("status") == "done":
            closed.append(t)
    return active, closed


def nl2br(s):
    return E(s or "—").replace("\n", "<br>")


def detail_row(t, colspan):
    fields = [
        ("Summary", E(t.get("summary") or "—")),
        ("Description", nl2br(t.get("description"))),
        ("Acceptance criteria", nl2br(t.get("acceptance_criteria"))),
        ("Assignee", E(t.get("assignee") or "Unassigned")),
        ("Priority", E(str(t.get("priority") or "—"))),
        ("Severity", E(str(t.get("severity") or "—"))),
        ("Parent / epic", E(t.get("parent") or "—")),
        ("Status", E(str(t.get("status") or "—"))),
        ("Sprint", E(t.get("sprint_id") or "—")),
        ("Linked PR", E(t.get("linked_pr_id") or "—")),
        ("Created", E(t.get("created") or "—")),
        ("Updated", E(t.get("updated") or "—")),
        ("Start date", E(t.get("start_date") or "—")),
        ("Blocked by", E(t.get("blocked_by") or "—")),
    ]
    dl = "".join(f'<div><dt>{k}</dt><dd>{v}</dd></div>' for k, v in fields)
    return f'<tr class="detail" data-for="{E(t["key"])}" hidden><td colspan="{colspan}"><dl class="detail-dl">{dl}</dl></td></tr>'


def key_link(key):
    return f'<button class="lnk" data-key="{E(key)}">{E(key)}</button>'


def full_pill(ok):
    return '<span class="pill ok">Full data</span>' if ok else '<span class="pill bad">Gaps</span>'


def old_badge(stale):
    return ' <span class="pill old">6+ months</span>' if stale else ""


def build(result, history, active_sprint, closed):
    p, teams = result["program"], result["teams"]
    as_of_date = date.fromisoformat(result["as_of"])
    tiles = "".join(f'<div class="card"><div class="label">{l}</div><div class="big">{v}</div><div class="muted">{d}</div></div>' for l, v, d in [
        ("Ready", f'{p["ready_pct"]}<small>%</small>', f'{p["Ready"]} tickets meet every rule for their type'),
        ("Almost ready", p["Almost ready"], "tickets with exactly one gap to close"),
        ("Not ready", p["Not ready"], "two or more gaps, a thin description, or an open blocker"),
        ("6+ months old", p["stale_6m"], f'tickets, {p["stale_6m_not_ready"]} not fully ready'),
        ("Blocked", p["blocked"], "tickets blocked by another ticket"),
        ("Split warning", p["split_candidates"], f'cards at {result["split_at"]}+ points: consider splitting')])

    as_by_team, closed_by_team = {}, {}
    for t in active_sprint:
        s = as_by_team.setdefault(t["team_id"], {"full": 0, "total": 0})
        s["total"] += 1
        s["full"] += int(t["full_data"])
    for t in closed:
        closed_by_team[t["team_id"]] = closed_by_team.get(t["team_id"], 0) + 1

    cmp_cols = "".join(f"<th>{E(t['name'])}</th>" for t in teams.values())

    def cmp_cell(tid, t):
        asf = as_by_team.get(tid, {"full": 0, "total": 0})
        if asf["total"] == 0:
            as_cell = '<span class="muted">no active-sprint cards</span>'
        else:
            as_cell = f'<a class="statlink" href="#active-sprint-sec"><b>{asf["full"]}</b> of {asf["total"]}</a>'
        ready_cell = f'<a class="statlink" href="#tix-sec" data-team="{E(t["name"])}" data-tier="Ready"><b>{t["Ready"]}</b></a> of {t["total"]} ({t["ready_pct"]}%)'
        untouched_cell = f'<a class="statlink" href="#tix-sec" data-team="{E(t["name"])}" data-untouched="1"><b>{t["untouched"]}</b></a>'
        closed_cell = f'<a class="statlink" href="#closed-sec"><b>{closed_by_team.get(tid, 0)}</b></a>'
        return as_cell, ready_cell, untouched_cell, closed_cell

    cmp_rows_data = {tid: cmp_cell(tid, t) for tid, t in teams.items()}
    cmp_table = f'''<table class="cmp"><thead><tr><th>Metric</th>{cmp_cols}</tr></thead><tbody>
<tr><td>Active sprint &mdash; full data</td>{"".join(f"<td>{v[0]}</td>" for v in cmp_rows_data.values())}</tr>
<tr><td>Ready to implement</td>{"".join(f"<td>{v[1]}</td>" for v in cmp_rows_data.values())}</tr>
<tr><td>90+ days untouched</td>{"".join(f"<td>{v[2]}</td>" for v in cmp_rows_data.values())}</tr>
<tr><td>Closed (done)</td>{"".join(f"<td>{v[3]}</td>" for v in cmp_rows_data.values())}</tr>
</tbody></table>'''

    team_cards = ""
    for t in teams.values():
        gaps = "".join(f'<div style="display:flex;justify-content:space-between"><span>{E(g)}</span><b>{n}</b></div>' for g, n in t["top_gaps"][:4])
        n = t["next_sprint_candidates"]
        team_cards += f'''<article class="card"><h3>{E(t["name"])}</h3><div class="muted">Velocity {t["velocity"]} pts per sprint</div>{bar(t["Ready"], t["Almost ready"], t["Not ready"])}
<ul class="legend"><li><i class="sw ok"></i>Ready <b>{t["Ready"]}</b> ({t["ready_pct"]}%)</li><li><i class="sw warn"></i>Almost <b>{t["Almost ready"]}</b></li><li><i class="sw bad"></i>Not ready <b>{t["Not ready"]}</b></li></ul>
<dl><div><dt>Top of backlog ready</dt><dd><b>{t["top_slice"]["ready_pct"]}%</b> ({t["top_slice"]["Ready"]} of {t["top_slice"]["total"]})</dd></div>
<div><dt>Runway</dt><dd><b>{t["runway"]["sprints"]}</b> sprints ({t["runway"]["ready_points"]} pts)</dd></div>
<div><dt>Next-sprint candidates</dt><dd><b>{n["count"]}</b> ({n["points"]} pts)</dd></div>
<div><dt>Blocked by another ticket</dt><dd><b>{t["blocked"]}</b></dd></div>
<div><dt>6+ months old</dt><dd><b>{t["stale_6m"]}</b> ({t["stale_6m_not_ready"]} not fully ready)</dd></div>
<div><dt>Split warning (8+ pts)</dt><dd><b>{t["oversized"]}</b></dd></div></dl>
<div class="label" style="margin-top:10px">Most common gaps</div>{gaps}</article>'''
    types = ["Story", "Bug", "Tech Debt", "Research", "Spike", "Task"]
    rows = ""
    for t in teams.values():
        cells = "".join(
            f'<td class="heat {heat(t["by_type"][ty]["ready_pct"])}" style="color:#fff"><b>{t["by_type"][ty]["ready_pct"]}%</b><small style="color:#fff">{t["by_type"][ty]["Ready"]} of {t["by_type"][ty]["total"]}</small></td>'
            if ty in t["by_type"] else '<td class="heat muted">-</td>' for ty in types)
        rows += f'<tr><th>{E(t["name"])}</th>{cells}</tr>'
    matrix = f'<div class="box"><table><tr><th></th>{"".join(f"<th>{x}</th>" for x in types)}</tr>{rows}</table></div>'
    order = {"Not ready": 0, "Almost ready": 1, "Ready": 2}
    tk = sorted(result["tickets"], key=lambda t: (order[t["tier"]], t["team"], t["rank"]))
    li = lambda xs: "<ul>" + "".join(f"<li>{E(x)}</li>" for x in xs) + "</ul>" if xs else "—"
    trs = "".join(
        f'<tr data-team="{E(t["team"])}" data-tier="{t["tier"]}" data-old="{int(t["stale_6m"])}" data-untouched="{int(t["untouched"])}">'
        f'<td>{key_link(t["key"])}</td><td>{E(t["team"])}</td><td>{t["type"]}</td><td>{E(t["summary"])}</td><td>{pill(t["tier"])}</td>'
        f'<td>{li(t["gaps"])}</td><td>{li(t["advisories"])}</td><td>{t["age_tier"]}{old_badge(t["stale_6m"])}</td></tr>'
        + detail_row(t, 8)
        for t in tk)
    opts = "".join(f"<option>{E(t['name'])}</option>" for t in teams.values())
    blk = "".join(f'<tr><td>{t["key"]}</td><td>{E(t["team"])}</td><td>{E(t["summary"])}</td><td>{pill(t["tier"])}</td><td>{t["blocker"]["key"]}</td><td>{E(t["blocker"]["team"] or "")}</td><td>{t["blocker"]["status"]}</td><td>{"Blocked: Not ready until unblocked" if t["blocker"]["open"] else "Cleared: blocker is done"}</td></tr>'
                  for t in sorted((t for t in result["tickets"] if t.get("blocker")), key=lambda t: (not t["blocker"]["open"], t["team"], t["key"])))
    names = {k: v["name"] for k, v in teams.items()}
    tr_rows = "".join(f'<tr><td>{h["as_of"]}</td><td><b>{h["program_ready_pct"]}%</b></td>' + "".join(f'<td>{h["teams"].get(k, "")}%</td>' for k in names) + "</tr>" for h in history)
    tr_head = "".join(f"<th>{E(n)}</th>" for n in names.values())

    as_rows = "".join(
        f'<tr><td>{key_link(t["key"])}</td><td>{E(t["team"])}</td><td>{E(t.get("type") or "—")}</td><td>{E(t["summary"])}</td>'
        f'<td>{E((t["status"] or "").replace("_", " ").title())}</td><td>{full_pill(t["full_data"])}</td><td>{li(t["gaps"])}</td></tr>'
        + detail_row(t, 7)
        for t in sorted(active_sprint, key=lambda t: (t["team"], t["key"])))
    as_section = (
        '<section id="active-sprint-sec"><h2>Active sprint readiness</h2>'
        '<p class="muted">Cards already assigned to a team&rsquo;s active sprint. &ldquo;Full data&rdquo; here means '
        'pointed, linked to an epic, and (once in progress) linked to a PR &mdash; the backlog content rules '
        '(description, acceptance criteria) stop being tracked once a card leaves the backlog. Click a ticket for its full card.</p>'
        '<div class="box"><table><thead><tr><th>Ticket</th><th>Team</th><th>Type</th><th>Summary</th><th>Status</th><th>Data</th><th>Gaps</th></tr></thead>'
        f'<tbody>{as_rows or "<tr><td colspan=7 class=muted>No sprint-assigned cards in this input.</td></tr>"}</tbody></table></div></section>'
    )

    closed_rows = "".join(
        f'<tr><td>{key_link(t["key"])}</td><td>{E(t["team"])}</td><td>{E(t.get("type") or "—")}</td><td>{E(t["summary"])}</td>'
        f'<td>{E(t.get("sprint_id") or "—")}</td><td>{E(t.get("sprint_end") or "—")}</td>'
        f'<td>{(as_of_date - date.fromisoformat(t["sprint_end"])).days if t.get("sprint_end") else "—"}</td></tr>'
        + detail_row(t, 7)
        for t in sorted(closed, key=lambda t: t.get("sprint_end") or ""))
    closed_section = (
        '<section id="closed-sec"><h2>Closed tickets</h2>'
        '<p class="muted">Cards with status done. Not scored for readiness (that only applies to the backlog) &mdash; shown here for visibility. Click a ticket for its full card.</p>'
        '<div class="box"><table><thead><tr><th>Ticket</th><th>Team</th><th>Type</th><th>Summary</th><th>Sprint</th><th>Sprint ended</th><th>Days since</th></tr></thead>'
        f'<tbody>{closed_rows or "<tr><td colspan=7 class=muted>No closed cards in this input.</td></tr>"}</tbody></table></div></section>'
    )

    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Backlog Readiness</title><style>{CSS}</style></head><body><main>
<header><h1>Backlog readiness</h1><p class="muted">As of {result["as_of"]}. {p["total"]} tickets across {len(teams)} teams. Generated by scripts/build_dashboard.py from the analyzer; rerun it to refresh.</p></header>
<section><h2>Program health</h2><div class="grid">{tiles}</div></section>
<section><h2>Team comparison</h2><p class="muted">Click any number to jump to the tickets or cards behind it.</p><div class="box">{cmp_table}</div></section>
<section><h2>Health by team</h2><div class="grid">{team_cards}</div></section>
<section><h2>Where the weakness sits</h2><p class="muted">Ready % by team and ticket type. Red under 40%, amber 40-69%, green 70% and above.</p>{matrix}</section>
<section id="tix-sec"><h2>Tickets to fix</h2><p class="muted">Not ready tickets come first. Showing <span id="n">{len(tk)}</span> of {len(tk)}. Click a ticket for its full card.</p>
<div class="controls"><select id="t"><option value="">All teams</option>{opts}</select><select id="r"><option value="">All readiness</option><option>Not ready</option><option>Almost ready</option><option>Ready</option></select>
<label><input type="checkbox" id="o"> 6+ months old only</label><label><input type="checkbox" id="u"> 90+ days untouched only</label><input type="search" id="q" placeholder="Search ticket, summary or gap"></div>
<div class="box"><table id="tix"><thead><tr><th>Ticket</th><th>Team</th><th>Type</th><th>Summary</th><th>Readiness</th><th>What is missing</th><th>Flags to review</th><th>Age</th></tr></thead><tbody>{trs}</tbody></table></div></section>
{as_section}
{closed_section}
<section><h2>Dependencies</h2><p class="muted">A ticket blocked by another ticket stays Not ready until the blocker is done.</p><div class="box"><table><tr><th>Ticket</th><th>Team</th><th>Summary</th><th>Readiness</th><th>Blocked by</th><th>Blocker team</th><th>Blocker status</th><th>Effect</th></tr>{blk}</table></div></section>
<section><h2>Trend over time</h2><div class="box"><table><tr><th>Run</th><th>Program</th>{tr_head}</tr>{tr_rows or '<tr><td colspan="9" class="muted">Run the analyzer with --snapshot-dir to build a history.</td></tr>'}</table></div></section>
<section class="card"><h2>How tickets are scored</h2><p class="muted">Ready: no gaps. Almost ready: one gap. Not ready: two or more gaps, a thin description, or a blocker that is not yet done. Flags (no points, 8+ point split warning, no epic, no severity, possible duplicate, untouched 90 days) never change readiness. Runway counts Ready tickets only.</p></section>
</main><script>
const rows=[...document.querySelectorAll('#tix tbody tr:not(.detail)')],$=i=>document.getElementById(i);
function hideDetail(key){{const d=document.querySelector(`tr.detail[data-for="${{key}}"]`);if(d)d.hidden=true}}
function f(){{const t=$('t').value,r=$('r').value,o=$('o').checked,u=$('u').checked,q=$('q').value.toLowerCase();let n=0;
rows.forEach(x=>{{const show=(!t||x.dataset.team===t)&&(!r||x.dataset.tier===r)&&(!o||x.dataset.old==='1')&&(!u||x.dataset.untouched==='1')&&(!q||x.textContent.toLowerCase().includes(q));x.hidden=!show;if(!show)hideDetail(x.querySelector('.lnk')?.dataset.key);n+=show}});$('n').textContent=n}}
['t','r','o','u','q'].forEach(i=>$(i).addEventListener('input',f));
document.querySelectorAll('.lnk').forEach(b=>b.addEventListener('click',()=>{{const d=document.querySelector(`tr.detail[data-for="${{b.dataset.key}}"]`);if(d)d.hidden=!d.hidden}}));
document.querySelectorAll('.statlink').forEach(a=>a.addEventListener('click',e=>{{if(!a.dataset.team)return;e.preventDefault();$('t').value=a.dataset.team;$('r').value=a.dataset.tier||'';$('u').checked=a.dataset.untouched==='1';f();document.getElementById(a.getAttribute('href').slice(1)).scrollIntoView({{behavior:'smooth',block:'start'}})}}));
</script></body></html>'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", nargs="?", default=os.path.join(SHARED, "cards.json"))
    ap.add_argument("--snapshot-dir", default=os.path.join(ROOT, "snapshots"))
    ap.add_argument("--as-of")
    ap.add_argument("--out", default=os.path.join(ROOT, "dashboard", "index.html"))
    a = ap.parse_args()
    with open(a.input) as fh:
        raw_doc = json.load(fh)
    result = analyze(load(a.input), as_of=a.as_of)
    active_sprint, closed = non_backlog_cards(raw_doc, result["teams"])
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w") as fh:
        fh.write(build(result, trend(a.snapshot_dir), active_sprint, closed))
    print(f"Wrote {a.out}")


if __name__ == "__main__":
    main()
