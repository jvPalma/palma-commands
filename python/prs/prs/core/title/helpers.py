def compute_open_status(pr):
    # [OPEN]: green if not draft; gray-4 if draft.
    return "OPEN", "gray-4" if pr.isDraft else "green"


def format_title(title: str) -> str:
    # Truncate to 70 characters; if longer, truncate to 67 and add ellipsis.
    if len(title) > 70:
        return title[:67] + "..."
    else:
        return title.ljust(70)
