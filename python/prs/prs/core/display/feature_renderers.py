"""
Feature-specific rendering functions for PR display components.

This module contains focused functions for rendering:
- Check status badges and details
- Review status badges and details  
- Label status badges and details
- URL and branch information
"""

from rich.text import Text
from rich.console import Console, Group
from prs.utils.formatting import color_text, success, error, warning, waiting, comment, reqChanges, neutral
from prs.core.author.helpers import get_author
from prs.core.checks.helpers import get_checks, analyze_checks
from prs.core.reviews.helpers import get_reviews, analyze_reviews
from prs.core.labels.helpers import get_labels, analyze_labels, DANG_LIST, WARN_LIST, GOOD_LIST

SHORT_PAD_SIZE = 12

# Character limits for LONG mode columns
FEATURE_CHARACTER_LIMITS = {
    "Checks": 60,
    "Reviews": 35,
    "Labels": 30
}


def count_long_modes(modes: dict) -> int:
    """
    Count how many features are in long mode.
    
    Args:
        modes: Dictionary of display modes
        
    Returns:
        Number of features currently in long mode
    """
    if not modes:
        return 0
    
    long_count = 0
    for feature in ["checks", "reviews", "labels"]:
        if modes.get(feature) == "long":
            long_count += 1
    return long_count

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
    total_checks, nSuccess, nrPending, nrFailling, _ = analyze_checks(pr)
    
    ciText = Text()

    if total_checks == 0:
        ciText.append("CI: ", style="yellow")
    elif nrFailling > 0:
        ciText.append("CI: ", style="red")
    else:
        ciText.append("CI: ", style="green")

    ciText.append(str(nSuccess), style="green")
    ciText.append("/", style="dim")
    ciText.append(str(nrPending), style="yellow")
    ciText.append("/", style="dim")
    ciText.append(str(nrFailling), style="red")

    # Add the CI text to summary and pad to SHORT_PAD_SIZE
    summary_text.append(ciText)
    
    # Calculate padding needed (measure plain text length without color codes)
    ci_plain_length = len(ciText.plain)
    padding_needed = max(0, SHORT_PAD_SIZE - ci_plain_length)
    summary_text.append(" " * padding_needed)


def render_reviews_badge(pr, summary_text: Text) -> None:
    """
    Render review status badge into summary text.
    
    Args:
        pr: Pull request model object  
        summary_text: Rich Text object to append to
    """
    review_summary, details = analyze_reviews(pr)
    
    # Count reviews by type
    approved_count = 0
    changes_requested_count = 0
    commented_count = 0
    
    for state, author, color in details:
        if state == "APPROVED":
            approved_count += 1
        elif state == "CHANGES_REQUESTED":
            changes_requested_count += 1
        elif state == "COMMENTED":
            commented_count += 1
    
    reviewText = Text()
    
    # Set overall color based on review state
    if review_summary == "APPROVED":
        reviewText.append("RV: ", style="green")
    elif review_summary == "REVIEW_REQUIRED":
        reviewText.append("RV: ", style="yellow")
    else:
        reviewText.append("RV: ", style="red")
    
    # Add counts in format: approved/commented/changes_requested
    reviewText.append(str(approved_count), style="green")
    reviewText.append("/", style="dim")
    reviewText.append(str(commented_count), style="yellow")
    reviewText.append("/", style="dim")
    reviewText.append(str(changes_requested_count), style="red")
    
    # Add the review text to summary and pad to SHORT_PAD_SIZE
    summary_text.append(reviewText)
    
    # Calculate padding needed (measure plain text length without color codes)
    review_plain_length = len(reviewText.plain)
    padding_needed = max(0, SHORT_PAD_SIZE - review_plain_length)
    summary_text.append(" " * padding_needed)


def render_labels_badge(pr, summary_text: Text) -> None:
    """
    Render labels status badge into summary text.
    
    Args:
        pr: Pull request model object
        summary_text: Rich Text object to append to  
    """
    # Count labels by category
    good_count = 0
    warn_count = 0
    danger_count = 0
    
    for label in pr.labels:
        if label in DANG_LIST:
            danger_count += 1
        elif label in WARN_LIST:
            warn_count += 1
        elif label in GOOD_LIST:
            good_count += 1
    
    labelText = Text()
    
    # Determine overall color based on highest priority label present
    if danger_count > 0:
        labelText.append("LB: ", style="bright_red")
    elif warn_count > 0:
        labelText.append("LB: ", style="yellow")
    elif good_count > 0:
        labelText.append("LB: ", style="green")
    else:
        labelText.append("LB: ", style="bright_black")
    
    # Add counts in format: good/warn/danger
    labelText.append(str(good_count), style="green")
    labelText.append("/", style="dim")
    labelText.append(str(warn_count), style="yellow")
    labelText.append("/", style="dim")
    labelText.append(str(danger_count), style="red")
    
    # Add the label text to summary and pad to SHORT_PAD_SIZE
    summary_text.append(labelText)
    
    # Calculate padding needed (measure plain text length without color codes)
    label_plain_length = len(labelText.plain)
    padding_needed = max(0, SHORT_PAD_SIZE - label_plain_length)
    summary_text.append(" " * padding_needed)


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
    branch_text.append(" ")
    
    # Create clickable link for branch checkout
    # This creates a hyperlink that can be clicked in supported terminals
    # Fallback: branch name shows normally in unsupported terminals
    try:
        # Use Rich's hyperlink support - works in many modern terminals
        # Including iTerm2, VS Code terminal, Windows Terminal, etc.
        branch_text.append(
            pr.branch,
            style="yellow",
            url=f"command:git checkout {pr.branch}"
        )
        # Note: For local git checkout, you could use url=f"file:///{pr.branch}" 
        # but GitHub link is more universally useful
    except Exception:
        # Fallback for terminals that don't support hyperlinks
        branch_text.append(pr.branch, style="yellow")
    
    return branch_text


def render_checks_detail(pr, mode: str, modes: dict = None) -> Text or None:
    """
    Render detailed check information with dynamic formatting for normal mode.
    
    Args:
        pr: Pull request model object
        mode: Display mode for checks
        modes: Dictionary of all display modes (for context-aware formatting)
        
    Returns:
        Rich Text object with check details or None if not normal/long mode
    """
    if mode not in ["normal", "long"]:
        return None
        
    # Get analysis data directly instead of pre-formatted string
    total, success_count, pending_count, nrFailling, details = analyze_checks(pr)
    
    check_detail = Text()    
    if mode == "normal":
        # Determine format based on context: 2-line if ≥2 features in long mode, otherwise 1-line
        use_two_line_format = False
        if modes:
            long_modes_count = count_long_modes(modes)
            use_two_line_format = long_modes_count >= 2
        
        if use_two_line_format:
            # 2-line format: Line 1: report name, Line 2: report value
            check_detail.append("Checks")
            check_detail.append("\n")
            if total == success_count:
                formatted_result = success("ALL TESTS PASSED")
            elif nrFailling > 0:
                formatted_result = error(f"#{nrFailling}")
            elif pending_count > 0:
                formatted_result = warning(f"#{pending_count}")
            else:
                formatted_result = success("ALL TESTS PASSED")
            check_detail.append(formatted_result)
        else:
            # 1-line format: reportName: reportValue
            check_detail.append("Checks: ")
            if total == success_count:
                formatted_result = success("ALL TESTS PASSED")
            elif nrFailling > 0:
                formatted_result = error(f"#{nrFailling}")
            elif pending_count > 0:
                formatted_result = warning(f"#{pending_count}")
            else:
                formatted_result = success("ALL TESTS PASSED")
            check_detail.append(formatted_result)
    else:  # long mode
        check_detail.append(Text(f"||-  Checks  --||", style="cyan3 bold"))
        if details:
            line_limit = modes.get("lines", 5) if modes else 5
            for i, (state, context, color, stateIcon) in enumerate(details[:line_limit]):
                check_detail.append("\n")
                # Use new formatting functions based on state with character limits
                # Account for icon + space (2 chars) in the limit
                char_limit = FEATURE_CHARACTER_LIMITS["Checks"] - 2  # Subtract 2 for icon + space
                if state == "SUCCESS":
                    formatted_check = success(context, char_limit)
                elif state in ["FAILURE", "FAILED"]:
                    formatted_check = error(context, char_limit)
                elif state == "PENDING":
                    formatted_check = warning(context, char_limit)
                else:
                    formatted_check = Text(f"{stateIcon} {context}", style=color)
                check_detail.append(formatted_check)
        else:
            check_detail.append("\nNo checks available")
    
    return check_detail


def render_reviews_detail(pr, mode: str, modes: dict = None) -> Text or None:
    """
    Render detailed review information with dynamic formatting for normal mode.
    
    Args:
        pr: Pull request model object
        mode: Display mode for reviews
        modes: Dictionary of all display modes (for context-aware formatting)
        
    Returns:
        Rich Text object with review details or None if not normal/long mode
    """
    if mode not in ["normal", "long"]:
        return None
        
    # Get analysis data directly instead of pre-formatted string
    summary, details = analyze_reviews(pr)
    
    review_detail = Text()
    
    if mode == "normal":
        # Determine format based on context: 2-line if ≥2 features in long mode, otherwise 1-line
        use_two_line_format = False
        if modes:
            long_modes_count = count_long_modes(modes)
            use_two_line_format = long_modes_count >= 2
        
        if use_two_line_format:
            # 2-line format: Line 1: report name, Line 2: report value
            review_detail.append("Review")
            review_detail.append("\n")
            if summary == "APPROVED":
                formatted_review = success("")  # Just the icon
            elif summary == "REVIEW_REQUIRED":
                formatted_review = waiting("")  # Just the icon
            elif summary == "COMMENTED":
                formatted_review = comment("")  # Just the icon
            elif summary == "CHANGES_REQUESTED":
                formatted_review = reqChanges("")  # Just the icon
            elif summary == "N/A":
                formatted_review = Text("N/A", style="dim")
            else:
                formatted_review = Text(summary, style="cyan")
            review_detail.append(formatted_review)
        else:
            # 1-line format: reportName: reportValue
            review_detail.append("Review: ")
            if summary == "APPROVED":
                formatted_review = success("")  # Just the icon
            elif summary == "REVIEW_REQUIRED":
                formatted_review = waiting("")  # Just the icon
            elif summary == "COMMENTED":
                formatted_review = comment("")  # Just the icon
            elif summary == "CHANGES_REQUESTED":
                formatted_review = reqChanges("")  # Just the icon
            elif summary == "N/A":
                formatted_review = Text("N/A", style="dim")
            else:
                formatted_review = Text(summary, style="cyan")
            review_detail.append(formatted_review)
    else:  # long mode
        review_detail.append(Text(f"||-  Reviews  --||", style="spring_green1 bold"))
        if details:
            line_limit = modes.get("lines", 5) if modes else 5
            for i, (state, author, color) in enumerate(details[:line_limit]):
                review_detail.append("\n")
                # Use new formatting functions for review states with character limits
                # Account for icon + space (2 chars) in the limit
                char_limit = FEATURE_CHARACTER_LIMITS["Reviews"] - 2  # Subtract 2 for icon + space
                if state == "APPROVED":
                    formatted_review = success(author, char_limit)
                elif state == "REVIEW_REQUIRED":
                    formatted_review = waiting(author, char_limit)
                elif state == "COMMENTED":
                    formatted_review = comment(author, char_limit)
                elif state == "CHANGES_REQUESTED":
                    formatted_review = reqChanges(author, char_limit)
                else:
                    formatted_review = Text(f"{state} {author}", style=color)
                
                review_detail.append(formatted_review)
        else:
            review_detail.append("\n")
            review_detail.append(waiting("No reviews available"))
    
    return review_detail


def render_labels_detail(pr, mode: str, modes: dict = None) -> Text or None:
    """
    Render detailed label information with dynamic formatting for normal mode.
    
    Args:
        pr: Pull request model object
        mode: Display mode for labels
        modes: Dictionary of all display modes (for context-aware formatting)
        
    Returns:
        Rich Text object with label details or None if not normal/long mode
    """
    if mode not in ["normal", "long"]:
        return None
        
    # Get analysis data directly instead of pre-formatted string
    details = analyze_labels(pr)
    mainColor = details[0][1]


    label_detail = Text()
    
    if not details:
        if mode == "normal":
            # Determine format based on context: 2-line if ≥2 features in long mode, otherwise 1-line
            use_two_line_format = False
            if modes:
                long_modes_count = count_long_modes(modes)
                use_two_line_format = long_modes_count >= 2
            
            if use_two_line_format:
                # 2-line format: Line 1: report name, Line 2: report value
                label_detail.append("Labels")
                label_detail.append("\nNo relevant labels to show", style="bright_black")
            else:
                # 1-line format: reportName: reportValue
                label_detail.append("Labels: ")
                label_detail.append("No relevant labels to show", style="bright_black")
        else:  # long mode
            label_detail.append(Text(f"||-  Labels  --||", style=f"{mainColor} bold"))
            label_detail.append("\nNo relevant labels to show", style="bright_black")
    else:
        if mode == "normal":
            # Determine format based on context: 2-line if ≥2 features in long mode, otherwise 1-line
            use_two_line_format = False
            if modes:
                long_modes_count = count_long_modes(modes)
                use_two_line_format = long_modes_count >= 2
                
            # Show only non-black colored labels in comma-separated list
            relevant_labels = [(label, color) for label, color in details if color != "brblack"]
            
            if use_two_line_format:
                # 2-line format: Line 1: report name, Line 2: report value
                label_detail.append("Labels")
                label_detail.append("\n")
                if relevant_labels:
                    for i, (label, color) in enumerate(relevant_labels):
                        if i > 0:
                            label_detail.append(", ")
                        # For normal mode, keep simple styling to maintain comma-separated format
                        label_detail.append(label, style=color)
                else:
                    label_detail.append("No relevant labels to show", style="bright_black")
            else:
                # 1-line format: reportName: reportValue
                label_detail.append("Labels: ")
                if relevant_labels:
                    for i, (label, color) in enumerate(relevant_labels):
                        if i > 0:
                            label_detail.append(", ")
                        # For normal mode, keep simple styling to maintain comma-separated format
                        label_detail.append(label, style=color)
                else:
                    label_detail.append("No relevant labels to show", style="bright_black")
        else:  # long mode
            label_detail.append(Text(f"||-  Labels  --||", style=f"{mainColor} bold"))
            # Show all labels, each on its own line using new formatting functions
            line_limit = modes.get("lines", 5) if modes else 5
            for i, (label, color) in enumerate(details[:line_limit]):
                label_detail.append("\n")
                # Use new formatting functions based on label category with character limits
                # Account for icon + space (2 chars) in the limit
                char_limit = FEATURE_CHARACTER_LIMITS["Labels"] - 2  # Subtract 2 for icon + space
                if label in DANG_LIST:
                    formatted_label = error(label, char_limit)
                elif label in WARN_LIST:
                    formatted_label = warning(label, char_limit)
                elif label in GOOD_LIST:
                    formatted_label = success(label, char_limit)
                else:
                    formatted_label = neutral(label, char_limit)
                label_detail.append(formatted_label)
    
    return label_detail