import argparse
import os
import sys
import time
from datetime import datetime

from prs.config import all_config, get, set
from prs.core.analytics import show_pr_analytics, show_pr_history, show_pr_analytics_extended
from prs.core.history_builder import build_pr_history, clear_pr_history, update_pr_history
from prs.core.usecases import list_pull_requests

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax


def show_chunk_examples():
    """Show examples of chunk-based processing commands."""
    console = Console()
    
    console.print()
    console.print(Panel.fit(
        "[bold cyan]🔄 Chunk-Based Processing Examples[/bold cyan]",
        border_style="cyan"
    ))
    
    # Basic Chunk Processing
    basic_commands = """# Build history using quarterly chunks
nprs build-history --chunk
nprs build-history --chunk --incremental"""
    
    console.print(f"\n[bold yellow]📝 Basic Chunk Processing:[/bold yellow]")
    console.print(Panel(basic_commands, border_style="yellow", padding=(0, 1)))
    
    # Time Range Examples
    time_commands = """# Process last 5 years (2020-2025)
nprs build-history --chunk --start-year 2020 --end-year 2025

# Process recent data only (last 2 years)
nprs build-history --chunk --start-year 2023

# Process all available data
nprs build-history --chunk --all"""
    
    console.print(f"\n[bold yellow]📅 Time Range Examples:[/bold yellow]")
    console.print(Panel(time_commands, border_style="yellow", padding=(0, 1)))
    
    # Testing & Optimization
    test_commands = """# Test with limited chunks
nprs build-history --chunk --max-chunks 4

# Process with custom limits
nprs build-history --chunk --limit 25 --max-chunks 8

# Use incremental updates for better data merging
nprs build-history --chunk --incremental --limit 50"""
    
    console.print(f"\n[bold yellow]🔧 Testing & Optimization:[/bold yellow]")
    console.print(Panel(test_commands, border_style="yellow", padding=(0, 1)))
    
    # Multi-User Processing
    user_commands = """# Process specific users with chunks
nprs build-history --chunk --users 'user1,user2,user3'

# Combine with incremental updates
nprs build-history --chunk --incremental --users 'user1,user2'"""
    
    console.print(f"\n[bold yellow]👥 Multi-User Processing:[/bold yellow]")
    console.print(Panel(user_commands, border_style="yellow", padding=(0, 1)))
    
    # Production Examples
    prod_commands = """# Complete history build (recommended)
nprs build-history --chunk --incremental --all

# Recent data update
nprs build-history --chunk --incremental --max-chunks 8

# Large team processing
nprs build-history --chunk --incremental --users 'team1,team2,team3' --limit 30"""
    
    console.print(f"\n[bold yellow]🚀 Production Examples:[/bold yellow]")
    console.print(Panel(prod_commands, border_style="yellow", padding=(0, 1)))
    
    # Tips & Best Practices
    tips = """• Use --incremental for better data merging and conflict resolution
• Start with --max-chunks 4 to test before processing all data
• Use --limit 25-50 to avoid API rate limits
• Combine --chunk with --incremental for optimal performance
• Use --start-year to focus on recent data if needed"""
    
    console.print(f"\n[bold cyan]💡 Tips & Best Practices:[/bold cyan]")
    console.print(Panel(tips, border_style="cyan", padding=(0, 1)))
    
    # Important Notes
    notes = """• Chunk processing is more efficient for large datasets
• Each quarter is processed separately with clear progress indicators
• API rate limits are automatically handled with retries
• Incremental updates preserve existing data while adding new information
• Use 'nprs analytics' to view results after building history"""
    
    console.print(f"\n[bold yellow]⚠️  Important Notes:[/bold yellow]")
    console.print(Panel(notes, border_style="yellow", padding=(0, 1)))
    
    # Related Commands
    related_commands = """nprs analytics              # View PR analytics
nprs analytics --extended   # Detailed analytics
nprs history 123           # View specific PR history
nprs clear-history         # Clear cached history"""
    
    console.print(f"\n[bold green]🔍 Related Commands:[/bold green]")
    console.print(Panel(related_commands, border_style="green", padding=(0, 1)))
    console.print()


def run_cli():
    parser = argparse.ArgumentParser(
        prog="nprs", description="PRS - Pull Request Status CLI"
    )
    # Global arguments for the list command
    parser.add_argument(
        "--draft", "-d", action="store_true", default=False, help="Include draft PRs"
    )
    parser.add_argument(
        "--pr_url",
        type=str,
        choices=["none", "short", "normal", "long"],
        default=None,
        help="Set display verbosity for PR URL",
    )
    parser.add_argument(
        "--branch",
        "-b",
        type=str,
        choices=["none", "short", "normal", "long"],
        default=None,
        help="Set display verbosity for branch",
    )
    parser.add_argument(
        "--checks",
        "-c",
        type=str,
        choices=["none", "short", "normal", "long"],
        default=None,
        help="Set display verbosity for checks",
    )
    parser.add_argument(
        "--reviews",
        "-r",
        type=str,
        choices=["none", "short", "normal", "long"],
        default=None,
        help="Set display verbosity for reviews",
    )
    parser.add_argument(
        "--labels",
        "-l",
        type=str,
        choices=["none", "short", "normal", "long"],
        default=None,
        help="Set display verbosity for labels",
    )
    parser.add_argument(
        "--comments",
        type=str,
        choices=["none", "short", "normal", "long"],
        default=None,
        help="Set display verbosity for comments",
    )
    parser.add_argument(
        "--watch",
        "-w",
        type=int,
        metavar="SECONDS",
        default=None,
        help="Watch mode: refresh every N seconds (default: 10)",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["panels", "table"],
        default="panels",
        help="Display format (default: panels)",
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command")

    # 'config' subcommand
    config_parser = subparsers.add_parser("config", help="Get or set configuration")
    config_parser.add_argument("action", choices=["get", "set", "all"])
    config_parser.add_argument("key", nargs="?", help="Ex: git.username")
    config_parser.add_argument(
        "value", nargs="?", help="Value to set (used with 'set')"
    )
    
    # 'analytics' subcommand
    analytics_parser = subparsers.add_parser("analytics", help="View PR analytics from cache")
    analytics_parser.add_argument("--mode", choices=["short", "normal", "long", "extended", "table"], default="normal", help="Analytics verbosity level")
    analytics_parser.add_argument("--user", type=str, help="View analytics for a specific user (e.g., 'palma-anchor')")
    analytics_parser.add_argument("--compare", type=str, help="Compare analytics for multiple users (comma-separated, e.g., 'user1,user2,user3')")
    analytics_parser.add_argument("--equal", action="store_true", help="When comparing, use equal sample size (minimum PR count) for all users")
    analytics_parser.add_argument("--no-limit", action="store_true", help="Allow comparing more than 6 users (may impact display performance)")
    analytics_parser.add_argument("--from", dest="from_date", type=str, help="Start date for analytics (YYYY-MM-DD format, e.g., '2022-09-30')")
    analytics_parser.add_argument("--to", dest="to_date", type=str, help="End date for analytics (YYYY-MM-DD format, defaults to today)")
    analytics_parser.add_argument("--approvers", type=str, help="Filter table mode to specific approvers (comma-separated)")
    analytics_parser.add_argument("--pr-limit", type=int, help="Limit number of PRs shown in table mode")
    analytics_parser.add_argument("--ranking-limit", type=int, help="Limit number of approvers/reviewers shown in rankings")
    analytics_parser.add_argument("--top-approvers", type=int, default=3, help="Number of top approvers to show (default: 3)")
    
    # 'history' subcommand
    history_parser = subparsers.add_parser("history", help="View history for a specific PR")
    history_parser.add_argument("pr_id", type=int, help="PR number to view history for")
    
    # 'build-history' subcommand
    build_history_parser = subparsers.add_parser("build-history", help="Build PR history by fetching PRs")
    build_history_parser.add_argument("--limit", type=int, default=50, help="Number of PRs to fetch (default: 50)")
    build_history_parser.add_argument("--all", action="store_true", help="Fetch all PRs (open, closed, merged)")
    build_history_parser.add_argument("--users", type=str, help="Comma-separated list of users to build history for (e.g., 'palma-anchor,rpereira-anchor')")
    build_history_parser.add_argument("--chunk", action="store_true", help="Use quarterly chunks for efficient historical data fetching")
    build_history_parser.add_argument("--incremental", action="store_true", help="Update existing PRs with new data instead of skipping (use intelligent data merging)")
    build_history_parser.add_argument("--start-year", type=int, help="Earliest year to fetch (e.g., 2022, default: 10 years ago)")
    build_history_parser.add_argument("--end-year", type=int, help="Latest year to fetch (defaults to current year)")
    build_history_parser.add_argument("--max-chunks", type=int, help="Maximum number of quarterly chunks to process (useful for testing)")
    
    # 'update-history' subcommand
    update_history_parser = subparsers.add_parser("update-history", help="Update existing PR history with latest data")
    update_history_parser.add_argument("--users", type=str, help="Comma-separated list of users to update history for (e.g., 'palma-anchor,rpereira-anchor')")
    update_history_parser.add_argument("--limit", type=int, help="Limit number of PRs to update per user")
    update_history_parser.add_argument("--force", action="store_true", help="Force update all fields even if they already exist")
    
    # 'clear-history' subcommand
    clear_history_parser = subparsers.add_parser("clear-history", help="Clear PR history cache")
    
    # 'chunk-examples' subcommand
    chunk_examples_parser = subparsers.add_parser("chunk-examples", help="Show examples of chunk-based processing")

    args = parser.parse_args()

    # If no subcommand provided, default to "list"
    if args.command is None:
        args.command = "list"

    if args.command == "list":
        options = {"include_draft": args.draft}
        if args.pr_url is not None:
            options["pr_url"] = args.pr_url
        if args.branch is not None:
            options["branch"] = args.branch
        if args.checks is not None:
            options["checks"] = args.checks
        if args.reviews is not None:
            options["reviews"] = args.reviews
        if args.labels is not None:
            options["labels"] = args.labels
        if args.comments is not None:
            options["comments"] = args.comments
        
        # Add display format option
        options["format"] = args.format

        # Handle watch mode
        if args.watch is not None:
            interval = args.watch if args.watch > 0 else 10
            try:
                console = Console()
                while True:
                    # Clear screen
                    os.system('clear' if os.name == 'posix' else 'cls')
                    
                    # Print header with timestamp
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    console.print(Panel.fit(
                        f"[bold cyan]🔄 PRS Watch Mode[/bold cyan] - Refreshing every [yellow]{interval}s[/yellow] - Last update: [green]{timestamp}[/green]\nPress [red]Ctrl+C[/red] to exit",
                        border_style="cyan"
                    ))
                    console.print()
                    
                    # List pull requests
                    list_pull_requests(options)
                    
                    # Wait for the specified interval with countdown
                    console.print(f"\n[yellow]⏱️  Next refresh in {interval} seconds...[/yellow]", end='')
                    for i in range(interval, 0, -1):
                        console.print(f"\r[yellow]⏱️  Next refresh in {i} seconds...[/yellow]", end='')
                        time.sleep(1)
                    console.print("\r" + " " * 50 + "\r", end='')  # Clear the countdown line
            except KeyboardInterrupt:
                console = Console()
                console.print("\n\n[bold yellow]✋ Watch mode stopped[/bold yellow]")
                sys.exit(0)
        else:
            # Normal mode - just list once
            list_pull_requests(options)
    elif args.command == "config":
        console = Console()
        if args.action == "get":
            if not args.key:
                console.print("[red]You must provide a key. Example: git.username[/red]")
                sys.exit(1)
            section, key = args.key.split(".")
            value = get(section, key)
            console.print(f"[cyan]{section}.{key}[/cyan] = [green]{value}[/green]")
        elif args.action == "set":
            if not args.key or not args.value:
                console.print("[red]Usage: nprs config set git.username yourName[/red]")
                sys.exit(1)
            section, key = args.key.split(".")
            set(section, key, args.value)
            console.print(f"[green]✅ Set[/green] [cyan]{section}.{key}[/cyan] = [yellow]{args.value}[/yellow]")
        elif args.action == "all":
            console.print("\n[bold cyan]📋 Configuration:[/bold cyan]")
            for section, items in all_config().items():
                console.print(f"\n[bold yellow][{section}][/bold yellow]")
                for key, value in items.items():
                    console.print(f"  [cyan]{key}[/cyan] = [green]{value}[/green]")
            console.print()
    elif args.command == "analytics":
        options = {"mode": args.mode}
        if args.user:
            options["user"] = args.user
        if args.compare:
            options["compare"] = args.compare
        if args.equal:
            options["equal"] = args.equal
        if args.no_limit:
            options["no_limit"] = args.no_limit
        if args.from_date:
            options["from_date"] = args.from_date
        if args.to_date:
            options["to_date"] = args.to_date
        if args.approvers:
            options["approvers"] = args.approvers
        if args.pr_limit:
            options["pr_limit"] = args.pr_limit
        if args.ranking_limit:
            options["ranking_limit"] = args.ranking_limit
        if args.top_approvers:
            options["top_approvers"] = args.top_approvers
            
        if args.compare:
            from prs.core.analytics import show_pr_analytics_comparison
            show_pr_analytics_comparison(options)
        elif args.mode == "extended":
            show_pr_analytics_extended(options)
        elif args.mode == "table":
            from prs.core.analytics import show_pr_analytics_table
            show_pr_analytics_table(options)
        else:
            show_pr_analytics(options)
    elif args.command == "history":
        show_pr_history({"pr_id": args.pr_id})
    elif args.command == "build-history":
        options = {"limit": args.limit, "all": args.all}
        if args.users:
            options["users"] = args.users
        if args.chunk:
            options["chunk"] = True
        if args.start_year:
            options["start_year"] = args.start_year
        if args.end_year:
            options["end_year"] = args.end_year
        if args.max_chunks:
            options["max_chunks"] = args.max_chunks
        if args.incremental:
            options["incremental"] = True
        build_pr_history(options)
    elif args.command == "update-history":
        options = {}
        if args.users:
            options["users"] = args.users
        if args.limit:
            options["limit"] = args.limit
        if args.force:
            options["force"] = args.force
        update_pr_history(options)
    elif args.command == "clear-history":
        clear_pr_history({})
    elif args.command == "chunk-examples":
        show_chunk_examples()


if __name__ == "__main__":
    run_cli()
