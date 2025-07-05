from prs.core.models import PullRequest
from prs.utils.formatting import color_text


def analyze_comments(pr: PullRequest):
    """
    Analyzes the comments on the given PR.

    Returns a tuple:
      (summary, details)
    where summary is a string with comment count,
    and details is a list of tuples (author, body_preview, created_at)
    for each comment.
    """
    total_comments = len(pr.comments)
    details = []
    
    for comment in pr.comments:
        author = comment.get("author", {})
        author_login = author.get("login") if author else "Unknown"
        body = comment.get("body", "")
        created_at = comment.get("createdAt", "")
        
        # Create a preview of the comment (first 100 characters)
        body_preview = body[:100] + "..." if len(body) > 100 else body
        # Replace newlines with spaces for better formatting
        body_preview = body_preview.replace('\n', ' ').replace('\r', ' ')
        
        details.append((author_login, body_preview, created_at))
    
    if total_comments == 0:
        summary = "No comments"
    elif total_comments == 1:
        summary = "1 comment"
    else:
        summary = f"{total_comments} comments"
    
    return summary, details


def get_comments(pr: PullRequest, mode: str) -> str:
    """
    Formats the comments information based on the provided mode.

    Modes:
      - "none": returns an empty string.
      - "short": returns a colored summary string with comment count.
      - "normal": returns a colored summary string (same as short).
      - "long": returns a detailed multi-line string with each comment preview.

    Raises:
      ValueError: if an unknown mode is provided.
    """
    summary, details = analyze_comments(pr)

    if mode == "none":
        return ""

    elif mode == "short":
        if len(pr.comments) == 0:
            return color_text("[CMTS]", "gray-3")
        elif len(pr.comments) <= 3:
            return color_text("[CMTS]", "blue")
        else:
            return color_text("[CMTS]", "yellow")
    
    elif mode == "normal":
        if len(pr.comments) == 0:
            return color_text("No comments", "gray-3")
        else:
            return color_text(summary, "blue")
    
    elif mode == "long":
        if details:
            comment_lines = []
            for author, body_preview, created_at in details:
                # Format the timestamp to be more readable
                timestamp = created_at.split('T')[0] if 'T' in created_at else created_at
                comment_line = f"{color_text(author, 'yellow')}: {body_preview}"
                if timestamp:
                    comment_line += f" ({color_text(timestamp, 'gray-3')})"
                comment_lines.append(comment_line)
            return "\n\t\t".join(comment_lines)
        else:
            return "No comments available"
    
    else:
        raise ValueError(f"Unknown mode: {mode}")