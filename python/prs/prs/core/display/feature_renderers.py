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
        
    # Get analysis data directly instead of pre-formatted string
    total, success_count, pending_count, failing_count, details = analyze_checks(pr)
    
    check_detail = Text()
    check_detail.append("    Checks: ")
    
    if mode == "normal":
        if total == success_count:
            check_detail.append("ALL TESTS PASSED", style="green")
        elif failing_count > 0:
            check_detail.append(f"FAILURE #{failing_count}", style="red")
        elif pending_count > 0:
            check_detail.append(f"PENDING #{pending_count}", style="yellow")
        else:
            check_detail.append("ALL TESTS PASSED", style="green")
    else:  # long mode
        if details:
            for i, (state, context, color) in enumerate(details):
                if i > 0:
                    check_detail.append("\n            ")  # Align with first item: 4 spaces + 8 chars "Checks: " = 12 spaces
                check_detail.append(f"{state.ljust(14)}", style=color)
                check_detail.append(f" {context}")
        else:
            check_detail.append("No checks available")
    
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
        
    # Get analysis data directly instead of pre-formatted string
    summary, details = analyze_reviews(pr)
    
    review_detail = Text()
    review_detail.append("    Review: ")
    
    if mode == "normal":
        if summary == "APPROVED":
            review_detail.append("APPROVED", style="green")
        elif summary == "REVIEW_REQUIRED":
            review_detail.append("REVIEW_REQUIRED", style="yellow")
        else:
            review_detail.append(summary, style="red")
    else:  # long mode
        if details:
            for i, (state, author, color) in enumerate(details):
                if i > 0:
                    review_detail.append("\n            ")  # Align with first item: 4 spaces + 8 chars "Review: " = 12 spaces
                review_detail.append(f"{state.ljust(14)}", style=color)
                review_detail.append(f" {author}")
        else:
            review_detail.append("No reviews available")
    
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
        
    # Get analysis data directly instead of pre-formatted string
    details = analyze_labels(pr)
    
    label_detail = Text()
    label_detail.append("    Labels: ")
    
    if not details:
        label_detail.append("No relevant labels to show", style="bright_black")
    else:
        if mode == "normal":
            # Show only non-black colored labels in comma-separated list
            relevant_labels = [(label, color) for label, color in details if color != "brblack"]
            if relevant_labels:
                for i, (label, color) in enumerate(relevant_labels):
                    if i > 0:
                        label_detail.append(", ")
                    label_detail.append(label, style=color)
            else:
                label_detail.append("No relevant labels to show", style="bright_black")
        else:  # long mode
            # Show all labels, each on its own line with indentation
            for i, (label, color) in enumerate(details):
                if i > 0:
                    label_detail.append("\n            ")  # Align with first item: 4 spaces + 8 chars "Labels: " = 12 spaces
                label_detail.append(label, style=color)
    
    return label_detail