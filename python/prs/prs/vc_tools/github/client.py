import json
import subprocess

from prs.config import get
from prs.core.helpers import read_authors, resolve_owner


def list_all_prs(filters: dict):
    """
    Uses 'gh api' with the search/issues endpoint to fetch PRs for each author.
    For each author from the config, executes the command:
      gh api -X GET search/issues -f q="repo:{owner}/{repo_name} is:pr is:open author:{author}"
      -f page=1 -f per_page=5 --jq '.items | .[] | {number: .number, user: .user.login, updated_at: .updated_at, isDraft: (.draft // false)}'
    Aggregates the results from all authors, sorts them by updated_at descending, and returns the list.
    """
    owner = resolve_owner()
    repo_name = get("git", "repo_name")
    authors = read_authors()
    all_results = []
    state_value = filters.get("state")
    draft_value = filters["include_draft"]

    for author in authors:
        query = f"repo:{owner}/{repo_name} is:pr is:{state_value} draft:{draft_value} author:{author}"
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
            "per_page=5",
            "--jq",
            ".items | .[] | {number: .number, user: .user.login, updated_at: .updated_at, isDraft: (.draft // false)}",
        ]
        try:
            output = subprocess.check_output(gh_args, text=True)
            # Split output into lines and parse each JSON object.
            results = [json.loads(line) for line in output.splitlines() if line.strip()]
            all_results.extend(results)
        except subprocess.CalledProcessError as e:
            print(f"Error calling gh api for author {author}: {e}")
            continue

    sorted_results = sorted(all_results, key=lambda x: x["updated_at"], reverse=True)
    return sorted_results


def list_pull_request_ids(filters: dict) -> list[tuple[int, str, bool]]:
    """
    Calls list_all_prs to aggregate PRs from all authors and returns a list of tuples:
      (pr_id, source_tag, isDraft)
    """
    data = list_all_prs(filters)
    result = []
    for pr in data:
        number = pr.get("number")
        is_draft = pr.get("isDraft", False)
        if number is not None:
            result.append((number, "multi", is_draft))
    return result


def get_pull_request_details(pr_id: int) -> dict:
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
        "number,title,author,labels,statusCheckRollup,reviews,url,headRefName,isDraft",
    ]
    try:
        output = subprocess.check_output(gh_args, text=True)
        data = json.loads(output)
        return data
    except subprocess.CalledProcessError as e:
        print("Error fetching details for PR #", pr_id, e)
        return {}
