import json
import subprocess

from prs.config import get
from prs.core.helpers import read_authors, resolve_owner
from prs.vc_tools.github.adapter import pr_info_to_model


def get_authenticated_user() -> str:
    """
    Fetches the authenticated GitHub username using 'gh api user'.
    Returns the username of the currently authenticated user.
    """
    gh_args = ["gh", "api", "user", "--jq", ".login"]
    try:
        output = subprocess.check_output(gh_args, text=True)
        return output.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error fetching authenticated user: {e}")
        return ""


def list_all_prs(filters: dict):
    """
    Uses 'gh api' with the search/issues endpoint to fetch PRs for each author.
    Also fetches PRs where the authenticated user is a reviewer.
    Aggregates and deduplicates the results, sorts them by updated_at descending.
    """
    owner = resolve_owner()
    repo_name = get("git", "repo_name")
    authors = read_authors()
    all_results = []
    seen_pr_numbers = set()  # To track PRs we've already added
    state_value = filters.get("state")
    draft_value = filters["include_draft"]
    
    # Check if no_reviewer option is set in filters (from CLI)
    no_reviewer = filters.get("no_reviewer", False)
    # Check if no_reviewed option is set in filters (from CLI)
    no_reviewed = filters.get("no_reviewed", False)

    if draft_value:  # If include_draft is True, we want to INCLUDE draft PRs, so we exclude the "draft:" filter.
        draft_value = ""
    else:  # If include_draft is False, we include the "draft:false" to filter them out.
        draft_value = "draft:false"

    # First, fetch PRs authored by configured authors
    for author in authors:
        query = f"repo:{owner}/{repo_name} is:pr is:{state_value} {draft_value} author:{author}"
        gh_args = [
            "gh",
            "api",
            "-X",
            "GET",
            "search/issues",
            "-f",
            f"q={query}",
            "-f",
            "page=1",
            "-f",
            "per_page=10",  # Increased to handle more PRs
            "--jq",
            ".items | .[] | {number: .number, user: .user.login, updated_at: .updated_at, isDraft: (.draft // false), source: \"authored\"}",
        ]
        try:
            output = subprocess.check_output(gh_args, text=True)
            # Split output into lines and parse each JSON object.
            results = [json.loads(line) for line in output.splitlines() if line.strip()]
            for result in results:
                if result["number"] not in seen_pr_numbers:
                    all_results.append(result)
                    seen_pr_numbers.add(result["number"])
        except subprocess.CalledProcessError as e:
            print(f"Error calling gh api for author {author}: {e}")
            continue

    # Now fetch PRs where the authenticated user is a reviewer (if enabled)
    # Check both config and CLI option - CLI takes precedence
    include_reviewer_prs = get("filters", "include_reviewer_prs", fallback="true").lower() == "true"
    if include_reviewer_prs and not no_reviewer:
        auth_user = get_authenticated_user()
        if auth_user:
            # First, fetch PRs where user has pending review requests
            query = f"repo:{owner}/{repo_name} is:pr is:{state_value} {draft_value} review-requested:{auth_user}"
            gh_args = [
                "gh",
                "api",
                "-X",
                "GET",
                "search/issues",
                "-f",
                f"q={query}",
                "-f",
                "page=1",
                "-f",
                "per_page=10",  # Increased to handle more PRs
                "--jq",
                ".items | .[] | {number: .number, user: .user.login, updated_at: .updated_at, isDraft: (.draft // false), source: \"reviewer_pending\"}",
            ]
            try:
                output = subprocess.check_output(gh_args, text=True)
                # Split output into lines and parse each JSON object.
                results = [json.loads(line) for line in output.splitlines() if line.strip()]
                for result in results:
                    if result["number"] not in seen_pr_numbers:
                        all_results.append(result)
                        seen_pr_numbers.add(result["number"])
                    else:
                        # Update source to handle combined roles - prioritize pending reviews
                        for pr in all_results:
                            if pr["number"] == result["number"]:
                                if pr["source"] == "authored":
                                    pr["source"] = "both_pending"  # Author + pending reviewer
                                elif pr["source"] == "reviewer_completed":
                                    pr["source"] = "reviewer_pending"  # Upgrade completed to pending
                                break
            except subprocess.CalledProcessError as e:
                print(f"Error calling gh api for pending reviewer {auth_user}: {e}")

            # Second, fetch PRs where user has already given reviews (but may not have pending requests)
            # Check if include_reviewed_prs is enabled AND no_reviewed CLI option is not set
            include_reviewed_prs = get("filters", "include_reviewed_prs", fallback="true").lower() == "true"
            if include_reviewed_prs and not no_reviewed:
                query = f"repo:{owner}/{repo_name} is:pr is:{state_value} {draft_value} reviewed-by:{auth_user}"
                gh_args = [
                    "gh",
                    "api",
                    "-X",
                    "GET",
                    "search/issues",
                    "-f",
                    f"q={query}",
                    "-f",
                    "page=1",
                    "-f",
                    "per_page=10",  # Increased to handle more PRs
                    "--jq",
                    ".items | .[] | {number: .number, user: .user.login, updated_at: .updated_at, isDraft: (.draft // false), source: \"reviewer_completed\"}",
                ]
                try:
                    output = subprocess.check_output(gh_args, text=True)
                    # Split output into lines and parse each JSON object.
                    results = [json.loads(line) for line in output.splitlines() if line.strip()]
                    for result in results:
                        if result["number"] not in seen_pr_numbers:
                            # Only add if this PR isn't already tracked with a higher priority status
                            all_results.append(result)
                            seen_pr_numbers.add(result["number"])
                        else:
                            # Update source to handle combined roles - prioritize pending over completed
                            for pr in all_results:
                                if pr["number"] == result["number"]:
                                    if pr["source"] == "authored":
                                        pr["source"] = "both_completed"  # Author + completed reviewer
                                    elif pr["source"] == "reviewer_pending":
                                        # Don't downgrade pending to completed
                                        pass
                                    elif pr["source"] == "both_pending":
                                        # Don't downgrade pending to completed
                                        pass
                                    # If already reviewer_completed, no change needed
                                    break
                except subprocess.CalledProcessError as e:
                    print(f"Error calling gh api for completed reviewer {auth_user}: {e}")

    sorted_results = sorted(all_results, key=lambda x: x["updated_at"], reverse=True)
    return sorted_results


def list_pull_request_ids(filters: dict) -> list[tuple[int, str, bool]]:
    """
    Calls list_all_prs to aggregate PRs from all authors and returns a list of tuples:
      (pr_id, source_tag, isDraft)
    The source_tag indicates whether the PR was authored, review-requested, or both.
    """
    data = list_all_prs(filters)
    result = []
    for pr in data:
        number = pr.get("number")
        is_draft = pr.get("isDraft", False)
        source = pr.get("source", "authored")  # Default to authored if not specified
        if number is not None:
            result.append((number, source, is_draft))
    return result


def get_pull_request_details(pr_id: int, source_tag: str = None) -> dict:
    """
    Calls 'gh pr view <pr_id>' to get the full JSON details for a given PR.
    Returns the raw JSON as a dictionary.
    """
    owner = resolve_owner()
    repo_name = get("git", "repo_name")
    gh_args = [
        "gh",
        "pr",
        "view",
        str(pr_id),
        "--repo",
        f"{owner}/{repo_name}",
        "--json",
        "number,title,author,labels,statusCheckRollup,reviews,reviewRequests,url,headRefName,isDraft",
    ]
    try:
        output = subprocess.check_output(gh_args, text=True)
        data = json.loads(output)
        return pr_info_to_model(data, source_tag)
    except subprocess.CalledProcessError as e:
        print("Error fetching details for PR #", pr_id, e)
        return {}
