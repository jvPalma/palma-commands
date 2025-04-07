def compute_open_status(pr):
    if pr.isDraft:
        return "DRFT", "gray-4"
    else:
        return "OPEN", "green"


def format_title(title: str) -> str:
    # Truncate to 70 characters; if longer, truncate to 67 and add ellipsis.
    if len(title) > 70:
        return title[:67] + "..."
    else:
        return title.ljust(70)
