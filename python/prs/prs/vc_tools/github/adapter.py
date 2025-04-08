import pprint

from prs.core.models import PullRequest


def pr_info_to_model(pr_json: dict) -> PullRequest:
    """
    Transform the raw JSON from get_pull_request_details into a PullRequest model.
    """
    pr_id = pr_json.get("number", 0)
    title = pr_json.get("title", "")
    is_draft = pr_json.get("isDraft", False)
    
    author = pr_json.get("author", {}).get("login", "")
    
    url = pr_json.get("url", "")
    branch = pr_json.get("headRefName", "")

    checks_raw = pr_json.get("statusCheckRollup", [])
    
    reviews_raw = pr_json.get("reviews", [])
    reviewRequests_raw = pr_json.get("reviewRequests", [])
    
    labels = [lbl.get("name", "") for lbl in pr_json.get("labels", [])]
    

    printer = pprint.PrettyPrinter(indent=4)
    print("\n\ndetails for PR #", pr_id, ":")
    print("\nReviews:")
    printer.pprint(reviews_raw)

    print("\nReview Requests:")
    printer.pprint(reviewRequests_raw)

    print("\n")

    return PullRequest(
        id=pr_id,
        title=title,
        is_draft=is_draft,
        url=url,
        branch=branch,
        author=author,
        labels=labels,
        checks=checks_raw,
        reviews=reviews_raw,
    )
