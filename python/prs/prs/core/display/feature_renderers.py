"""
Feature-specific rendering functions for PR display components.

This module contains focused functions for rendering:
- Check status badges and details
- Review status badges and details  
- Label status badges and details
- URL and branch information
"""

from rich.text import Text
from prs.core.author.helpers import get_author
from prs.core.checks.helpers import get_checks, analyze_checks
from prs.core.reviews.helpers import get_reviews, analyze_reviews
from prs.core.labels.helpers import get_labels, analyze_labels, DANG_LIST, WARN_LIST, GOOD_LIST
from prs.core.title.helpers import compute_open_status


def render_summary_status(pr, modes: dict) -> Text:
    """
    Render the main summary line with status badges.
    
    Args:
        pr: Pull request model object
        modes: Dictionary of display modes
        
    Returns:
        Rich Text object with formatted summary
    """
    summary_text = Text()

    # OPEN STATUS
    open_text, open_color = compute_open_status(pr)
    summary_text.append(f"[{open_text}]", style=open_color)
    summary_text.append(" ")

    # CHECKS BADGE
    if modes["checks"] == "short":
        render_checks_badge(pr, summary_text)

    # REVIEWS BADGE
    if modes["reviews"] == "short":
        render_reviews_badge(pr, summary_text)

    # LABELS BADGE
    if modes["labels"] == "short":
        render_labels_badge(pr, summary_text)

    # AUTHOR
    summary_text.append(get_author(pr, modes["author"]), style="white")

    return summary_text


def render_checks_badge(pr, summary_text: Text) -> None:
    """
    Render checks status badge into summary text.
    
    Args:
        pr: Pull request model object
        summary_text: Rich Text object to append to
    """
    _, _, _, failing_count, _ = analyze_checks(pr)
    total_checks, _, _, _, _ = analyze_checks(pr)
    
    if total_checks == 0:
        summary_text.append("[CHKS]", style="yellow")
    elif failing_count > 0:
        summary_text.append("[CHKS]", style="red")
    else:
        summary_text.append("[CHKS]", style="green")
    summary_text.append(" ")


def render_reviews_badge(pr, summary_text: Text) -> None:
    """
    Render review status badge into summary text.
    
    Args:
        pr: Pull request model object  
        summary_text: Rich Text object to append to
    """
    review_summary, _ = analyze_reviews(pr)
    
    if review_summary == "APPROVED":
        summary_text.append("[RVWS]", style="green")
    elif review_summary == "REVIEW_REQUIRED":
        summary_text.append("[RVWS]", style="yellow")
    else:
        summary_text.append("[RVWS]", style="red")
    summary_text.append(" ")


def render_labels_badge(pr, summary_text: Text) -> None:
    """
    Render labels status badge into summary text.
    
    Args:
        pr: Pull request model object
        summary_text: Rich Text object to append to  
    """
    if not pr.labels:
        summary_text.append("[LABL]", style="bright_black")
    else:
        label_color = "bright_black"
        for label in pr.labels:
            if label in DANG_LIST:
                label_color = "bright_red"
                break
            elif label in WARN_LIST:
                label_color = "yellow"
            elif label in GOOD_LIST and label_color == "bright_black":
                label_color = "green"
        summary_text.append("[LABL]", style=label_color)
    summary_text.append(" ")


def render_url_info(pr, mode: str) -> Text or None:
    """
    Render PR URL information if mode is not 'none'.
    
    Args:
        pr: Pull request model object
        mode: Display mode for URL
        
    Returns:
        Rich Text object with URL info or None if mode is 'none'
    """
    if mode == "none":
        return None
        
    url_text = Text()
    url_text.append("[LINK] ")
    url_text.append(pr.url, style="blue")
    return url_text


def render_branch_info(pr, mode: str) -> Text or None:
    """
    Render branch information if mode is not 'none'.
    
    Args:
        pr: Pull request model object
        mode: Display mode for branch
        
    Returns:
        Rich Text object with branch info or None if mode is 'none'
    """
    if mode == "none":
        return None
        
    branch_text = Text()
    branch_text.append("[BNCH] ")
    branch_text.append(pr.branch, style="yellow")
    return branch_text


def render_checks_detail(pr, mode: str) -> Text or None:
    """
    Render detailed check information.
    
    Args:
        pr: Pull request model object
        mode: Display mode for checks
        
    Returns:
        Rich Text object with check details or None if not normal/long mode
    """
    if mode not in ["normal", "long"]:
        return None
        
    checks_text = get_checks(pr, mode)
    check_detail = Text()
    check_detail.append("    Checks: " + checks_text)
    return check_detail


def render_reviews_detail(pr, mode: str) -> Text or None:
    """
    Render detailed review information.
    
    Args:
        pr: Pull request model object
        mode: Display mode for reviews
        
    Returns:
        Rich Text object with review details or None if not normal/long mode
    """
    if mode not in ["normal", "long"]:
        return None
        
    reviews_text = get_reviews(pr, mode)
    review_detail = Text()
    review_detail.append("    Review: " + reviews_text)
    return review_detail


def render_labels_detail(pr, mode: str) -> Text or None:
    """
    Render detailed label information.
    
    Args:
        pr: Pull request model object
        mode: Display mode for labels
        
    Returns:
        Rich Text object with label details or None if not normal/long mode
    """
    if mode not in ["normal", "long"]:
        return None
        
    labels_text = get_labels(pr, mode)
    label_detail = Text()
    label_detail.append("    Labels: " + labels_text)
    return label_detail