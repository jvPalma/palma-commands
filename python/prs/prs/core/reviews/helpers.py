from prs.utils.formatting import color_text


def format_reviews(pr, mode: str) -> str:
    """
    Returns a formatted string for the reviews information.
    Mode can be "none", "short", or "long".
    """
    if mode == "none":
        return ""
    if mode == "short":
        overall = pr.reviews[0].get("state", "N/A") if pr.reviews else "N/A"
        if overall.upper() == "APPROVED":
            return color_text("APPROVED", "green")
        elif overall.upper() == "REVIEW_REQUIRED":
            return color_text("REVIEW_REQUIRED", "yellow")
        else:
            return color_text(overall, "red")
    else:  # mode == "long"
        details = []
        seen_authors = set()
        for review in pr.reviews:
            author = review.get("author", {}).get("login", "unknown")
            if author in seen_authors:
                continue
            seen_authors.add(author)
            state = review.get("state", "N/A")
            if state.upper() == "CHANGES_REQUESTED":
                color = "red"
            elif state.upper() == "COMMENTED":
                color = "yellow"
            else:
                color = "green"
            details.append(f"{color_text(state.ljust(14), color)} {author}")
        return "\n\t\t".join(details) if details else "No reviews available"


def compute_reviews_status(pr):
    approved = False
    if pr.reviews:
        for review in pr.reviews:
            if review.get("state", "").upper() == "APPROVED":
                approved = True
                break
    return "RVWS", "green" if approved else "yellow"
