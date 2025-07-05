from datetime import datetime, timedelta

from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.panel import Panel

from prs.cache.manager import PRCacheManager
from prs.cache.incremental_manager import IncrementalPRCacheManager
from prs.config import get
from prs.core.helpers import resolve_owner
from prs.utils.formatting import color_text


def show_pr_analytics_table(options: dict):
    """Show PR approvals in a table format with PRs as rows and approvers as columns."""
    # Get repository info
    username = get("git", "username")
    owner = resolve_owner()
    repo_name = get("git", "repo_name")
    target_user = options.get("user")
    filter_approvers = options.get("approvers")
    
    if not username or not owner or not repo_name:
        console = Console()
        console.print("[red]Error: Missing configuration. Please set git.username, git.repo_name, and git.origin/upstream[/red]")
        return
    
    # Initialize cache manager  
    cache_user = target_user if target_user else username
    
    # Try incremental cache manager first (used by chunk-based builds), fallback to regular
    try:
        cache_manager = IncrementalPRCacheManager(cache_user, owner, repo_name)
        if not cache_manager.history:
            # If incremental cache is empty, try regular cache manager
            cache_manager = PRCacheManager(cache_user, owner, repo_name)
    except:
        cache_manager = PRCacheManager(cache_user, owner, repo_name)
    
    # Check if cache exists
    if target_user and not cache_manager.history:
        console = Console()
        console.print(f"[yellow]No cache found for user '{target_user}'. Run 'nprs build-history --users=\"{target_user}\"' first.[/yellow]")
        return
    
    # Parse filter approvers if provided
    filter_list = []
    if filter_approvers:
        filter_list = [a.strip() for a in filter_approvers.split(",") if a.strip()]
    
    # Collect all PRs with approvals
    pr_approvals = []
    all_approvers = set()
    
    for pr_id, pr_data in cache_manager.history.items():
        # Only include merged PRs, exclude closed and draft PRs
        pr_state = pr_data.get('state', '').upper()
        pr_draft = pr_data.get('draft', False)
        
        if pr_state != 'MERGED' or pr_draft:
            continue
            
        reviews = pr_data.get('reviews', [])
        approvers = []
        
        for review in reviews:
            if review.get('state') == 'APPROVED':
                author = review.get('author', {})
                if isinstance(author, dict):
                    approver = author.get('login', 'unknown')
                else:
                    approver = str(author)
                
                # Exclude PR author and copilot from approver list
                pr_author = pr_data.get('author', '')
                if approver and approver != 'unknown' and approver != pr_author and approver != 'copilot-pull-request-reviewer':
                    approvers.append(approver)
                    all_approvers.add(approver)
        
        if approvers:  # Only include PRs that have approvals
            pr_approvals.append({
                'id': pr_data.get('id'),
                'title': pr_data.get('title', ''),
                'state': pr_data.get('state', 'UNKNOWN'),
                'approvers': list(set(approvers))  # Remove duplicates
            })
    
    # Sort PRs by ID (newest first)
    pr_approvals.sort(key=lambda x: x['id'], reverse=True)
    
    # Filter PRs if specific approvers are requested
    if filter_list:
        # Only show PRs that have at least one approval from the filtered approvers
        filtered_pr_approvals = []
        for pr in pr_approvals:
            if any(approver in pr['approvers'] for approver in filter_list):
                filtered_pr_approvals.append(pr)
        pr_approvals = filtered_pr_approvals
    
    # Apply PR limit if specified
    pr_limit = options.get("pr_limit")
    if pr_limit and pr_limit > 0:
        pr_approvals = pr_approvals[:pr_limit]
    
    # Filter approvers if requested
    if filter_list:
        approvers_list = [a for a in sorted(list(all_approvers)) if a in filter_list]
        if not approvers_list:
            console = Console()
            console.print(f"\\n[yellow]No approvals found from specified approvers: {', '.join(filter_list)}[/yellow]")
            return
    else:
        approvers_list = sorted(list(all_approvers))
    
    # Apply top_approvers limit to columns
    top_n = options.get('top_approvers', 3)
    
    # If not filtering by specific approvers, limit to top N by approval count
    if not filter_list and len(approvers_list) > top_n:
        # Count approvals per person
        approval_counts = {}
        for approver in approvers_list:
            count = sum(1 for pr in pr_approvals if approver in pr['approvers'])
            approval_counts[approver] = count
        
        # Sort by count and take top N
        sorted_approvers = sorted(approval_counts.items(), key=lambda x: x[1], reverse=True)
        approvers_list = [approver for approver, count in sorted_approvers[:top_n]]
    
    if not pr_approvals:
        console = Console()
        console.print(f"\\n[yellow]No PRs with approvals found for {cache_user}[/yellow]")
        return
    
    # Initialize Rich console
    console = Console()
    
    # Create Rich table with styling
    table_title = f"📊 PR Approval Matrix - {owner}/{repo_name} ({cache_user})"
    table_caption = f"{len(pr_approvals)} PRs with approvals, {len(approvers_list)} unique approvers"
    
    table = Table(
        show_header=True, 
        header_style="bold blue", 
        show_lines=True,
        title=table_title,
        title_style="bold cyan",
        caption=table_caption,
        caption_style="dim"
    )
    
    console.print()
    
    # Add PR column with wider width for titles and metrics
    table.add_column("PR # & Details", style="cyan", min_width=15, max_width=60)
    
    # Add timing column
    table.add_column("Timing", style="yellow", min_width=12, max_width=20)
    
    # Add approver columns
    for approver in approvers_list:
        # Truncate long usernames for column headers
        display_name = approver[:10] + "..." if len(approver) > 13 else approver
        table.add_column(display_name, justify="center", min_width=4, max_width=12)
    
    # Add rows
    for pr in pr_approvals:
        # Get the full PR data to access metrics
        pr_data = None
        for pr_id, data in cache_manager.history.items():
            if str(data.get('id')) == str(pr['id']):
                pr_data = data
                break
        
        # Prepare PR number with state color
        pr_num = f"#{pr['id']}"
        if pr['state'].lower() == 'merged':
            pr_display = f"[green]{pr_num}[/green]"
        elif pr['state'].lower() == 'open':
            pr_display = f"[yellow]{pr_num}[/yellow]"
        else:
            pr_display = f"[red]{pr_num}[/red]"
        
        # Add metrics line (additions, deletions, files changed) with fixed width
        if pr_data:
            additions = pr_data.get('additions', 0)
            deletions = pr_data.get('deletions', 0)
            changed_files = pr_data.get('changed_files', 0)
            
            # Format with fixed widths and colors
            # Each block gets exactly 10 characters, rest for files
            additions_text = f"+{additions}"
            deletions_text = f"-{deletions}"
            files_text = f"{changed_files} files"
            
            # Use padding to ensure exact 10-char blocks
            additions_padded = additions_text.ljust(10)
            deletions_padded = deletions_text.ljust(10)
            
            pr_display += f"    [green]{additions_padded}[/green][red]{deletions_padded}[/red][blue]{files_text}[/blue]"
        
        # Add title as subtitle (properly formatted for Rich)
        title = pr['title'][:65] + "..." if len(pr['title']) > 68 else pr['title']
        # Clean up any literal newlines in the title
        title = title.replace('\\n', ' ').replace('\\r', ' ')
        pr_display += f"\n[dim italic]{title}[/dim italic]"
        
        # Prepare timing information
        timing_info = ""
        if pr_data:
            created_at = pr_data.get('created_at', '')
            merged_at = pr_data.get('merged_at', '')
            closed_at = pr_data.get('closed_at', '')
            
            # Calculate time to first review
            reviews = pr_data.get('reviews', [])
            if reviews:
                # Find earliest review
                earliest_review = None
                for review in reviews:
                    submitted_at = review.get('submittedAt') or review.get('submitted_at', '')
                    if submitted_at:
                        if not earliest_review or submitted_at < earliest_review:
                            earliest_review = submitted_at
                
                if earliest_review and created_at:
                    try:
                        from datetime import datetime
                        created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        review_time = datetime.fromisoformat(earliest_review.replace('Z', '+00:00'))
                        time_diff = review_time - created_time
                        
                        if time_diff.days > 0:
                            timing_info += f"{time_diff.days}d → Reviews\n"
                        else:
                            hours = time_diff.seconds // 3600
                            timing_info += f"{hours}h → Reviews\n"
                    except:
                        timing_info += "? → Reviews\n"
            
            # Calculate time to merge/close
            end_time = merged_at or closed_at
            if end_time and created_at:
                try:
                    created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    end_time_parsed = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    time_diff = end_time_parsed - created_time
                    
                    if time_diff.days > 0:
                        action = "Merged" if merged_at else "Closed"
                        timing_info += f"{time_diff.days}d → {action}"
                    else:
                        hours = time_diff.seconds // 3600
                        action = "Merged" if merged_at else "Closed"
                        timing_info += f"{hours}h → {action}"
                except:
                    action = "Merged" if merged_at else "Closed"
                    timing_info += f"? → {action}"
        
        if not timing_info:
            timing_info = "[dim]No timing data[/dim]"
        
        # Prepare approval columns
        row_data = [pr_display, timing_info]
        for approver in approvers_list:
            if approver in pr['approvers']:
                row_data.append("[white on green]✅[/white on green]")
            else:
                row_data.append("")
        
        table.add_row(*row_data)
    
    # Display the table
    console.print(table)
    
    # Summary section
    console.print()
    console.print("📊 [yellow]Summary:[/yellow]")
    
    # Count approvals per person (only for displayed approvers)
    approval_counts = {}
    for approver in approvers_list:
        count = sum(1 for pr in pr_approvals if approver in pr['approvers'])
        approval_counts[approver] = count
    
    # Sort by count and print
    sorted_approvers = sorted(approval_counts.items(), key=lambda x: x[1], reverse=True)
    console.print(f"   Top {len(approvers_list)} Approvers:")
    for i, (approver, count) in enumerate(sorted_approvers):
        console.print(f"   {i+1}. [cyan]{approver}[/cyan]: {count} approvals")
    
    console.print()


def show_pr_analytics(options: dict):
    """Show analytics from cached PR data with different verbosity levels."""
    # Get repository info
    username = get("git", "username")
    owner = resolve_owner()
    repo_name = get("git", "repo_name")
    mode = options.get("mode", "normal")
    target_user = options.get("user")
    
    if not username or not owner or not repo_name:
        console = Console()
        console.print("[red]Error: Missing configuration. Please set git.username, git.repo_name, and git.origin/upstream[/red]")
        return
    
    # Initialize cache manager (use target_user if specified, otherwise current user)
    cache_user = target_user if target_user else username
    
    # Try incremental cache manager first (used by chunk-based builds), fallback to regular
    try:
        cache_manager = IncrementalPRCacheManager(cache_user, owner, repo_name)
        if not cache_manager.history:
            # If incremental cache is empty, try regular cache manager
            cache_manager = PRCacheManager(cache_user, owner, repo_name)
    except:
        cache_manager = PRCacheManager(cache_user, owner, repo_name)
    
    # Check if cache exists for target user
    if target_user and not cache_manager.history:
        console = Console()
        console.print(f"[yellow]No cache found for user '{target_user}'. Run 'nprs build-history --users=\"{target_user}\"' first.[/yellow]")
        return
    
    # Check for date filtering
    from_date = options.get("from_date")
    to_date = options.get("to_date")
    
    # Default to_date to today if not specified but from_date is
    if from_date and not to_date:
        from datetime import date
        to_date = date.today().strftime('%Y-%m-%d')
    
    # Apply date filtering if requested
    if from_date or to_date:
        try:
            from datetime import datetime
            date_filter = {}
            if from_date:
                date_filter["from"] = datetime.strptime(from_date, '%Y-%m-%d')
            if to_date:
                date_filter["to"] = datetime.strptime(to_date, '%Y-%m-%d')
            
            print(f"📅 Filtering PRs from {from_date or 'beginning'} to {to_date}")
            analytics = _compute_date_filtered_analytics(cache_manager, date_filter)
        except ValueError:
            print("Error: Invalid date format. Use YYYY-MM-DD (e.g., '2022-09-30')")
            return
    else:
        # Compute regular analytics
        analytics = cache_manager.compute_analytics()
    
    # Display analytics based on mode
    if mode == "short":
        _show_analytics_short(analytics, owner, repo_name, cache_user, options)
    elif mode == "long":
        _show_analytics_long(analytics, owner, repo_name, cache_user, options)
    else:  # normal
        _show_analytics_normal(analytics, owner, repo_name, cache_user, options)


def _show_analytics_short(analytics: dict, owner: str, repo_name: str, user: str = None, options: dict = None):
    """Show condensed analytics with Rich formatting."""
    console = Console()
    
    user_info = f" ({user})" if user else ""
    console.print()
    console.print(f"📊 [blue]{owner}/{repo_name}[/blue]{user_info} - [cyan bold]{analytics['total_prs']}[/cyan bold] PRs")
    
    # States in a compact format
    states = []
    for state, count in analytics['prs_by_state'].items():
        if state.upper() == 'MERGED':
            states.append(f"[green]{state}: {count}[/green]")
        elif state.upper() == 'OPEN':
            states.append(f"[yellow]{state}: {count}[/yellow]")  
        elif state.upper() == 'CLOSED':
            states.append(f"[red]{state}: {count}[/red]")
        else:
            states.append(f"{state}: {count}")
    
    if states:
        console.print(f"📋 {' | '.join(states)}")
    
    # Key metrics
    if analytics.get('avg_review_time'):
        hours = analytics['avg_review_time']
        time_str = f"{hours/24:.1f}d" if hours > 24 else f"{hours:.1f}h"
        console.print(f"⏱️  Review time: [cyan]{time_str}[/cyan]")
    
    # Top approver (prioritize approvers over general reviewers)
    if analytics.get('top_approvers'):
        top_approver, count = next(iter(analytics['top_approvers'].items()))
        console.print(f"👑 Top approver: [yellow]{top_approver}[/yellow] ({count})")
    elif analytics.get('top_reviewers'):
        top_reviewer, count = next(iter(analytics['top_reviewers'].items()))
        console.print(f"👑 Top reviewer: [yellow]{top_reviewer}[/yellow] ({count})")
    
    console.print()


def _show_analytics_normal(analytics: dict, owner: str, repo_name: str, user: str = None, options: dict = None):
    """Show standard analytics with Rich formatting."""
    console = Console()
    
    if options is None:
        options = {}
    
    user_info = f" ({user})" if user else ""
    
    # Header with Rich
    console.print()
    console.print(f"📊 [cyan]PR Analytics[/cyan] for [blue]{owner}/{repo_name}[/blue]{user_info}")
    console.print(f"📅 Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    console.print()
    
    # Summary with Rich table
    summary_table = Table(show_header=False, box=None, padding=(0, 1))
    summary_table.add_column("Metric", style="yellow")
    summary_table.add_column("Value", style="cyan bold")
    
    summary_table.add_row("📈 Total PRs", str(analytics['total_prs']))
    
    # Add velocity metrics if available
    if analytics.get('pr_velocity'):
        velocity = analytics['pr_velocity']
        if velocity.get('monthly'):
            summary_table.add_row("📊 Monthly Velocity", f"{velocity['monthly']:.1f} PRs/month")
        if velocity.get('weekly'):
            summary_table.add_row("📊 Weekly Velocity", f"{velocity['weekly']:.1f} PRs/week")
    
    # Add average metrics
    if analytics.get('avg_pr_lifetime'):
        lifetime_days = analytics['avg_pr_lifetime'] / 24
        summary_table.add_row("⏳ Avg PR Lifetime", f"{lifetime_days:.1f} days")
    
    if analytics.get('avg_commits_per_pr'):
        summary_table.add_row("📝 Avg Commits/PR", f"{analytics['avg_commits_per_pr']:.1f}")
    
    console.print(summary_table)
    console.print()
    
    
    # Timing metrics with Rich
    _show_timing_metrics_rich(analytics, console)
    
    # Size metrics with Rich
    _show_size_metrics_rich(analytics, console)
    
    # Top contributors with Rich
    ranking_limit = options.get('ranking_limit', options.get('top_approvers', 3))
    _show_top_rankings_rich(analytics, console, limit=ranking_limit)
    
    console.print()


def _show_timing_metrics_rich(analytics: dict, console: Console):
    """Show timing metrics with Rich formatting."""
    timing_table = Table(title="⏱️ Timing Metrics", show_header=True, header_style="bold blue")
    timing_table.add_column("Metric", style="yellow")
    timing_table.add_column("Value", justify="right", style="cyan")
    
    if analytics.get('avg_review_time'):
        hours = analytics['avg_review_time']
        if hours > 24:
            timing_table.add_row("Time to first review", f"{hours/24:.1f} days")
        elif hours > 1:
            timing_table.add_row("Time to first review", f"{hours:.1f} hours")
        else:
            minutes = hours * 60
            timing_table.add_row("Time to first review", f"{minutes:.0f} minutes")
    else:
        timing_table.add_row("Time to first review", "[dim]N/A[/dim]")
    
    if analytics.get('avg_checks_time'):
        hours = analytics['avg_checks_time']
        if hours > 24:
            timing_table.add_row("Time for checks to pass", f"{hours/24:.1f} days")
        elif hours > 1:
            timing_table.add_row("Time for checks to pass", f"{hours:.1f} hours")
        else:
            minutes = hours * 60
            timing_table.add_row("Time for checks to pass", f"{minutes:.0f} minutes")
    else:
        timing_table.add_row("Time for checks to pass", "[dim]N/A[/dim]")
    
    console.print(timing_table)
    console.print()


def _show_size_metrics_rich(analytics: dict, console: Console):
    """Show size metrics with Rich formatting."""
    size_table = Table(title="📏 PR Size Metrics", show_header=True, header_style="bold blue")
    size_table.add_column("Metric", style="yellow")
    size_table.add_column("Value", justify="right", style="cyan")
    
    if analytics.get('avg_pr_size'):
        size = analytics['avg_pr_size']
        if 'additions' in size and 'deletions' in size:
            size_table.add_row("Avg Additions", f"[green]+{size['additions']:.0f}[/green]")
            size_table.add_row("Avg Deletions", f"[red]-{size['deletions']:.0f}[/red]")
            size_table.add_row("Avg Files Changed", f"[blue]{size.get('files', 0):.0f}[/blue]")
        else:
            # Handle legacy format
            size_table.add_row("Avg PR Size", f"{size:.0f} lines")
    
    # Size distribution if available
    if analytics.get('size_distribution'):
        dist = analytics['size_distribution']
        console.print(size_table)
        console.print()
        
        # Size distribution chart
        dist_table = Table(title="📊 Size Distribution", show_header=True, header_style="bold blue")
        dist_table.add_column("Size Category", style="white")
        dist_table.add_column("Count", justify="right", style="cyan")
        dist_table.add_column("Description", style="dim")
        
        categories = [
            ("Small", dist.get('small', 0), "< 100 lines"),
            ("Medium", dist.get('medium', 0), "100-500 lines"),
            ("Large", dist.get('large', 0), "500-1000 lines"),
            ("Huge", dist.get('huge', 0), "> 1000 lines")
        ]
        
        for category, count, desc in categories:
            if count > 0:
                dist_table.add_row(category, str(count), desc)
        
        console.print(dist_table)
    else:
        console.print(size_table)
    
    console.print()


def _show_top_rankings_rich(analytics: dict, console: Console, limit: int = 3):
    """Show top rankings with Rich formatting."""
    rankings_data = [
        ("✅ Top Approvers", analytics.get('top_approvers', {}), "green"),
        ("👥 Top Reviewers", analytics.get('top_reviewers', {}), "blue"),
        ("📝 Most Requested", analytics.get('top_requested_reviewers', {}), "yellow"),
        ("💬 Active Commenters", analytics.get('top_commenters', {}), "magenta")
    ]
    
    contributors_table = Table(title=f"🏆 Top {limit} Contributors", show_header=True, header_style="bold blue")
    contributors_table.add_column("Category", style="white")
    contributors_table.add_column("Top Contributors", style="cyan")
    
    for title, ranking, color in rankings_data:
        if ranking:
            top_contributors = list(ranking.items())[:limit]
            contributors_str = ", ".join([f"[{color}]{user}[/{color}] ({count})" for user, count in top_contributors])
            contributors_table.add_row(title, contributors_str)
    
    if contributors_table.row_count > 0:
        console.print(contributors_table)
        console.print()


def _show_analytics_long(analytics: dict, owner: str, repo_name: str, user: str = None, options: dict = None):
    """Show comprehensive analytics with Rich formatting."""
    console = Console()
    
    if options is None:
        options = {}
    
    user_info = f" ({user})" if user else ""
    
    # Header with Rich
    console.print()
    console.print(f"📊 [cyan]Comprehensive PR Analytics[/cyan] for [blue]{owner}/{repo_name}[/blue]{user_info}")
    console.print(f"📅 Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    console.print()
    
    # Comprehensive summary with Rich table
    summary_table = Table(title="📈 Comprehensive Summary", show_header=True, header_style="bold blue")
    summary_table.add_column("Metric", style="yellow")
    summary_table.add_column("Value", justify="right", style="cyan bold")
    summary_table.add_column("Additional Info", style="dim")
    
    summary_table.add_row("Total PRs", str(analytics['total_prs']), "All tracked pull requests")
    
    if analytics.get('avg_commits_per_pr'):
        summary_table.add_row("Avg Commits/PR", f"{analytics['avg_commits_per_pr']:.1f}", "Code change frequency")
    
    if analytics.get('avg_pr_lifetime'):
        lifetime_days = analytics['avg_pr_lifetime'] / 24
        summary_table.add_row("Avg PR Lifetime", f"{lifetime_days:.1f} days", "Time from open to close")
    
    if analytics.get('pr_velocity'):
        velocity = analytics['pr_velocity']
        if velocity.get('monthly'):
            summary_table.add_row("Monthly Velocity", f"{velocity['monthly']:.1f} PRs", "PRs created per month")
        if velocity.get('weekly'):
            summary_table.add_row("Weekly Velocity", f"{velocity['weekly']:.1f} PRs", "PRs created per week")
    
    console.print(summary_table)
    console.print()
    
    
    # Enhanced timing metrics
    _show_timing_metrics_rich(analytics, console)
    
    # Enhanced size metrics with distribution
    _show_size_metrics_rich(analytics, console)
    
    # Review patterns with Rich
    if analytics.get('review_patterns'):
        patterns_table = Table(title="🔄 Review Patterns", show_header=True, header_style="bold blue")
        patterns_table.add_column("Pattern", style="yellow")
        patterns_table.add_column("Count", justify="right", style="cyan")
        patterns_table.add_column("Percentage", justify="right", style="green")
        patterns_table.add_column("Description", style="dim")
        
        patterns = analytics['review_patterns']
        total_prs = analytics.get('total_prs', 1)  # Avoid division by zero
        
        if patterns.get('same_day_reviews'):
            count = patterns['same_day_reviews']
            percentage = (count / total_prs) * 100 if total_prs > 0 else 0
            patterns_table.add_row("Same-day reviews", str(count), f"{percentage:.1f}%", "Reviews within 24 hours")
        if patterns.get('quick_approvals'):
            count = patterns['quick_approvals']
            percentage = (count / total_prs) * 100 if total_prs > 0 else 0
            patterns_table.add_row("Quick approvals", str(count), f"{percentage:.1f}%", "Approved within 1 hour")
        if patterns.get('weekend_reviews'):
            count = patterns['weekend_reviews']
            percentage = (count / total_prs) * 100 if total_prs > 0 else 0
            patterns_table.add_row("Weekend reviews", str(count), f"{percentage:.1f}%", "Reviews on weekends")
        
        if patterns_table.row_count > 0:
            console.print(patterns_table)
            console.print()
    
    # Enhanced complete rankings
    ranking_limit = options.get('ranking_limit', options.get('top_approvers', 7))
    _show_complete_rankings_rich(analytics, console, ranking_limit)
    
    # Activity patterns
    if analytics.get('busiest_days'):
        activity_table = Table(title="📅 Busiest Days", show_header=True, header_style="bold blue")
        activity_table.add_column("Date", style="blue")
        activity_table.add_column("PRs Created", justify="right", style="cyan")
        
        for day, count in list(analytics['busiest_days'].items())[:10]:
            activity_table.add_row(day, str(count))
        
        console.print(activity_table)
        console.print()
    
    # Labels usage
    if analytics.get('most_active_labels'):
        labels_table = Table(title="🏷️ Most Used Labels", show_header=True, header_style="bold blue")
        labels_table.add_column("Label", style="magenta")
        labels_table.add_column("Usage Count", justify="right", style="cyan")
        
        for label, count in list(analytics['most_active_labels'].items())[:10]:
            labels_table.add_row(label, str(count))
        
        console.print(labels_table)
        console.print()
    
    console.print()


def _show_complete_rankings_rich(analytics: dict, console: Console, limit: int = 7):
    """Show complete rankings with Rich formatting."""
    rankings_data = [
        ("✅ Top Approvers", analytics.get('top_approvers', {}), "green"),
        ("👥 Top Reviewers", analytics.get('top_reviewers', {}), "blue"),
        ("📝 Most Requested", analytics.get('top_requested_reviewers', {}), "yellow"),
        ("💬 Active Commenters", analytics.get('top_commenters', {}), "magenta")
    ]
    
    for title, ranking, color in rankings_data:
        if ranking:
            rank_table = Table(title=title, show_header=True, header_style="bold blue")
            rank_table.add_column("Rank", style="white", justify="center", width=4)
            rank_table.add_column("User", style=color)
            rank_table.add_column("Count", justify="right", style="cyan")
            
            medals = ["🥇", "🥈", "🥉"]
            # Row color pattern: bright-green, cyan, yellow, white, and neutral colors below
            row_styles = ["bright_green", "cyan", "yellow", "white", "dim", "grey58", "grey42"]
            
            # Use the provided limit parameter
            display_limit = max(7, limit) if title in ["✅ Top Approvers", "👥 Top Reviewers"] else min(limit, 10)
            for i, (user, count) in enumerate(list(ranking.items())[:display_limit]):
                rank_display = medals[i] if i < 3 else f"{i+1}."
                row_style = row_styles[min(i, len(row_styles)-1)]
                rank_table.add_row(rank_display, user, str(count), style=row_style)
            
            console.print(rank_table)
            console.print()


def _show_timing_metrics(analytics: dict):
    """Show timing-related metrics."""
    if analytics.get('avg_review_time'):
        hours = analytics['avg_review_time']
        if hours > 24:
            print(f"   • Time to first review: {color_text(f'{hours/24:.1f} days', 'cyan')}")
        elif hours > 1:
            print(f"   • Time to first review: {color_text(f'{hours:.1f} hours', 'cyan')}")
        else:
            minutes = hours * 60
            print(f"   • Time to first review: {color_text(f'{minutes:.0f} minutes', 'cyan')}")
    else:
        print(f"   • Time to first review: {color_text('N/A', 'gray-3')}")
    
    if analytics.get('avg_checks_time'):
        hours = analytics['avg_checks_time']
        if hours > 24:
            print(f"   • Time for checks to pass: {color_text(f'{hours/24:.1f} days', 'cyan')}")
        elif hours > 1:
            print(f"   • Time for checks to pass: {color_text(f'{hours:.1f} hours', 'cyan')}")
        else:
            minutes = hours * 60
            print(f"   • Time for checks to pass: {color_text(f'{minutes:.0f} minutes', 'cyan')}")
    else:
        print(f"   • Time for checks to pass: {color_text('N/A', 'gray-3')}")
    
    # Always show PR lifetime if available
    if analytics.get('avg_pr_lifetime'):
        hours = analytics['avg_pr_lifetime']
        if hours > 24:
            print(f"   • Average PR lifetime: {color_text(f'{hours/24:.1f} days', 'cyan')}")
        else:
            print(f"   • Average PR lifetime: {color_text(f'{hours:.1f} hours', 'cyan')}")


def _show_size_metrics(analytics: dict):
    """Show size-related metrics."""
    avg_size = analytics.get('avg_pr_size', {})
    if avg_size.get('additions', 0) > 0 or avg_size.get('deletions', 0) > 0:
        additions = avg_size["additions"]
        deletions = avg_size["deletions"]
        files = avg_size["files"]
        print(f"\n📏 {color_text('Average PR Size:', 'yellow')}")
        print(f"   • Additions: {color_text(f'+{additions:.0f}', 'green')}")
        print(f"   • Deletions: {color_text(f'-{deletions:.0f}', 'red')}")
        print(f"   • Files changed: {color_text(f'{files:.0f}', 'blue')}")


def _show_size_distribution(analytics: dict):
    """Show PR size distribution."""
    dist = analytics.get('size_distribution', {})
    if any(dist.values()):
        print(f"   • Size distribution:")
        if dist.get('small'): print(f"     - Small (<100 lines): {color_text(str(dist['small']), 'green')}")
        if dist.get('medium'): print(f"     - Medium (100-500): {color_text(str(dist['medium']), 'yellow')}")
        if dist.get('large'): print(f"     - Large (500-1000): {color_text(str(dist['large']), 'red')}")
        if dist.get('huge'): print(f"     - Huge (>1000): {color_text(str(dist['huge']), 'magenta')}")


def _show_top_rankings(analytics: dict, limit: int = 3):
    """Show top N rankings, prioritizing approvers. Always show at least 7 for approvers and reviewers."""
    rankings = [
        ("✅ Top Approvers", analytics.get('top_approvers', {})),
        ("📝 Most Requested", analytics.get('top_requested_reviewers', {})),
        ("💬 Active Commenters", analytics.get('top_commenters', {}))
    ]
    
    for title, ranking in rankings:
        if ranking:
            print(f"   {title}:")
            for user, count in list(ranking.items())[:limit]:
                print(f"      • {color_text(user, 'cyan')}: {count}")


def _show_all_rankings(analytics: dict):
    """Show complete rankings with colored rows."""
    rankings = [
        ("👥 Top Reviewers (All Reviews)", analytics.get('top_reviewers', {})),
        ("📝 Most Requested Reviewers", analytics.get('top_requested_reviewers', {})),
        ("✅ Top Approvers", analytics.get('top_approvers', {})),
        ("💬 Most Active Commenters", analytics.get('top_commenters', {}))
    ]
    
    # Row color pattern: bright-green, cyan, yellow, white, and neutral colors below
    row_colors = ['bright_green', 'cyan', 'yellow', 'white', 'gray-3', 'gray-2', 'gray-1']
    
    for title, ranking in rankings:
        if ranking:
            print(f"\n   {color_text(title, 'white')}:")
            for i, (user, count) in enumerate(ranking.items(), 1):
                color = row_colors[min(i-1, len(row_colors)-1)]
                if i <= 3:
                    medals = ["🥇", "🥈", "🥉"]
                    print(f"      {medals[i-1]} {color_text(user, color)}: {count}")
                else:
                    print(f"      {i:2d}. {color_text(user, color)}: {count}")
                if i >= 10:  # Limit to top 10
                    break


def show_pr_history(options: dict):
    """Show PR history with detailed events."""
    pr_id = options.get('pr_id')
    if not pr_id:
        print("Error: Please specify a PR ID with --pr-id")
        return
    
    # Get repository info
    username = get("git", "username")
    owner = resolve_owner()
    repo_name = get("git", "repo_name")
    
    if not username or not owner or not repo_name:
        print("Error: Missing configuration")
        return
    
    # Initialize cache manager
    cache_manager = PRCacheManager(username, owner, repo_name)
    
    # Get PR history
    pr_history = cache_manager.get_pr_history(pr_id)
    if not pr_history:
        print(f"No history found for PR #{pr_id}")
        return
    
    # Display PR info
    print(f"\n📜 {color_text(f'History for PR #{pr_id}', 'cyan')}")
    print(f"📝 Title: {pr_history['title']}")
    print(f"👤 Author: {color_text(pr_history['author'], 'yellow')}")
    print(f"📅 Created: {pr_history['created_at']}")
    print(f"👁️  First seen: {pr_history['first_seen']}")
    
    # Display size metrics
    size = pr_history['metrics']['size']
    additions = size["additions"]
    deletions = size["deletions"]
    files = size["changed_files"]
    print(f"\n📏 Size: {color_text(f'+{additions}', 'green')} / {color_text(f'-{deletions}', 'red')} ({files} files)")
    
    # Display events timeline
    events = pr_history.get('events', [])
    if events:
        print(f"\n📅 {color_text('Event Timeline:', 'yellow')}")
        for event in events:
            timestamp = datetime.fromisoformat(event['timestamp']).strftime('%Y-%m-%d %H:%M')
            event_type = event['type']
            
            if event_type == 'state_change':
                print(f"   • {timestamp}: State changed to {color_text(event['value'], 'cyan')}")
            elif event_type == 'reviewers_added':
                added = event.get('added', [])
                print(f"   • {timestamp}: Reviewers added: {', '.join(color_text(r, 'yellow') for r in added)}")
            elif event_type == 'review':
                author = event.get('author', 'Unknown')
                state = event.get('state', 'UNKNOWN')
                state_color = {
                    'APPROVED': 'green',
                    'CHANGES_REQUESTED': 'red',
                    'COMMENTED': 'yellow'
                }.get(state, 'white')
                print(f"   • {timestamp}: {color_text(author, 'yellow')} {color_text(state, state_color)}")
            elif event_type == 'checks_status':
                status = event.get('value', 'unknown')
                status_color = {
                    'success': 'green',
                    'failure': 'red',
                    'pending': 'yellow'
                }.get(status, 'white')
                print(f"   • {timestamp}: Checks {color_text(status, status_color)}")
            elif event_type == 'checks_passed':
                print(f"   • {timestamp}: {color_text('✓ All checks passed', 'green')}")
            elif event_type == 'commit_count':
                change = event.get('change', 0)
                new_count = event.get('value', 0)
                if change > 0:
                    print(f"   • {timestamp}: {color_text(f'+{change} commits', 'cyan')} (total: {new_count})")
                else:
                    print(f"   • {timestamp}: {color_text(f'{change} commits', 'red')} (total: {new_count})")
            elif event_type == 'labels_changed':
                added = event.get('added', [])
                removed = event.get('removed', [])
                if added:
                    print(f"   • {timestamp}: Labels added: {', '.join(color_text(l, 'magenta') for l in added)}")
                if removed:
                    print(f"   • {timestamp}: Labels removed: {', '.join(color_text(l, 'gray-3') for l in removed)}")
    
    print()  # Empty line at end


def show_pr_analytics_extended(options: dict):
    """Show extended per-PR analytics for debugging and verification."""
    # Get repository info
    username = get("git", "username")
    owner = resolve_owner()
    repo_name = get("git", "repo_name")
    target_user = options.get("user")
    
    if not username or not owner or not repo_name:
        console = Console()
        console.print("[red]Error: Missing configuration. Please set git.username, git.repo_name, and git.origin/upstream[/red]")
        return
    
    # Initialize cache manager (use target_user if specified, otherwise current user)
    cache_user = target_user if target_user else username
    cache_manager = PRCacheManager(cache_user, owner, repo_name)
    
    # Check if cache exists for target user
    if target_user and not cache_manager.history:
        console = Console()
        console.print(f"[yellow]No cache found for user '{target_user}'. Run 'nprs build-history --users=\"{target_user}\"' first.[/yellow]")
        return
    
    user_info = f" ({color_text(cache_user, 'yellow')})" if target_user else ""
    print(f"\\n📊 {color_text('Extended PR Analytics', 'cyan')} for {color_text(f'{owner}/{repo_name}', 'blue')}{user_info}")
    print(f"📅 Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")
    
    # Sort PRs by creation date
    pr_list = []
    for pr_id, pr_data in cache_manager.history.items():
        created_at = pr_data.get('created_at')
        if created_at:
            pr_list.append((pr_id, pr_data, created_at))
    
    # Sort by creation date (newest first)
    pr_list.sort(key=lambda x: x[2], reverse=True)
    
    print(f"📋 {color_text('Per-PR Details:', 'yellow')} (ordered by creation date)\\n")
    
    for i, (pr_id, pr_data, created_at) in enumerate(pr_list):
        events = pr_data.get('events', [])
        
        # Get current state
        current_state = cache_manager._get_last_event_value(events, 'state_change') or 'unknown'
        
        # Count events
        review_events = [e for e in events if e.get('type') == 'review']
        approval_events = [e for e in events if e.get('type') == 'review' and e.get('state') == 'APPROVED']
        reviewer_request_events = [e for e in events if e.get('type') == 'reviewers_added']
        
        # Get unique reviewers and approvers
        reviewers = list(set([e.get('author') for e in review_events if e.get('author')]))
        approvers = list(set([e.get('author') for e in approval_events if e.get('author')]))
        
        # Get requested reviewers (from latest event)
        requested_reviewers = []
        for event in reversed(reviewer_request_events):
            if event.get('value'):
                requested_reviewers = event.get('value', [])
                break
        
        # Show PR info
        state_color = {'OPEN': 'green', 'CLOSED': 'red', 'MERGED': 'magenta', 'unknown': 'white'}.get(current_state, 'white')
        print(f"{i+1:2d}. PR #{color_text(pr_id, 'blue')} - {color_text(current_state, state_color)}")
        print(f"     📅 Created: {created_at}")
        print(f"     📝 Title: {pr_data.get('title', 'Unknown')[:60]}...")
        print(f"     👤 Author: {color_text(pr_data.get('author', 'Unknown'), 'yellow')}")
        print(f"     📊 Events: {len(events)} total, {len(review_events)} reviews, {len(approval_events)} approvals, {len(reviewer_request_events)} reviewer requests")
        
        if reviewers:
            print(f"     👥 Reviewers: {', '.join(reviewers[:5])}{'...' if len(reviewers) > 5 else ''}")
        if approvers:
            print(f"     ✅ Approvers: {', '.join(approvers)}")
        if requested_reviewers:
            print(f"     📝 Requested: {', '.join(requested_reviewers[:5])}{'...' if len(requested_reviewers) > 5 else ''}")
            
        # Show individual review events for verification
        if review_events:
            print(f"     🔍 Review details:")
            for event in review_events:
                author = event.get('author', 'Unknown')
                state = event.get('state', 'Unknown')
                timestamp = event.get('timestamp', 'Unknown')
                print(f"        • {author}: {state} at {timestamp}")
        
        print()  # Empty line between PRs
        
        # Limit output to prevent overwhelming display
        if i >= 9:  # Show first 10 PRs
            remaining = len(pr_list) - 10
            if remaining > 0:
                print(f"     ... and {remaining} more PRs\\n")
            break


def show_pr_analytics_comparison(options: dict):
    """Show side-by-side comparison of analytics for multiple users."""
    console = Console()
    
    # Parse user list
    user_list_str = options.get("compare", "")
    if not user_list_str:
        console.print("[red]Error: No users specified for comparison. Use --compare 'user1,user2,user3'[/red]")
        return
    
    users = [u.strip() for u in user_list_str.split(",") if u.strip()]
    if len(users) < 2:
        console.print("[red]Error: At least 2 users required for comparison[/red]")
        return
    
    # Check user limit (default 6, unless --no-limit is used)
    no_limit = options.get("no_limit", False)
    if len(users) > 6 and not no_limit:
        console.print("[yellow]Warning: Limiting to first 6 users for better display. Use --no-limit to compare more users.[/yellow]")
        users = users[:6]
    elif len(users) > 6:
        console.print(f"[yellow]Comparing {len(users)} users (--no-limit enabled)[/yellow]")
    
    # Get repository info
    username = get("git", "username")
    owner = resolve_owner()
    repo_name = get("git", "repo_name")
    
    if not username or not owner or not repo_name:
        console.print("[red]Error: Missing configuration. Please set git.username, git.repo_name, and git.origin/upstream[/red]")
        return
    
    # Parse date range if provided
    from_date = options.get("from_date")
    to_date = options.get("to_date")
    
    # Default to_date to today if not specified
    if to_date is None:
        from datetime import date
        to_date = date.today().strftime('%Y-%m-%d')
    
    # Validate date formats
    date_filter = None
    if from_date or to_date:
        try:
            from datetime import datetime
            if from_date:
                from_dt = datetime.strptime(from_date, '%Y-%m-%d')
            else:
                from_dt = None
            if to_date:
                to_dt = datetime.strptime(to_date, '%Y-%m-%d')
            else:
                to_dt = None
            
            date_filter = {"from": from_dt, "to": to_dt}
            console.print(f"📅 Filtering PRs from {from_date or 'beginning'} to {to_date}")
        except ValueError as e:
            console.print(f"[red]Error: Invalid date format. Use YYYY-MM-DD (e.g., '2022-09-30')[/red]")
            return
    
    # Load analytics for each user
    user_cache_managers = {}
    user_pr_counts = {}
    use_equal = options.get("equal", False)
    
    console.print(f"\n🔄 Loading analytics for {len(users)} users...")
    
    # First pass: load cache managers and count PRs
    for user in users:
        try:
            # Try incremental cache manager first, fallback to regular
            try:
                cache_manager = IncrementalPRCacheManager(user, owner, repo_name)
                if not cache_manager.history:
                    cache_manager = PRCacheManager(user, owner, repo_name)
            except:
                cache_manager = PRCacheManager(user, owner, repo_name)
            
            if not cache_manager.history:
                console.print(f"[yellow]Warning: No cache found for user '{user}'. Run 'nprs build-history --users=\"{user}\"' first.[/yellow]")
                continue
            
            # Count merged PRs for this user
            merged_count = 0
            for pr_id, pr_data in cache_manager.history.items():
                state = pr_data.get('state', 'UNKNOWN').upper()
                if hasattr(cache_manager, '_is_stale_conflict_pr'):
                    # Check if it's PRCacheManager (needs events) or IncrementalPRCacheManager (doesn't need events)
                    if cache_manager.__class__.__name__ == 'PRCacheManager':
                        events = pr_data.get('events', [])
                        if cache_manager._is_stale_conflict_pr(pr_data, events):
                            continue
                    else:
                        if cache_manager._is_stale_conflict_pr(pr_data):
                            continue
                if state == 'MERGED' and not pr_data.get('draft', False) and not pr_data.get('is_draft', False):
                    merged_count += 1
            
            user_cache_managers[user] = cache_manager
            user_pr_counts[user] = merged_count
            console.print(f"✅ Loaded data for {user}: {merged_count} merged PRs")
            
        except Exception as e:
            console.print(f"[red]Error loading data for {user}: {str(e)}[/red]")
            continue
    
    if len(user_cache_managers) < 2:
        console.print("[red]Error: Need at least 2 users with valid data for comparison[/red]")
        return
    
    # Determine comparison method
    min_pr_count = None
    if date_filter:
        console.print(f"\n[yellow]Using date-based comparison: PRs created between {from_date or 'beginning'} and {to_date}[/yellow]")
    elif use_equal:
        min_pr_count = min(user_pr_counts.values())
        console.print(f"\n[yellow]Using equal comparison with {min_pr_count} most recent PRs per user[/yellow]")
    
    # Second pass: compute analytics (date-filtered, limited if --equal, or regular)
    user_analytics = {}
    for user, cache_manager in user_cache_managers.items():
        if date_filter:
            # Date-based filtering takes priority
            analytics = _compute_date_filtered_analytics(cache_manager, date_filter)
        elif use_equal and min_pr_count:
            # Create a limited analytics computation
            analytics = _compute_limited_analytics(cache_manager, min_pr_count)
        else:
            # Regular full analytics
            analytics = cache_manager.compute_analytics()
        
        user_analytics[user] = analytics
    
    console.print()
    
    # Display comparison header
    title_suffix = f" (Equal sample: {min_pr_count} PRs)" if use_equal and min_pr_count else ""
    console.print(f"📊 [cyan bold]Analytics Comparison[/cyan bold] - {owner}/{repo_name}{title_suffix}")
    console.print(f"📅 Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    console.print()
    
    # Create summary comparison table
    _show_comparison_summary(user_analytics, console)
    
    # Create timing comparison table
    _show_comparison_timing(user_analytics, console)
    
    # Create size comparison table
    _show_comparison_size(user_analytics, console)
    
    # Create rankings comparison
    ranking_limit = options.get("ranking_limit", options.get("top_approvers", 3))
    _show_comparison_rankings(user_analytics, console, ranking_limit)
    
    # Create activity patterns comparison
    _show_comparison_patterns(user_analytics, console)


def _show_comparison_summary(user_analytics: dict, console: Console):
    """Show summary metrics comparison table."""
    table = Table(title="📈 Summary Comparison", show_header=True, header_style="bold blue")
    table.add_column("Metric", style="yellow", min_width=15)
    
    # Add user columns
    for user in user_analytics.keys():
        display_name = user[:12] + "..." if len(user) > 15 else user
        table.add_column(display_name, justify="right", style="cyan")
    
    metrics = [
        ("Total PRs", "total_prs", lambda x: str(x)),
        ("Monthly Velocity", "pr_velocity.monthly", lambda x: f"{x:.1f}" if x else "N/A"),
        ("Weekly Velocity", "pr_velocity.weekly", lambda x: f"{x:.1f}" if x else "N/A"),
        ("Avg PR Lifetime", "avg_pr_lifetime", lambda x: f"{x/24:.1f}d" if x else "N/A"),
        ("Avg Commits/PR", "avg_commits_per_pr", lambda x: f"{x:.1f}" if x else "N/A")
    ]
    
    for metric_name, key_path, formatter in metrics:
        row = [metric_name]
        for user, analytics in user_analytics.items():
            value = _get_nested_value(analytics, key_path)
            row.append(formatter(value) if value is not None else "N/A")
        table.add_row(*row)
    
    console.print(table)
    console.print()


def _show_comparison_timing(user_analytics: dict, console: Console):
    """Show timing metrics comparison table."""
    table = Table(title="⏱️ Timing Comparison", show_header=True, header_style="bold blue")
    table.add_column("Metric", style="yellow", min_width=20)
    
    for user in user_analytics.keys():
        display_name = user[:12] + "..." if len(user) > 15 else user
        table.add_column(display_name, justify="right", style="cyan")
    
    timing_metrics = [
        ("Time to first review", "avg_review_time", lambda x: f"{x/24:.1f}d" if x and x > 24 else f"{x:.1f}h" if x else "N/A"),
        ("Time for checks to pass", "avg_checks_time", lambda x: f"{x/24:.1f}d" if x and x > 24 else f"{x:.1f}h" if x else "N/A")
    ]
    
    for metric_name, key, formatter in timing_metrics:
        row = [metric_name]
        for user, analytics in user_analytics.items():
            value = analytics.get(key)
            row.append(formatter(value))
        table.add_row(*row)
    
    console.print(table)
    console.print()


def _show_comparison_size(user_analytics: dict, console: Console):
    """Show size metrics comparison table."""
    table = Table(title="📏 Size Metrics Comparison", show_header=True, header_style="bold blue")
    table.add_column("Metric", style="yellow", min_width=15)
    
    for user in user_analytics.keys():
        display_name = user[:12] + "..." if len(user) > 15 else user
        table.add_column(display_name, justify="right", style="cyan")
    
    size_metrics = [
        ("Avg Additions", "avg_pr_size.additions", lambda x: f"[green]+{x:.0f}[/green]" if x else "N/A"),
        ("Avg Deletions", "avg_pr_size.deletions", lambda x: f"[red]-{x:.0f}[/red]" if x else "N/A"),
        ("Avg Files Changed", "avg_pr_size.files", lambda x: f"{x:.0f}" if x else "N/A")
    ]
    
    for metric_name, key_path, formatter in size_metrics:
        row = [metric_name]
        for user, analytics in user_analytics.items():
            value = _get_nested_value(analytics, key_path)
            row.append(formatter(value) if value is not None else "N/A")
        table.add_row(*row)
    
    console.print(table)
    console.print()
    
    # Size distribution comparison
    dist_table = Table(title="📊 Size Distribution Comparison", show_header=True, header_style="bold blue")
    dist_table.add_column("Size Category", style="yellow")
    
    for user in user_analytics.keys():
        display_name = user[:12] + "..." if len(user) > 15 else user
        dist_table.add_column(display_name, justify="right", style="cyan")
    
    categories = [
        ("Small (<100 lines)", "small"),
        ("Medium (100-500)", "medium"), 
        ("Large (500-1000)", "large"),
        ("Huge (>1000)", "huge")
    ]
    
    for category_name, key in categories:
        row = [category_name]
        for user, analytics in user_analytics.items():
            dist = analytics.get('size_distribution', {})
            count = dist.get(key, 0)
            total = analytics.get('total_prs', 1)
            percentage = (count / total) * 100 if total > 0 else 0
            row.append(f"{count} ({percentage:.1f}%)")
        dist_table.add_row(*row)
    
    console.print(dist_table)
    console.print()


def _show_comparison_rankings(user_analytics: dict, console: Console, top_n: int = 3):
    """Show rankings comparison with colored rows."""
    ranking_types = [
        ("✅ Top Approvers", "top_approvers"),
        ("👥 Top Reviewers", "top_reviewers"),
        ("📝 Most Requested", "top_requested_reviewers")
    ]
    
    # Row color pattern: bright-green, cyan, yellow, white, and neutral colors below
    row_styles = ["bright_green", "cyan", "yellow", "white", "dim", "grey58", "grey42"]
    
    for title, ranking_key in ranking_types:
        table = Table(title=title, show_header=True, header_style="bold blue")
        table.add_column("Rank", style="white", justify="center", width=4)
        
        for user in user_analytics.keys():
            display_name = user[:12] + "..." if len(user) > 15 else user
            table.add_column(display_name, style="cyan", min_width=20)
        
        # Get all unique people across all users
        all_people = set()
        for analytics in user_analytics.values():
            ranking = analytics.get(ranking_key, {})
            all_people.update(ranking.keys())
        
        # Create ranking display - always show at least 7, up to top_n
        medals = ["🥇", "🥈", "🥉"]
        max_rank = max(7, top_n)  # Show at least 7 (top 5 + 2 more), up to top_n
        
        for rank in range(max_rank):
            rank_display = medals[rank] if rank < 3 else f"{rank+1}."
            row = [rank_display]
            
            for user, analytics in user_analytics.items():
                ranking = analytics.get(ranking_key, {})
                ranked_list = list(ranking.items())
                
                if rank < len(ranked_list):
                    person, count = ranked_list[rank]
                    row.append(f"{person} ({count})")
                else:
                    row.append("-")
            
            # Get style for this row
            row_style = row_styles[min(rank, len(row_styles)-1)]
            table.add_row(*row, style=row_style)
        
        console.print(table)
        console.print()


def _show_comparison_patterns(user_analytics: dict, console: Console):
    """Show review patterns comparison."""
    table = Table(title="🔄 Review Patterns Comparison", show_header=True, header_style="bold blue")
    table.add_column("Pattern", style="yellow", min_width=18)
    
    for user in user_analytics.keys():
        display_name = user[:12] + "..." if len(user) > 15 else user
        table.add_column(display_name, justify="right", style="cyan")
    
    patterns = [
        ("Same-day reviews", "same_day_reviews"),
        ("Quick approvals", "quick_approvals")
    ]
    
    for pattern_name, key in patterns:
        row = [pattern_name]
        for user, analytics in user_analytics.items():
            patterns_data = analytics.get('review_patterns', {})
            count = patterns_data.get(key, 0)
            total = analytics.get('total_prs', 1)
            percentage = (count / total) * 100 if total > 0 else 0
            row.append(f"{count} ({percentage:.1f}%)")
        table.add_row(*row)
    
    console.print(table)
    console.print()


def _get_nested_value(data: dict, key_path: str):
    """Get value from nested dictionary using dot notation."""
    keys = key_path.split('.')
    value = data
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return None
    return value


def _compute_limited_analytics(cache_manager, limit: int) -> dict:
    """Compute analytics for only the most recent N merged PRs."""
    # Get all merged PRs with their IDs and timestamps
    merged_prs = []
    
    for pr_id, pr_data in cache_manager.history.items():
        state = pr_data.get('state', 'UNKNOWN').upper()
        pr_draft = pr_data.get('draft', False) or pr_data.get('is_draft', False)
        
        # Skip non-merged, draft, or stale conflict PRs
        if state != 'MERGED' or pr_draft:
            continue
            
        if hasattr(cache_manager, '_is_stale_conflict_pr'):
            # Check if it's PRCacheManager (needs events) or IncrementalPRCacheManager (doesn't need events)
            if cache_manager.__class__.__name__ == 'PRCacheManager':
                events = pr_data.get('events', [])
                if cache_manager._is_stale_conflict_pr(pr_data, events):
                    continue
            else:
                if cache_manager._is_stale_conflict_pr(pr_data):
                    continue
        
        # Extract PR number from ID for sorting
        pr_num = pr_data.get('id', 0)
        if isinstance(pr_num, str) and pr_num.isdigit():
            pr_num = int(pr_num)
        
        merged_prs.append((pr_num, pr_id, pr_data))
    
    # Sort by PR number (descending) to get most recent first
    merged_prs.sort(key=lambda x: x[0], reverse=True)
    
    # Take only the most recent 'limit' PRs
    limited_prs = merged_prs[:limit]
    
    # Create a temporary limited history for analytics computation
    limited_history = {pr_id: pr_data for _, pr_id, pr_data in limited_prs}
    
    # Temporarily replace the cache manager's history
    original_history = cache_manager.history
    cache_manager.history = limited_history
    
    try:
        # Compute analytics on the limited set
        analytics = cache_manager.compute_analytics()
        # Update the total to reflect actual limited count
        analytics['total_prs'] = len(limited_prs)
    finally:
        # Restore original history
        cache_manager.history = original_history
    
    return analytics


def _compute_date_filtered_analytics(cache_manager, date_filter: dict) -> dict:
    """Compute analytics for PRs within a specific date range."""
    from datetime import datetime
    
    # Get date range
    from_dt = date_filter.get("from")
    to_dt = date_filter.get("to")
    
    # Get all merged PRs within the date range
    filtered_prs = []
    
    for pr_id, pr_data in cache_manager.history.items():
        state = pr_data.get('state', 'UNKNOWN').upper()
        pr_draft = pr_data.get('draft', False) or pr_data.get('is_draft', False)
        
        # Skip non-merged, draft, or stale conflict PRs
        if state != 'MERGED' or pr_draft:
            continue
            
        if hasattr(cache_manager, '_is_stale_conflict_pr'):
            # Check if it's PRCacheManager (needs events) or IncrementalPRCacheManager (doesn't need events)
            if cache_manager.__class__.__name__ == 'PRCacheManager':
                events = pr_data.get('events', [])
                if cache_manager._is_stale_conflict_pr(pr_data, events):
                    continue
            else:
                if cache_manager._is_stale_conflict_pr(pr_data):
                    continue
        
        # Check if PR is within date range
        created_at = pr_data.get('created_at', '')
        if created_at:
            try:
                # Parse PR creation date
                if created_at.endswith('Z'):
                    created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    created_dt = datetime.fromisoformat(created_at)
                
                # Remove timezone info for comparison
                created_dt = created_dt.replace(tzinfo=None)
                
                # Check if within range
                if from_dt and created_dt < from_dt:
                    continue
                if to_dt and created_dt > to_dt:
                    continue
                    
                filtered_prs.append((created_dt, pr_id, pr_data))
            except:
                continue  # Skip PRs with invalid dates
    
    
    if not filtered_prs:
        # Return empty analytics if no PRs in range
        return {
            'total_prs': 0,
            'prs_by_state': {'MERGED': 0},
            'top_reviewers': {},
            'top_approvers': {},
            'top_requested_reviewers': {},
            'top_commenters': {},
            'avg_review_time': 0,
            'avg_checks_time': 0,
            'avg_pr_lifetime': 0,
            'avg_commits_per_pr': 0,
            'pr_velocity': {'monthly': 0, 'weekly': 0}
        }
    
    # Create a temporary filtered history for analytics computation
    filtered_history = {pr_id: pr_data for _, pr_id, pr_data in filtered_prs}
    
    # Temporarily replace the cache manager's history
    original_history = cache_manager.history
    cache_manager.history = filtered_history
    
    try:
        # Compute analytics on the filtered set
        analytics = cache_manager.compute_analytics()
        # Update the total to reflect actual filtered count
        analytics['total_prs'] = len(filtered_prs)
        return analytics
    finally:
        # Restore original history
        cache_manager.history = original_history