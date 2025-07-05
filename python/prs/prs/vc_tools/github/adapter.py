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
    comments_raw = pr_json.get("comments", [])
    
    labels = [lbl.get("name", "") for lbl in pr_json.get("labels", [])]
    
    # Extract new fields
    additions = pr_json.get("additions", 0)
    deletions = pr_json.get("deletions", 0)
    changed_files = pr_json.get("changedFiles", 0)
    created_at = pr_json.get("createdAt")
    updated_at = pr_json.get("updatedAt")
    state = pr_json.get("state", "open")
    commits = pr_json.get("commits", [])
    merged_at = pr_json.get("mergedAt")
    merged = merged_at is not None  # If mergedAt exists, it's merged
    closed_at = pr_json.get("closedAt")
    merged_by = pr_json.get("mergedBy")
    
    return PullRequest(
        id=pr_id,
        title=title,
        author=author,
        labels=labels,
        checks=checks_raw,
        reviews=reviews_raw,
        comments=comments_raw,
        url=url,
        branch=branch,
        is_draft=is_draft,
        additions=additions,
        deletions=deletions,
        changed_files=changed_files,
        created_at=created_at,
        updated_at=updated_at,
        state=state,
        commits=commits,
        merged=merged,
        merged_at=merged_at,
        closed_at=closed_at,
        merged_by=merged_by,
    )
