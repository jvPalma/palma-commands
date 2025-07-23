"""
Main entry point for PR listing and display functionality.

This module orchestrates the entire PR display process:
- Fetching PR data from the API
- Applying filters and sorting
- Rendering each PR using the display system
"""

from prs.config import get_ignored_prs
from prs.vc_tools.github.client import get_pull_request_details, list_pull_request_ids
from prs.core.display.display_config import resolve_display_modes
from prs.core.display.panel_renderer import render_pr_panel, render_ignored_count
from rich.console import Console


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
    }

    # Fetch PR references and details
    pr_refs = list_pull_request_ids(filters)
    all_prs = []
    for pr_id, source_tag, is_draft in pr_refs:
        pr_model = get_pull_request_details(pr_id)
        pr_model.source = source_tag
        pr_model.isDraft = is_draft
        all_prs.append(pr_model)

    # Sort PRs by PR number (ascending: oldest first, latest last)
    all_prs.sort(key=lambda pr: pr.id)

    # Filter out ignored PRs
    ignored_pr_numbers = get_ignored_prs()
    filtered_prs = [pr for pr in all_prs if pr.id not in ignored_pr_numbers]
    ignored_count = len(all_prs) - len(filtered_prs)

    # Initialize Rich console for output
    console = Console()

    # Render each PR as a panel
    for pr in filtered_prs:
        render_pr_panel(pr, modes, console)

    # Display ignored count if any PRs were filtered out
    render_ignored_count(ignored_count, console)