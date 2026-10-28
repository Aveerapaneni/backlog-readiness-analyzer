"""Plain-text report for the terminal."""
from .config import TIERS


def _signed(x, unit=""):
    return "n/a" if x is None else f"{x:+.1f}{unit}"


def render(result, change=None, list_tickets=False):
    p = result["program"]
    out = [f"Backlog readiness as of {result['as_of']}", "=" * 60,
           f"Program: {p['Ready']} Ready ({p['ready_pct']}%), {p['Almost ready']} Almost ready, {p['Not ready']} Not ready "
           f"of {p['total']}. {p['stale_6m']} are 6+ months old ({p['stale_6m_not_ready']} not fully ready)."]
    if change:
        out.append(f"  Since {change['from']}: ready share {_signed(change['program_ready_pct_change'], ' pts')}")
    out.append("")
    for tid, t in result["teams"].items():
        out.append(f"{t['name']} (velocity {t['velocity']})")
        out.append(f"  Ready {t['Ready']} / Almost {t['Almost ready']} / Not ready {t['Not ready']}  "
                   f"=> {t['ready_pct']}% ready")
        out.append(f"  Top of backlog: {t['top_slice']['ready_pct']}% ready ({t['top_slice']['Ready']} of {t['top_slice']['total']})")
        out.append(f"  Runway: {t['runway']['sprints']} sprints of ready, pointed work ({t['runway']['ready_points']} pts)")
        n = t["next_sprint_candidates"]
        out.append(f"  Next-sprint candidates (Almost ready, unblocked): {n['count']} tickets, {n['points']} pts   Blocked by another ticket: {t['blocked']}")
        out.append(f"  6+ months old: {t['stale_6m']} ({t['stale_6m_not_ready']} not fully ready)")
        if t["oversized"]:
            out.append(f"  WARNING: {t['oversized']} cards at {result['split_at']}+ pts - consider splitting")
        if t["top_gaps"]:
            out.append("  Most common gaps: " + "; ".join(f"{g} x{n}" for g, n in t["top_gaps"][:3]))
        if change:
            c = change["teams"][tid]
            out.append(f"  Change: ready {_signed(c['ready_pct_change'], ' pts')}, runway {_signed(c['runway_change'], ' sprints')}, "
                       f"top of backlog {_signed(c['top_ready_pct_change'], ' pts')}")
        out.append("")
    if p["duplicates"]:
        out.append("Possible duplicates: " + "; ".join(" / ".join(d) for d in p["duplicates"]))
        out.append("")
    if change:
        out.append(f"What changed since {change['from']}")
        out.append(f"  Moved up a tier: {len(change['moved_up'])}   (newly Ready: {len(change['newly_ready'])})")
        out.append(f"  Moved down:      {len(change['moved_down'])}")
        out.append(f"  Gaps closed:     {change['gaps_closed']}")
        out.append(f"  New tickets:     {len(change['added'])}   Removed: {len(change['removed'])}   Newly 6+ months old: {len(change['newly_stale'])}")
        for key, a, b in change["moved_up"]:
            out.append(f"    + {key}: {a} -> {b}")
        for key, a, b in change["moved_down"]:
            out.append(f"    - {key}: {a} -> {b}")
        out.append("")
    if list_tickets:
        out.append("Tickets to fix (Not ready first)")
        order = {"Not ready": 0, "Almost ready": 1}
        for t in sorted((t for t in result["tickets"] if t["tier"] != "Ready"),
                        key=lambda t: (order[t["tier"]], t["team_id"], t["rank"])):
            old = " [6+ months]" if t["stale_6m"] else ""
            if (t.get("story_points") or 0) >= result["split_at"]:
                old += f" [SPLIT? {t['story_points']} pts]"
            out.append(f"  {t['key']:<10} {t['tier']:<13} {t['type']:<9}{old}  {'; '.join(t['gaps'])}")
    return "\n".join(out)
