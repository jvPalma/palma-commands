"""
Display configuration and mode resolution utilities.

This module centralizes:
- Display mode resolution from CLI options and config
- Panel color determination logic
- Display constants and configurations
"""

from prs.config import get
from prs.core.checks.helpers import analyze_checks
from prs.core.reviews.helpers import analyze_reviews
from prs.core.labels.helpers import DANG_LIST


def resolve_display_modes(options: dict) -> dict:
    """
    Resolve all display modes from CLI options or config fallbacks.
    
    Args:
        options: Dictionary of CLI options
        
    Returns:
        Dictionary containing resolved display modes for all features
    """
    return {
        "include_drafts": options.get("include_draft", False),
        "author": options.get("author", get("pr-info", "author", fallback="short")),
        "checks": options.get("checks", get("pr-info", "checks", fallback="short")),
        "reviews": options.get("reviews", get("pr-info", "reviews", fallback="short")),
        "labels": options.get("labels", get("pr-info", "labels", fallback="short")),
        "pr_url": options.get("pr_url", get("pr-info", "pr_url", fallback="normal")),
        "branch": options.get("branch", get("pr-info", "branch", fallback="normal")),
        "lines": options.get("lines", 5),
    }


def get_panel_color(pr) -> str:
    """
    Determines the Rich Panel color based on PR status.
    
    Draft PRs:
    - CI is OK -> cyan
    - other scenarios -> gray
    
    Open PRs:
    - anything is actually failing/NOT-OK -> red
    - if [Checks/Labels/Reviews] at least 1 of these is OK -> yellow
    - if [Checks/Labels/Reviews] at least 2 of these is OK -> green
    - if [Checks/Labels/Reviews] all 3 of are OK -> white
    
    Args:
        pr: Pull request model object
        
    Returns:
        Color string for Rich Panel border
    """
    # Handle Draft PRs first
    if pr.is_draft:
        _, _, _, failing_count, _ = analyze_checks(pr)
        # Cyan if CI is OK (no failures), gray otherwise
        return "cyan" if failing_count == 0 else "bright_black"
    
    # Logic for Open (non-draft) PRs
    ok_count = 0
    
    # 1. Check Status: OK if there are checks and none are failing
    total_checks, _, _, failing_count, _ = analyze_checks(pr)
    if total_checks > 0 and failing_count == 0:
        ok_count += 1
    
    # 2. Review Status: OK if approved
    review_summary, _ = analyze_reviews(pr)
    if review_summary == "APPROVED":
        ok_count += 1
    
    # 3. Label Status: OK if there are labels and no danger labels are present
    if pr.labels and not any(label in DANG_LIST for label in pr.labels):
        ok_count += 1
    
    # Map OK count to color
    color_map = {
        0: "red",
        1: "yellow", 
        2: "green",
        3: "white"
    }
    return color_map.get(ok_count, "red")  # Default to red


# Display constants
MAX_TITLE_LENGTH = 90