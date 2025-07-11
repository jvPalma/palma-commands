"""
Border coloring logic for PR display based on the status of LABELS, CHECKS, and REVIEWS.

This module analyzes PR data and determines the appropriate border color according to:
- Green border: All three (labels, checks, reviews) are OK
- Cyan border: Two are OK, one is pending  
- Yellow border: Other combinations (warnings)
- Red border: Any failures detected
"""

from enum import Enum
from typing import Tuple, Dict, Any
from prs.core.models import PullRequest
from prs.core.labels.helpers import DANG_LIST, WARN_LIST, GOOD_LIST


class ComponentStatus(Enum):
    """Status of a PR component (labels, checks, reviews)."""
    OK = "ok"
    PENDING = "pending"
    FAILED = "failed"
    NO_DATA = "no_data"


class BorderColor(Enum):
    """Available border colors for PR display."""
    GREEN = "green"
    CYAN = "cyan"
    YELLOW = "yellow"
    RED = "red"


def analyze_labels_status(pr: PullRequest) -> ComponentStatus:
    """
    Analyze the labels status of a PR.
    
    Returns:
        - OK: Only good labels or no dangerous/warning labels
        - FAILED: Contains any dangerous labels (DANG_LIST)
        - PENDING: Contains warning labels (WARN_LIST) but no dangerous ones
        - NO_DATA: No labels present
    """
    if not pr.labels:
        return ComponentStatus.NO_DATA
    
    has_dangerous = any(label in DANG_LIST for label in pr.labels)
    has_warning = any(label in WARN_LIST for label in pr.labels)
    has_good = any(label in GOOD_LIST for label in pr.labels)
    
    if has_dangerous:
        return ComponentStatus.FAILED
    elif has_warning:
        return ComponentStatus.PENDING
    elif has_good:
        return ComponentStatus.OK
    else:
        # Neutral labels that are not in any category
        return ComponentStatus.OK


def analyze_checks_status(pr: PullRequest) -> ComponentStatus:
    """
    Analyze the checks status of a PR.
    
    Returns:
        - OK: All checks are successful
        - FAILED: Any check has failed
        - PENDING: Some checks are pending/in-progress
        - NO_DATA: No checks present
    """
    if not pr.checks:
        return ComponentStatus.NO_DATA
    
    success_count = 0
    failure_count = 0
    pending_count = 0
    
    for check in pr.checks:
        state = check.get("state", "").upper()
        conclusion = check.get("conclusion", "").upper()
        
        # Handle GitHub check runs (with status and conclusion)
        if "status" in check:
            status = check.get("status", "").upper()
            if status == "COMPLETED":
                if conclusion in ["SUCCESS", "NEUTRAL", "SKIPPED"]:
                    success_count += 1
                elif conclusion in ["FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED"]:
                    failure_count += 1
                else:
                    # Unknown conclusion, treat as pending
                    pending_count += 1
            else:
                # Status is IN_PROGRESS, QUEUED, etc.
                pending_count += 1
        # Handle legacy check states
        elif state:
            if state == "SUCCESS":
                success_count += 1
            elif state in ["FAILURE", "FAILED", "ERROR"]:
                failure_count += 1
            elif state in ["PENDING", "IN_PROGRESS", "QUEUED"]:
                pending_count += 1
            else:
                # Unknown state, treat as pending
                pending_count += 1
        else:
            # No recognizable state information
            pending_count += 1
    
    if failure_count > 0:
        return ComponentStatus.FAILED
    elif pending_count > 0:
        return ComponentStatus.PENDING
    elif success_count > 0:
        return ComponentStatus.OK
    else:
        return ComponentStatus.NO_DATA


def analyze_reviews_status(pr: PullRequest) -> ComponentStatus:
    """
    Analyze the reviews status of a PR.
    
    Returns:
        - OK: At least one approval and no changes requested
        - FAILED: Any review requests changes
        - PENDING: No approvals but no change requests either
        - NO_DATA: No reviews present
    """
    if not pr.reviews:
        return ComponentStatus.NO_DATA
    
    has_approval = False
    has_changes_requested = False
    has_comments = False
    
    # Track latest review from each reviewer (GitHub reviews are typically ordered chronologically)
    # We want to keep the latest review from each author
    latest_reviews = {}
    
    for review in pr.reviews:
        author = review.get("author")
        author_login = author.get("login") if author else "Unknown"
        
        # Keep the latest review from each author (assuming reviews are in chronological order)
        latest_reviews[author_login] = review
    
    # Now analyze the latest reviews
    for review in latest_reviews.values():
        state = review.get("state", "").upper()
        
        if state == "APPROVED":
            has_approval = True
        elif state == "CHANGES_REQUESTED":
            has_changes_requested = True
        elif state == "COMMENTED":
            has_comments = True
    
    if has_changes_requested:
        return ComponentStatus.FAILED
    elif has_approval:
        return ComponentStatus.OK
    elif has_comments:
        return ComponentStatus.PENDING
    else:
        # No meaningful reviews
        return ComponentStatus.PENDING


def determine_border_color(
    labels_status: ComponentStatus,
    checks_status: ComponentStatus,
    reviews_status: ComponentStatus
) -> BorderColor:
    """
    Determine the border color based on the status of all three components.
    
    Rules:
    - Green: All three components are OK
    - Cyan: Two components are OK, one is pending
    - Yellow: Other combinations (warnings)
    - Red: Any component has failed
    
    Special handling for NO_DATA:
    - NO_DATA is treated as OK for border color determination
    - This allows PRs with missing data to still get meaningful colors
    """
    # Convert NO_DATA to OK for border color logic
    # This allows PRs without certain data types to still get meaningful colors
    effective_labels = ComponentStatus.OK if labels_status == ComponentStatus.NO_DATA else labels_status
    effective_checks = ComponentStatus.OK if checks_status == ComponentStatus.NO_DATA else checks_status  
    effective_reviews = ComponentStatus.OK if reviews_status == ComponentStatus.NO_DATA else reviews_status
    
    statuses = [effective_labels, effective_checks, effective_reviews]
    
    # Red: Any failures
    if ComponentStatus.FAILED in statuses:
        return BorderColor.RED
    
    # Count OK and pending statuses
    ok_count = statuses.count(ComponentStatus.OK)
    pending_count = statuses.count(ComponentStatus.PENDING)
    
    # Green: All OK
    if ok_count == 3:
        return BorderColor.GREEN
    
    # Cyan: Two OK, one pending
    if ok_count == 2 and pending_count == 1:
        return BorderColor.CYAN
    
    # Yellow: All other combinations (warnings)
    return BorderColor.YELLOW


def get_pr_border_color_and_style(pr: PullRequest) -> Tuple[str, Dict[str, Any]]:
    """
    Get the border color and style for a PR based on its status.
    
    Returns:
        Tuple of (color_name, style_info) where:
        - color_name: Rich-compatible color name
        - style_info: Dict with additional styling information
    """
    # Analyze each component
    labels_status = analyze_labels_status(pr)
    checks_status = analyze_checks_status(pr)
    reviews_status = analyze_reviews_status(pr)
    
    # Determine border color
    border_color = determine_border_color(labels_status, checks_status, reviews_status)
    
    # Map to Rich color names
    color_mapping = {
        BorderColor.GREEN: "green",
        BorderColor.CYAN: "cyan", 
        BorderColor.YELLOW: "yellow",
        BorderColor.RED: "red"
    }
    
    color_name = color_mapping[border_color]
    
    # Provide additional context for debugging/logging
    style_info = {
        "labels_status": labels_status.value,
        "checks_status": checks_status.value,
        "reviews_status": reviews_status.value,
        "border_reason": border_color.value,
        "has_labels": bool(pr.labels),
        "has_checks": bool(pr.checks),
        "has_reviews": bool(pr.reviews)
    }
    
    return color_name, style_info


def get_status_summary(pr: PullRequest) -> Dict[str, Any]:
    """
    Get a comprehensive status summary for a PR.
    
    This is useful for debugging and providing detailed status information.
    """
    labels_status = analyze_labels_status(pr)
    checks_status = analyze_checks_status(pr)
    reviews_status = analyze_reviews_status(pr)
    border_color = determine_border_color(labels_status, checks_status, reviews_status)
    
    return {
        "pr_id": pr.id,
        "pr_title": pr.title[:50] + "..." if len(pr.title) > 50 else pr.title,
        "is_draft": pr.is_draft,
        "labels": {
            "status": labels_status.value,
            "count": len(pr.labels) if pr.labels else 0,
            "values": pr.labels if pr.labels else []
        },
        "checks": {
            "status": checks_status.value,
            "count": len(pr.checks) if pr.checks else 0
        },
        "reviews": {
            "status": reviews_status.value,
            "count": len(pr.reviews) if pr.reviews else 0
        },
        "border_color": border_color.value,
        "overall_health": _get_overall_health(labels_status, checks_status, reviews_status)
    }


def _get_overall_health(
    labels_status: ComponentStatus,
    checks_status: ComponentStatus, 
    reviews_status: ComponentStatus
) -> str:
    """Get an overall health assessment of the PR."""
    statuses = [labels_status, checks_status, reviews_status]
    
    if ComponentStatus.FAILED in statuses:
        return "needs_attention"
    elif all(s in [ComponentStatus.OK, ComponentStatus.NO_DATA] for s in statuses):
        return "healthy"
    elif ComponentStatus.PENDING in statuses:
        return "in_progress"
    else:
        return "unknown"