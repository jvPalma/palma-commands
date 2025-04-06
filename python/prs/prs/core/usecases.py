from prs.config import get
from prs.core.author.helpers import compute_author_status
from prs.core.checks.helpers import compute_checks_status
from prs.core.labels.helpers import compute_labels_status
from prs.core.reviews.helpers import compute_reviews_status
from prs.core.title.helpers import compute_open_status, format_title
from prs.utils.formatting import OutputBuilder, color_text
from prs.vc_tools.github.adapter import to_model
from prs.vc_tools.github.client import get_pull_request_details, list_pull_request_ids


def list_pull_requests(options: dict):
    config_username = get("git", "username")
    filters = {
        "author": config_username,
        "state": "open",
        "include_draft": options.get("include_draft", False),
    }
    pr_refs = list_pull_request_ids(filters)
    all_prs = []
    for pr_id, source_tag, is_draft in pr_refs:
        raw = get_pull_request_details(pr_id)
        pr_model = to_model(raw)
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

        # Second summary line: structured summary.
        open_text, open_color = compute_open_status(pr)
        reviews_text, reviews_color = compute_reviews_status(pr)
        checks_text, checks_color = compute_checks_status(pr)
        labels_text, labels_color = compute_labels_status(pr)
        formatted_author = compute_author_status(pr)

        summary_line = "\t" + " ".join(
            [
                color_text(f"[{open_text}]", open_color),
                color_text(f"[{reviews_text}]", reviews_color),
                color_text(f"[{checks_text}]", checks_color),
                color_text(f"[{labels_text}]", labels_color),
                formatted_author,
            ]
        )
        ob.add_line(summary_line)
        ob.add_line("")  # Blank line between PRs

    print(ob.get_output())
