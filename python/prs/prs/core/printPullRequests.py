"""
Main entry point for PR listing and display functionality.

This module orchestrates the entire PR display process:
- Fetching PR data from the API
- Applying filters and sorting
- Rendering each PR using the display system
- Watch mode for real-time updates
"""

import asyncio
from prs.config import get_ignored_prs, get_ignored_users
from prs.vc_tools.github.client import get_pull_request_details, list_pull_request_ids  
from prs.core.display.display_config import resolve_display_modes
from prs.core.display.panel_renderer import render_pr_panel, render_ignored_count
from prs.core.watch import WatchController, WatchConfig
from prs.core.export import export_pull_requests
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


def fetch_and_filter_prs(options: dict) -> tuple[list, dict]:
    """
    Fetch and filter PR data. Separated for use in both regular and watch modes.
    
    Args:
        options: Dictionary of CLI options
        
    Returns:
        Tuple of (filtered_prs, modes)
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
        # Handle case where get_pull_request_details returns empty dict on error
        if isinstance(pr_model, dict) and not pr_model:
            continue  # Skip failed PR fetches
        pr_model.source = source_tag
        pr_model.isDraft = is_draft
        all_prs.append(pr_model)

    # Sort PRs by PR number (ascending: oldest first, latest last)
    all_prs.sort(key=lambda pr: pr.id)

    # Filter out ignored PRs
    ignored_pr_numbers = get_ignored_prs()
    prs_after_ignored = [pr for pr in all_prs if pr.id not in ignored_pr_numbers]

    # Filter out ignored user PRs unless explicitly included
    filtered_prs, ignored_users_count = filter_ignored_users_prs(prs_after_ignored, filters["include_from_ignored_users"])
    
    return filtered_prs, modes


def list_pull_requests(options: dict) -> None:
    """
    Main function to list and display pull requests.
    
    Supports regular display, watch mode, and JSON export.
    
    Args:
        options: Dictionary of CLI options for display customization
    """
    # Check if export mode is requested
    export_filename = options.get("export")
    
    if export_filename is not None:
        # Export mode
        _export_prs(options, export_filename)
    elif options.get("watch_interval") is not None:
        # Start watch mode
        asyncio.run(_start_watch_mode(options, options["watch_interval"]))
    else:
        # Regular single display mode
        _display_prs_once(options)


def _export_prs(options: dict, export_filename: str) -> None:
    """Export PRs to JSON file."""
    # Get ALL PRs including ignored ones for export
    filters = {
        "state": "open",
        "include_draft": options.get("include_draft", False),
        "no_reviewer": options.get("no_reviewer", False),
        "no_reviewed": options.get("no_reviewed", False),
    }
    
    # Fetch PR IDs
    pr_ids = list_pull_request_ids(filters)
    
    # Get ignored PR numbers
    ignored_pr_numbers = get_ignored_prs()
    
    # Fetch detailed information for ALL PRs (including ignored)
    all_prs = []
    for pr_id, source_tag, is_draft in pr_ids:
        pr_model = get_pull_request_details(pr_id, source_tag)
        # Handle case where get_pull_request_details returns empty dict on error
        if isinstance(pr_model, dict) and not pr_model:
            continue  # Skip failed PR fetches
        pr_model.source = source_tag
        pr_model.isDraft = is_draft
        all_prs.append(pr_model)
    
    # Filter ignored users but keep the PRs for export
    filtered_prs, ignored_users_count = filter_ignored_users_prs(
        all_prs, 
        include_ignored_users=True  # Include all for export
    )
    
    # Export to JSON
    export_pull_requests(
        pull_requests=filtered_prs,
        ignored_prs=ignored_pr_numbers,
        filters=filters,
        filename=export_filename if export_filename != "default" else None
    )


def _display_prs_once(options: dict) -> None:
    """Display PRs once in regular mode."""
    # Fetch and filter PRs
    filtered_prs, modes = fetch_and_filter_prs(options)
    
    # Calculate ignored count for display
    ignored_pr_numbers = get_ignored_prs()
    all_prs_count = len(filtered_prs) + len(ignored_pr_numbers)  # Approximate
    total_filtered_count = all_prs_count - len(filtered_prs)
    
    # Initialize Rich console for output
    console = Console()

    # Render each PR as a panel
    for pr in filtered_prs:
        render_pr_panel(pr, modes, console)

    # Display ignored count if any PRs were filtered out
    if total_filtered_count > 0:
        render_ignored_count(total_filtered_count, console)


async def _start_watch_mode(options: dict, watch_interval: int) -> None:
    """Start watch mode with real-time updates."""
    # Initialize Rich console
    console = Console()
    
    # Create watch configuration
    config = WatchConfig(
        interval=watch_interval,
        show_update_time=True,
        highlight_changes=True,
        max_cache_size=1000
    )
    
    # Create watch controller
    watch_controller = WatchController(console, config)
    
    # Start watch mode
    await watch_controller.start_watch_mode(fetch_and_filter_prs, options)