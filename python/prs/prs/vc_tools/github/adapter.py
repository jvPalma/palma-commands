from prs.core.models import PullRequest


def to_model(pr_json: dict) -> PullRequest:
    """
    Transform the raw JSON from get_pull_request_details into a PullRequest model.
    """
    pr_id = pr_json.get("number", 0)
    title = pr_json.get("title", "")
    author = pr_json.get("author", {}).get("login", "")
    labels = [lbl.get("name", "") for lbl in pr_json.get("labels", [])]
    checks_raw = pr_json.get("statusCheckRollup", [])
    reviews_raw = pr_json.get("reviews", [])
    url = pr_json.get("url", "")
    branch = pr_json.get("headRefName", "")
    is_draft = pr_json.get("isDraft", False)

    return PullRequest(
        id=pr_id,
        title=title,
        author=author,
        labels=labels,
        checks=checks_raw,
        reviews=reviews_raw,
        url=url,
        branch=branch,
        is_draft=is_draft,
    )
