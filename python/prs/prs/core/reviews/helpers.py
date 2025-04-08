from prs.core.models import PullRequest
from prs.utils.formatting import color_text


def analyze_reviews(pr: PullRequest):
    """
    Analyzes the reviews on the given PR.

    Returns a tuple:
      (summary, details)
    where summary is a string:
      - "N/A" if there are no reviews,
      - "APPROVED" if any review is APPROVED,
      - otherwise "REVIEW_REQUIRED"
    and details is a list of tuples (state, author, color)
    for each unique reviewer.
    """
    total = 0
    approved = False
    details = []
    seen_authors = set()
    for review in pr.reviews:
        author = review.get("author")
        # Skip duplicate authors
        if author in seen_authors:
            continue
        seen_authors.add(author)
        state = review.get("state", "N/A").upper()
        total += 1
        if state == "APPROVED":
            approved = True
        if state == "CHANGES_REQUESTED":
            color = "red"
        elif state == "COMMENTED":
            color = "yellow"
        elif state == "APPROVED":
            color = "green"
        else:
            color = "red"
        details.append((state, author, color))
    if total == 0:
        summary = "N/A"
    elif approved:
        summary = "APPROVED"
    else:
        summary = "REVIEW_REQUIRED"
    return summary, details


def get_reviews(pr: PullRequest, mode: str) -> str:
    """
    Formats the reviews information based on the provided mode.

    Modes:
      - "none": returns an empty string.
      - "short": returns a colored summary string.
      - "normal": returns a colored summary string (same as short).
      - "long": returns a detailed multi-line string with each review.

    Raises:
      ValueError: if an unknown mode is provided.
    """
    summary, details = analyze_reviews(pr)

    if mode == "none":
        return ""

    elif mode == "short":
        if summary == "APPROVED":
            return color_text("[RVWS]", "green")
        elif summary == "REVIEW_REQUIRED":
            return color_text("[RVWS]", "yellow")
        else:
            return color_text("[RVWS]", "red")
    elif mode == "normal":
        if summary == "APPROVED":
            return color_text("APPROVED", "green")
        elif summary == "REVIEW_REQUIRED":
            return color_text("REVIEW_REQUIRED", "yellow")
        else:
            return color_text(summary, "red")
    elif mode == "long":
        if details:
            return "\n\t\t".join(
                [
                    f"{color_text(state.ljust(14), color)} {author}"
                    for state, author, color in details
                ]
            )
        else:
            return "No reviews available"
    else:
        raise ValueError(f"Unknown mode: {mode}")
