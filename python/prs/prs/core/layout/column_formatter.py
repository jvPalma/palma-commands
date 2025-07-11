"""
Column formatting utilities for the PRS columnar layout system.
"""
import re
from typing import List, Dict, Tuple, Optional
from rich.text import Text
from rich.console import Console

from prs.core.models import PullRequest
from prs.core.checks.helpers import get_checks
from prs.core.reviews.helpers import get_reviews
from prs.core.labels.helpers import get_labels
from prs.core.comments.helpers import get_comments
from prs.core.author.helpers import get_author
from prs.core.title.helpers import compute_open_status, format_title
from prs.utils.formatting import color_text, clickable_link


def strip_ansi_codes(text: str) -> str:
    """Remove ANSI color codes from text to get its display width."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def get_display_width(text: str) -> int:
    """Get the actual display width of text, accounting for ANSI codes."""
    return len(strip_ansi_codes(text))


def truncate_text(text: str, max_width: int, suffix: str = "...") -> str:
    """Truncate text to fit within max_width, preserving ANSI codes where possible."""
    if get_display_width(text) <= max_width:
        return text
    
    # For ANSI-coded text, we need to be more careful
    clean_text = strip_ansi_codes(text)
    if len(clean_text) <= max_width - len(suffix):
        return text  # Original text fits
    
    # Find color codes in original text
    ansi_pattern = re.compile(r'(\x1B\[[0-?]*[ -/]*[@-~])')
    parts = ansi_pattern.split(text)
    
    result = ""
    current_width = 0
    available_width = max_width - len(suffix)
    
    for part in parts:
        if ansi_pattern.match(part):
            # This is an ANSI code, add it without counting width
            result += part
        else:
            # This is regular text
            remaining_space = available_width - current_width
            if len(part) <= remaining_space:
                result += part
                current_width += len(part)
            else:
                # Truncate this part
                result += part[:remaining_space] + suffix
                break
    
    return result


def pad_text(text: str, width: int, align: str = "left") -> str:
    """Pad text to a specific width, accounting for ANSI codes."""
    display_width = get_display_width(text)
    padding_needed = max(0, width - display_width)
    
    if align == "left":
        return text + " " * padding_needed
    elif align == "right":
        return " " * padding_needed + text
    elif align == "center":
        left_pad = padding_needed // 2
        right_pad = padding_needed - left_pad
        return " " * left_pad + text + " " * right_pad
    else:
        return text


def format_pr_line1(pr: PullRequest) -> str:
    """Format Line 1: PR number (A) and PR title (B) - always visible."""
    pr_number = f"#{pr.id:06d}"
    pr_number_colored = color_text(pr_number, "gray-3")
    
    # Format title with appropriate color
    title_color = "gray-4" if pr.is_draft else "white"
    title_text = format_title(pr.title)
    title_colored = color_text(title_text, title_color)
    
    return f"{pr_number_colored} {title_colored}"


def format_pr_line2_short(pr: PullRequest) -> List[Tuple[str, int]]:
    """
    Format Line 2: All short mode data in fixed-size columns with emojis/colors.
    Returns list of (formatted_text, column_width) tuples.
    """
    columns = []
    
    # Status column (8 chars)
    open_text, open_color = compute_open_status(pr)
    status_icon = "🟢" if open_text == "OPEN" else "🟡" if open_text == "DRFT" else "⚫"
    status_text = f"{status_icon} {color_text(open_text, open_color)}"
    columns.append((status_text, 8))
    
    # Checks column (6 chars)
    checks_text = get_checks(pr, "short")
    if checks_text:
        check_icon = "✅" if "green" in checks_text else "❌" if "red" in checks_text else "⏳"
        checks_formatted = f"{check_icon} {checks_text}"
    else:
        checks_formatted = "⚫ " + color_text("[CHKS]", "gray-3")
    columns.append((checks_formatted, 6))
    
    # Reviews column (6 chars)
    reviews_text = get_reviews(pr, "short")
    if reviews_text:
        review_icon = "✅" if "green" in reviews_text else "❌" if "red" in reviews_text else "⏳"
        reviews_formatted = f"{review_icon} {reviews_text}"
    else:
        reviews_formatted = "⚫ " + color_text("[RVWS]", "gray-3")
    columns.append((reviews_formatted, 6))
    
    # Comments column (6 chars)
    comments_text = get_comments(pr, "short")
    comment_icon = "💬" if comments_text and "gray" not in comments_text else "⚫"
    comments_formatted = f"{comment_icon} {comments_text}" if comments_text else f"{comment_icon} " + color_text("[CMTS]", "gray-3")
    columns.append((comments_formatted, 6))
    
    # Labels column (6 chars)
    labels_text = get_labels(pr, "short")
    label_icon = "🏷️" if labels_text and "brblack" not in labels_text else "⚫"
    labels_formatted = f"{label_icon} {labels_text}" if labels_text else f"{label_icon} " + color_text("[LABL]", "gray-3")
    columns.append((labels_formatted, 6))
    
    # Author column (12 chars)
    author_text = get_author(pr, "short")
    author_icon = "👤"
    author_formatted = f"{author_icon} {author_text}"
    columns.append((author_formatted, 12))
    
    # Changes column (10 chars)
    if pr.additions or pr.deletions:
        changes_icon = "📊"
        additions_text = color_text(f"+{pr.additions}", "green")
        deletions_text = color_text(f"-{pr.deletions}", "red")
        changes_formatted = f"{changes_icon} {additions_text}/{deletions_text}"
    else:
        changes_formatted = "⚫ " + color_text("No changes", "gray-3")
    columns.append((changes_formatted, 10))
    
    return columns


def format_normal_mode_data(pr: PullRequest) -> List[str]:
    """Format normal mode data for the first column of lines 3-9."""
    data_lines = []
    
    # Checks (normal mode)
    checks_normal = get_checks(pr, "normal")
    if checks_normal:
        data_lines.append(f"Checks: {checks_normal}")
    
    # Reviews (normal mode)
    reviews_normal = get_reviews(pr, "normal")
    if reviews_normal:
        data_lines.append(f"Reviews: {reviews_normal}")
    
    # Labels (normal mode)
    labels_normal = get_labels(pr, "normal")
    if labels_normal:
        data_lines.append(f"Labels: {labels_normal}")
    
    # Comments (normal mode)
    comments_normal = get_comments(pr, "normal")
    if comments_normal:
        data_lines.append(f"Comments: {comments_normal}")
    
    # Author (always show in normal mode)
    author_normal = get_author(pr, "normal")
    if author_normal:
        data_lines.append(f"Author: {author_normal}")
    
    # Branch info
    if pr.branch:
        branch_colored = color_text(pr.branch, "yellow")
        data_lines.append(f"Branch: {branch_colored}")
    
    # URL (clickable link)
    if pr.url:
        url_link = clickable_link(pr.url, f"PR #{pr.id}", "blue")
        data_lines.append(f"URL: {url_link}")
    
    return data_lines


def format_long_mode_data(pr: PullRequest) -> Dict[str, List[str]]:
    """
    Format long mode data for additional columns.
    Returns a dict where keys are column names and values are lists of lines.
    """
    columns_data = {}
    
    # Checks details (long mode)
    checks_long = get_checks(pr, "long")
    if checks_long and checks_long != "No checks available":
        check_lines = checks_long.split("\n\t\t")
        # Limit to 7 lines max
        if len(check_lines) > 7:
            check_lines = check_lines[:6] + ["..."]
        columns_data["Checks Detail"] = check_lines
    
    # Reviews details (long mode)
    reviews_long = get_reviews(pr, "long")
    if reviews_long and reviews_long != "No reviews available":
        review_lines = reviews_long.split("\n\t\t")
        # Limit to 7 lines max
        if len(review_lines) > 7:
            review_lines = review_lines[:6] + ["..."]
        columns_data["Reviews Detail"] = review_lines
    
    # Labels details (long mode)
    labels_long = get_labels(pr, "long")
    if labels_long and labels_long != "No relevant labels to show":
        label_lines = labels_long.split("\n\t\t")
        # Limit to 7 lines max
        if len(label_lines) > 7:
            label_lines = label_lines[:6] + ["..."]
        columns_data["Labels Detail"] = label_lines
    
    # Comments details (long mode)
    comments_long = get_comments(pr, "long")
    if comments_long and comments_long != "No comments available":
        comment_lines = comments_long.split("\n\t\t")
        # Limit to 7 lines max
        if len(comment_lines) > 7:
            comment_lines = comment_lines[:6] + ["..."]
        columns_data["Comments Detail"] = comment_lines
    
    # File changes (if available)
    if pr.changed_files:
        changes_lines = [
            color_text(f"Files changed: {pr.changed_files}", "blue"),
            color_text(f"Additions: +{pr.additions}", "green"),
            color_text(f"Deletions: -{pr.deletions}", "red")
        ]
        if pr.additions and pr.deletions:
            total_changes = pr.additions + pr.deletions
            changes_lines.append(color_text(f"Total changes: {total_changes}", "cyan"))
        columns_data["File Changes"] = changes_lines
    
    return columns_data


def format_column_with_width(lines: List[str], width: int, title: str = None) -> List[str]:
    """
    Format a column's content to fit within the specified width.
    Optionally add a title header.
    """
    formatted_lines = []
    
    # Add title if provided
    if title:
        title_line = color_text(title, "cyan")
        title_line = truncate_text(title_line, width)
        title_line = pad_text(title_line, width)
        formatted_lines.append(title_line)
        formatted_lines.append("-" * width)  # Separator line
    
    # Format each content line
    for line in lines:
        if line:
            formatted_line = truncate_text(line, width)
            formatted_line = pad_text(formatted_line, width)
            formatted_lines.append(formatted_line)
        else:
            formatted_lines.append(" " * width)
    
    return formatted_lines


def align_columns_by_rows(columns: Dict[str, List[str]], max_lines: int = 7) -> List[List[str]]:
    """
    Align multiple columns by rows, ensuring each row has content from all columns.
    Pad shorter columns with empty strings.
    """
    if not columns:
        return []
    
    # Get the maximum number of lines among all columns
    max_column_lines = max(len(lines) for lines in columns.values())
    actual_max_lines = min(max_column_lines, max_lines)
    
    # Create aligned rows
    aligned_rows = []
    column_names = list(columns.keys())
    
    for row_idx in range(actual_max_lines):
        row = []
        for col_name in column_names:
            col_lines = columns[col_name]
            if row_idx < len(col_lines):
                row.append(col_lines[row_idx])
            else:
                # Pad with empty string if this column is shorter
                row.append("")
        aligned_rows.append(row)
    
    return aligned_rows