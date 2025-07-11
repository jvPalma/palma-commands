"""
Helper functions for PR status analysis and debugging.
"""

from typing import List
from prs.core.models import PullRequest
from prs.core.status.border_logic import get_status_summary, get_pr_border_color_and_style


def get_status_debug_info(pr: PullRequest) -> str:
    """
    Get detailed debug information about a PR's status analysis.
    
    This is useful for understanding why a specific border color was chosen.
    """
    summary = get_status_summary(pr)
    border_color, style_info = get_pr_border_color_and_style(pr)
    
    debug_lines = [
        f"PR #{pr.id}: {pr.title[:50]}{'...' if len(pr.title) > 50 else ''}",
        f"  Draft: {pr.is_draft}",
        f"  Border Color: {border_color}",
        f"  Overall Health: {summary['overall_health']}",
        "",
        "Component Analysis:",
        f"  Labels: {style_info['labels_status']} ({summary['labels']['count']} labels)",
        f"    Values: {summary['labels']['values']}",
        f"  Checks: {style_info['checks_status']} ({summary['checks']['count']} checks)",
        f"  Reviews: {style_info['reviews_status']} ({summary['reviews']['count']} reviews)",
        "",
        f"Raw Data Present: L={style_info['has_labels']}, C={style_info['has_checks']}, R={style_info['has_reviews']}"
    ]
    
    return "\n".join(debug_lines)


def analyze_pr_batch(prs: List[PullRequest]) -> dict:
    """
    Analyze a batch of PRs and return summary statistics.
    
    Useful for understanding the distribution of PR statuses in a repository.
    """
    if not prs:
        return {"total": 0, "distribution": {}, "health_distribution": {}}
    
    border_colors = []
    health_statuses = []
    
    for pr in prs:
        border_color, _ = get_pr_border_color_and_style(pr)
        summary = get_status_summary(pr)
        
        border_colors.append(border_color)
        health_statuses.append(summary['overall_health'])
    
    # Count distributions
    border_distribution = {}
    health_distribution = {}
    
    for color in border_colors:
        border_distribution[color] = border_distribution.get(color, 0) + 1
    
    for health in health_statuses:
        health_distribution[health] = health_distribution.get(health, 0) + 1
    
    return {
        "total": len(prs),
        "border_color_distribution": border_distribution,
        "health_distribution": health_distribution,
        "summary": {
            "healthy_prs": health_distribution.get("healthy", 0),
            "needs_attention": health_distribution.get("needs_attention", 0),
            "in_progress": health_distribution.get("in_progress", 0),
            "green_borders": border_distribution.get("green", 0),
            "red_borders": border_distribution.get("red", 0)
        }
    }


def get_status_legend() -> str:
    """
    Return a legend explaining the border color meanings.
    """
    return """
Border Color Legend:
  🟢 Green:  All components (labels, checks, reviews) are OK
  🔵 Cyan:   Two components are OK, one is pending  
  🟡 Yellow: Mixed status (warnings, other combinations)
  🔴 Red:    Any component has failed

Health Indicators (Table View):
  ●●● = All OK (Green)
  ●●○ = Mostly OK (Cyan) 
  ●○○ = Some Issues (Yellow)
  ●×× = Problems (Red)

Component Status:
  - Labels: OK=good/neutral, PENDING=warnings, FAILED=dangerous
  - Checks: OK=success, PENDING=in-progress, FAILED=failed
  - Reviews: OK=approved, PENDING=requested/commented, FAILED=changes requested
  - NO_DATA: Treated as OK for border color determination
"""