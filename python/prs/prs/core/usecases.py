from prs.config import get
from prs.core.author.helpers import get_author
from prs.core.checks.helpers import get_checks
from prs.core.labels.helpers import get_labels
from prs.core.reviews.helpers import get_reviews
from prs.core.title.helpers import compute_open_status, format_title
from prs.utils.formatting import OutputBuilder, color_text
from prs.vc_tools.github.client import get_pull_request_details, list_pull_request_ids


def list_pull_requests(options: dict):
    # Read display modes from CLI options or config as fallback.
    include_drafts = options.get("include_draft", False)

    author_mode = options.get("author", get("pr-info", "author", fallback="short"))
    checks_mode = options.get("checks", get("pr-info", "checks", fallback="short"))
    review_mode = options.get("reviews", get("pr-info", "reviews", fallback="short"))
    labels_mode = options.get("labels", get("pr-info", "labels", fallback="short"))
    pr_url_mode = options.get("pr_url", get("pr-info", "pr_url", fallback="normal"))
    branch_mode = options.get("branch", get("pr-info", "branch", fallback="normal"))

    filters = {
        "state": "open",
        "include_draft": include_drafts,
    }

    pr_refs = list_pull_request_ids(filters)
    all_prs = []
    for pr_id, source_tag, is_draft in pr_refs:
        pr_model = get_pull_request_details(pr_id)
        pr_model.source = source_tag
        pr_model.isDraft = is_draft
        all_prs.append(pr_model)

    ob = OutputBuilder()

    for pr in all_prs:
        # Format PR number to always occupy 6 characters with leading zeros.
        pr_number = color_text(f"#{pr.id:06d}", "gray-4")
        # Format title to 70 characters; if PR is draft, color it gray-4; otherwise blue.
        title_formatted = format_title(pr.title)
        pr_title = (
            color_text(title_formatted, "gray-3")
            if pr.isDraft
            else color_text(title_formatted, "blue")
        )

        # First line: PR number and title.
        ob.add_line(f"{pr_number} {pr_title}")

        # Summary line: structured summary.
        summary_line = []

        #! OPEN
        open_text, open_color = compute_open_status(pr)
        summary_line.append(color_text(f"[{open_text}]", open_color))

        #! CHECKS
        checks_text = get_checks(pr, checks_mode)
        if checks_mode == "short":
            summary_line.append(checks_text)

        #! RVWS
        reviews_text = get_reviews(pr, review_mode)
        if review_mode == "short":
            summary_line.append(reviews_text)

        #! LBLS
        labels_text = get_labels(pr, labels_mode)
        if labels_mode == "short":
            summary_line.append(labels_text)

        #! AUTH
        summary_line.append(get_author(pr, author_mode))

        # ** SUMMARY LINE
        ob.add_line("    " + " ".join(str(x) for x in summary_line))

        # ? URL
        if pr_url_mode != "none":
            ob.add_line("    [LINK] " + color_text(f"{pr.url}", "blue"))

        # ? BRANCH
        if branch_mode != "none":
            ob.add_line("    [BNCH] " + color_text(f"{pr.branch}", "yellow"))

        # ? CHECKS
        if checks_mode == "normal" or checks_mode == "long":
            ob.add_line("        Checks: " + checks_text)

        # ? RVWS
        if review_mode == "normal" or review_mode == "long":
            ob.add_line("        Review: " + reviews_text)

        # ? LBLS
        if labels_mode == "normal" or labels_mode == "long":
            ob.add_line("        Labels: " + labels_text)

        ob.add_line("")  # Blank line between PRs

    print(ob.get_output())
