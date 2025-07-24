from prs.config import get
from prs.utils.formatting import color_text, color_text_bg
from prs.utils.username_colors import get_username_color


def compute_author_status(pr):
    """
    Returns the formatted username using consistent, persistent colors.
    Own user: black text on green background.
    Others: colored with their deterministically assigned unique foreground color.
    Adds a indicator prefix if user is a reviewer.
    """
    config_username = get("git", "username")
    user = pr.author
    fg, bg = get_username_color(user, config_username)
    
    # Add role indicator if relevant - use role field instead of source for more precision
    prefix = ""
    if hasattr(pr, 'role') and pr.role:
        if pr.role == "reviewer_pending":
            prefix = "[R*] "  # Reviewer with pending review
        elif pr.role == "reviewer_completed":
            prefix = "[Rd] "  # Reviewer with completed review
        elif pr.role == "both_pending":
            prefix = "[A+R*] "  # Author and reviewer with pending review
        elif pr.role == "both_completed":
            prefix = "[A+Rd] "  # Author and reviewer with completed review
    # Fallback to legacy source field for backwards compatibility
    elif hasattr(pr, 'source') and pr.source:
        if pr.source in ["reviewer", "reviewer_pending"]:
            prefix = "[R*] "  # Reviewer with pending review (legacy)
        elif pr.source == "reviewer_completed":
            prefix = "[Rd] "  # Reviewer with completed review (legacy)
        elif pr.source in ["both", "both_pending"]:
            prefix = "[A+R*] "  # Author and reviewer with pending review (legacy)
        elif pr.source == "both_completed":
            prefix = "[A+Rd] "  # Author and reviewer with completed review (legacy)
    
    display_text = prefix + user
    
    if bg:
        return color_text_bg(display_text, fg, bg)
    else:
        return color_text(display_text, fg)


def get_author(pr, mode: str) -> str:
    # mode "none" returns an empty string,
    # mode "any other value" return the username,

    if mode == "none":
        return ""
    elif mode == "short":
        return compute_author_status(pr)
    else:
        return compute_author_status(pr)
