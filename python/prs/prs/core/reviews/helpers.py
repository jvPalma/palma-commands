from prs.core.models import PullRequest
from prs.utils.formatting import color_text


def analyze_reviews(pr: PullRequest):
    """
    Analyzes the reviews on the given PR, including pending review requests.

    Returns a tuple:
      (summary, details)
    where summary is a string:
      - "N/A" if there are no reviews and no review requests,
      - "APPROVED" if any review is APPROVED,
      - otherwise "REVIEW_REQUIRED"
    and details is a list of tuples (state, author, color)
    for each unique reviewer (including requested reviewers).
    """
    total = 0
    approved = False
    details = []
    seen_authors = set()
    
    # Process completed reviews
    for review in pr.reviews:
        author = review.get("author")
        # Extract author login from the author dict
        author_login = author.get("login") if author else None
        # Skip duplicate authors
        if author_login in seen_authors:
            continue
        seen_authors.add(author_login)
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
        details.append((state, author_login, color))
    
    # Process pending review requests
    for request in pr.review_requests:
        # Review requests can be for users or teams
        if isinstance(request, dict):
            # Check if it's a user request
            if "login" in request:
                author_login = request.get("login")
            # Check if it's a team request
            elif "name" in request:
                author_login = f"team:{request.get('name')}"
            else:
                continue
                
            # Skip if this author already has a completed review
            if author_login in seen_authors:
                continue
                
            seen_authors.add(author_login)
            total += 1
            # Pending review requests are shown in gray
            details.append(("PENDING", author_login, "gray"))
    
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
