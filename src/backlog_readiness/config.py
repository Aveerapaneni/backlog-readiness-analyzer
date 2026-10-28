"""All tunable thresholds in one place, each with its documented default."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    # A single-line description with fewer words than this is a "one-liner" (thin).
    thin_words: int = 10
    # A pointed ticket at or above this is flagged as a split candidate.
    # Sizing is decided after engineering refinement, so this is advisory only.
    oversize_points: int = 8
    # Days since created before a ticket counts as "6+ months old".
    stale_days: int = 182
    # Days with no update before a ticket is flagged as untouched.
    untouched_days: int = 90
    # Token-overlap (Jaccard) at or above this marks two summaries as possible duplicates.
    dup_similarity: float = 0.7
    # "Top of backlog" = the next N sprints of work, by rank.
    top_sprints: int = 2
    # Points assumed for an unpointed ticket ONLY when slicing the top of the backlog.
    unpointed_for_slicing: int = 3


TIERS = ("Ready", "Almost ready", "Not ready")
TYPES = ("Story", "Bug", "Tech Debt", "Research", "Spike", "Task")
POINTED_TYPES = ("Story", "Bug", "Tech Debt")
