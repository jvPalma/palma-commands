"""
Main entry point for PR listing and display functionality.

This module orchestrates the entire PR display process:
- Fetching PR data from the API
- Applying filters and sorting
- Rendering each PR using the display system
"""

from prs.config import get_ignored_prs, get_ignored_users
from prs.vc_tools.github.client import get_pull_request_details, list_pull_request_ids
from prs.core.display.display_config import resolve_display_modes
from prs.core.display.panel_renderer import render_pr_panel, render_ignored_count
from rich.console import Console


def filter_ignored_users_prs(prs: list, include_ignored_users: bool = False) -> tuple[list, int]:
    """
    Filter out PRs from ignored users unless explicitly included.
    
    Args:
        prs: List of PR objects
        include_ignored_users: Whether to include those PRs (default: False)
    
    Returns:
        Tuple of (filtered_prs, ignored_count) where ignored_count is number of filtered ignored PRs
    """
    if include_ignored_users:
        return prs, 0  # Return all PRs when ignored users are included

    ignored_users = get_ignored_users()
    if not ignored_users:
        return prs, 0  # No ignored users configured, return all PRs

    # Filter out PRs from ignored users
    ignored_users_prs = []
    filtered_prs = []
    
    for pr in prs:
        if pr.author in ignored_users:
            ignored_users_prs.append(pr)
        else:
            filtered_prs.append(pr)
    
    return filtered_prs, len(ignored_users_prs)


def list_pull_requests(options: dict) -> None:
    """
    Main function to list and display pull requests.
    
    This function:
    1. Resolves display modes from options and config
    2. Fetches PR data from the version control API
    3. Applies filters and sorting
    4. Renders each PR using the display system
    
    Args:
        options: Dictionary of CLI options for display customization
    """
    # Resolve all display modes from options and config
    modes = resolve_display_modes(options)
    
    # Set up filters for PR fetching
    filters = {
        "state": "open",
        "include_draft": modes["include_drafts"],
        "no_reviewer": options.get("no_reviewer", False),
        "no_reviewed": options.get("no_reviewed", False),
        "include_from_ignored_users": options.get("include_from_ignored_users", False),
    }

    # Fetch PR references and details
    pr_refs = list_pull_request_ids(filters)
    all_prs = []
    for pr_id, source_tag, is_draft in pr_refs:
        pr_model = get_pull_request_details(pr_id, source_tag)
        pr_model.source = source_tag
        pr_model.isDraft = is_draft
        all_prs.append(pr_model)

    # Sort PRs by PR number (ascending: oldest first, latest last)
    all_prs.sort(key=lambda pr: pr.id)

    # Filter out ignored PRs
    ignored_pr_numbers = get_ignored_prs()
    prs_after_ignored = [pr for pr in all_prs if pr.id not in ignored_pr_numbers]
    ignored_count = len(all_prs) - len(prs_after_ignored)

    # Filter out ignored user PRs unless explicitly included
    filtered_prs, ignored_users_count = filter_ignored_users_prs(prs_after_ignored, filters["include_from_ignored_users"])
    total_filtered_count = ignored_count + ignored_users_count

    # Initialize Rich console for output
    console = Console()

    # Render each PR as a panel
    for pr in filtered_prs:
        render_pr_panel(pr, modes, console)

    # Display ignored count if any PRs were filtered out
    render_ignored_count(total_filtered_count, console)