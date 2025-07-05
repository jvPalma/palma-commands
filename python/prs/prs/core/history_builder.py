"""
Build comprehensive PR history by fetching all PRs (open, closed, merged)
"""
import subprocess
import json
from datetime import datetime
import time

from prs.cache.manager import PRCacheManager
from prs.cache.incremental_manager import IncrementalPRCacheManager
from prs.config import get
from prs.core.helpers import resolve_owner, read_authors
from prs.core.quarterly_chunks import QuarterlyChunkCalculator, QuarterChunk
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn, TimeElapsedColumn
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich import box


def fetch_all_prs_for_history(state: str = "all", limit: int = 100, users: list = None):
    """Fetch PRs using gh CLI with specified state and date ranges for better coverage."""
    owner = resolve_owner()
    repo_name = get("git", "repo_name")
    
    # Use provided users or fallback to config authors
    if users:
        authors = users
    else:
        authors = read_authors()
    
    all_prs = []
    
    # Use 10-year date ranges to ensure we get comprehensive historical data
    current_year = datetime.now().year
    date_ranges = []
    for year in range(current_year - 9, current_year + 1):  # 10 years back to current
        date_ranges.append(f"{year}-01-01..{year}-12-31")
    
    for author in authors:
        for date_range in date_ranges:
            # Build query with date range
            if state == "all":
                query = f"repo:{owner}/{repo_name} is:pr author:{author} created:{date_range}"
            else:
                query = f"repo:{owner}/{repo_name} is:pr is:{state} author:{author} created:{date_range}"
            
            gh_args = [
                "gh",
                "api",
                "-X",
                "GET",
                "search/issues",
                "-f",
                f"q={query}",
                "-f",
                f"per_page=100",  # Use max per page
                "--jq",
                ".items | .[] | .number"
            ]
            
            try:
                output = subprocess.check_output(gh_args, text=True)
                pr_numbers = [int(num) for num in output.strip().split('\n') if num]
                all_prs.extend(pr_numbers)
            except subprocess.CalledProcessError:
                continue
    
    return list(set(all_prs))  # Remove duplicates


def _build_single_user_history(user: str, owner: str, repo_name: str, limit: int, fetch_all: bool):
    """Build history for a single user."""
    cache_manager = PRCacheManager(user, owner, repo_name)
    
    # Fetch PRs for this specific user
    if fetch_all:
        pr_numbers = fetch_all_prs_for_history("all", limit, [user])
    else:
        open_prs = fetch_all_prs_for_history("open", limit, [user])
        closed_prs = fetch_all_prs_for_history("closed", limit, [user])
        pr_numbers = list(set(open_prs + closed_prs))[:limit]
    
    # Limit to prevent API rate limiting and timeouts
    if len(pr_numbers) > 100:
        console = Console()
        console.print(f"   [yellow]Found {len(pr_numbers)} PRs for {user} - limiting to 100 to avoid rate limits[/yellow]")
        pr_numbers = pr_numbers[:100]
    else:
        console = Console()
        console.print(f"   [cyan]Found {len(pr_numbers)} PRs to process for {user}[/cyan]")
    
    processed = 0
    new_prs = 0
    updated_prs = 0
    
    for i, pr_id in enumerate(pr_numbers):
        # Progress will be shown via Rich progress bar
        
        # Get full PR details with error handling
        try:
            pr_data = get_pr_full_details(pr_id)
            if not pr_data:
                continue
        except Exception as e:
            console = Console()
            console.print(f"\n   [yellow]⚠️  Error fetching PR #{pr_id}: {str(e)[:50]}...[/yellow]")
            # If we hit rate limits or other API errors, stop processing this user
            if "rate limit" in str(e).lower() or "403" in str(e):
                console = Console()
                console.print(f"\n   [red]🛑 API rate limit hit for {user}. Stopping to avoid further issues.[/red]")
                break
            continue
        
        # Prepare cache data
        cache_data = {
            "id": pr_data.get("number"),
            "title": pr_data.get("title"),
            "author": pr_data.get("author", {}).get("login", ""),
            "created_at": pr_data.get("createdAt"),
            "updated_at": pr_data.get("updatedAt"),
            "state": pr_data.get("state", "OPEN"),
            "is_draft": pr_data.get("isDraft", False),
            "additions": pr_data.get("additions", 0),
            "deletions": pr_data.get("deletions", 0),
            "changed_files": pr_data.get("changedFiles", 0),
            "reviews": pr_data.get("reviews", []),
            "review_requests": [r.get("login", "") for r in pr_data.get("reviewRequests", []) if r],
            "labels": [lbl.get("name", "") for lbl in pr_data.get("labels", [])],
            "merged": pr_data.get("mergedAt") is not None,
            "merged_at": pr_data.get("mergedAt"),
            "closed_at": pr_data.get("closedAt"),
            "merged_by": pr_data.get("mergedBy", {}).get("login") if pr_data.get("mergedBy") else None,
            "commits": pr_data.get("commits", []),
            "commit_count": len(pr_data.get("commits", [])),
            "checks": {}
        }
        
        # Pass detailed checks information for enhanced analysis
        checks = pr_data.get("statusCheckRollup", [])
        if checks:
            cache_data["checks"] = checks
        
        # Update cache
        is_new = cache_manager.update_pr(cache_data)
        if is_new:
            new_prs += 1
        else:
            updated_prs += 1
        processed += 1
    
    console = Console()
    console.print(f"\n   [green]✅ {user}: {processed} PRs processed ({new_prs} new, {updated_prs} updated)[/green]")


def get_pr_full_details(pr_id: int):
    """Get comprehensive PR details including timeline events."""
    owner = resolve_owner()
    repo_name = get("git", "repo_name")
    
    # Get basic PR info
    gh_args = [
        "gh",
        "pr",
        "view",
        str(pr_id),
        "--repo",
        f"{owner}/{repo_name}",
        "--json",
        "number,title,author,labels,statusCheckRollup,reviews,reviewRequests,url,headRefName,isDraft,comments,additions,deletions,changedFiles,createdAt,updatedAt,state,commits,mergedAt,closedAt,mergedBy"
    ]
    
    try:
        output = subprocess.check_output(gh_args, text=True)
        return json.loads(output)
    except subprocess.CalledProcessError:
        return None


def build_pr_history(options: dict):
    """Build comprehensive PR history by fetching all PRs."""
    console = Console()
    console.print("\n[bold cyan]🔨 Building PR History[/bold cyan]")
    
    # Get configuration
    username = get("git", "username")
    owner = resolve_owner()
    repo_name = get("git", "repo_name")
    
    if not username or not owner or not repo_name:
        console.print("[red]Error: Missing configuration[/red]")
        return
    
    # Check if chunk-based processing is requested
    use_chunks = options.get("chunk", False)
    use_incremental = options.get("incremental", False)
    
    if use_chunks:
        _build_history_with_chunks(options, username, owner, repo_name, use_incremental)
    else:
        _build_history_traditional(options, username, owner, repo_name)


def _build_history_with_chunks(options: dict, username: str, owner: str, repo_name: str, use_incremental: bool = False):
    """Build PR history using quarterly chunks for efficient processing."""
    console = Console()
    console.print("\n[bold cyan]🔄 Using Quarterly Chunk-Based Processing[/bold cyan]")
    
    # Validate chunk options first
    validation = validate_chunk_options(options)
    if not validation["valid"]:
        console.print("\n[bold red]❌ Validation Errors:[/bold red]")
        for error in validation["errors"]:
            console.print(f"   • {error}")
        return
    
    # Show validation warnings and recommendations
    if validation["warnings"]:
        console.print("\n[bold yellow]⚠️  Warnings:[/bold yellow]")
        for warning in validation["warnings"]:
            console.print(f"   • {warning}")
    
    if validation["recommendations"]:
        console.print("\n[bold cyan]💡 Recommendations:[/bold cyan]")
        for rec in validation["recommendations"]:
            console.print(f"   • {rec}")
    
    # Get chunk options
    start_year = options.get("start_year")
    end_year = options.get("end_year")
    max_chunks = options.get("max_chunks")
    limit = options.get("limit", 50)
    fetch_all = options.get("all", False)
    users_option = options.get("users")
    
    # Parse users if provided
    target_users = None
    if users_option:
        target_users = [user.strip() for user in users_option.split(",") if user.strip()]
        console.print(f"🎯 Target users: [cyan]{', '.join(target_users)}[/cyan]")
    else:
        target_users = read_authors()
        console.print(f"📋 Using config authors: [cyan]{', '.join(target_users)}[/cyan]")
    
    console.print(f"📦 Repository: [blue]{owner}/{repo_name}[/blue]")
    console.print(f"👤 Current User: [yellow]{username}[/yellow]")
    
    # Calculate chunks
    from datetime import date
    reference_date = date.today()
    
    # Set default start year to 10 years back if not specified
    if not start_year:
        start_year = reference_date.year - 9  # 10 years back
    
    chunks = QuarterlyChunkCalculator.calculate_chunks(
        reference_date=reference_date,
        start_year=start_year,
        end_year=end_year,
        max_chunks=max_chunks
    )
    
    # Apply max_chunks limit if specified
    if max_chunks and max_chunks < len(chunks):
        chunks = chunks[-max_chunks:]  # Take the most recent chunks
        console.print(f"📊 Limited to [cyan]{max_chunks}[/cyan] most recent chunks")
    
    # Show chunk analysis
    console.print(f"\n[bold yellow]📊 Chunk Analysis:[/bold yellow]")
    console.print(f"   • Total chunks: [cyan]{len(chunks)}[/cyan]")
    console.print(f"   • Time span: [cyan]{chunks[-1].year}[/cyan] to [cyan]{chunks[0].year}[/cyan]")
    console.print(f"   • Date range: [cyan]{chunks[-1].start_date}[/cyan] to [cyan]{chunks[0].end_date}[/cyan]")
    console.print(f"   • Estimated API calls: [cyan]{len(chunks) * len(target_users) * 2}[/cyan]")
    
    # Validate chunk parameters
    warnings = QuarterlyChunkCalculator.validate_parameters(start_year, end_year, max_chunks)
    if warnings:
        console.print(f"\n[bold yellow]⚠️  Warnings:[/bold yellow]")
        for warning in warnings:
            console.print(f"   • {warning}")
    
    # Process each user
    for user_idx, user in enumerate(target_users):
        console.print(f"\n👤 Processing user: [cyan]{user}[/cyan] ({user_idx + 1}/{len(target_users)})")
        
        # Initialize cache manager (incremental or traditional)
        if use_incremental:
            cache_manager = IncrementalPRCacheManager(user, owner, repo_name)
            console.print(f"   📊 Using [green]incremental cache manager[/green] with intelligent merging")
        else:
            cache_manager = PRCacheManager(user, owner, repo_name)
            console.print(f"   📊 Using [yellow]traditional cache manager[/yellow]")
        
        # Process chunks for this user
        total_processed = 0
        total_new = 0
        total_updated = 0
        
        for chunk_idx, chunk in enumerate(chunks):
            progress_percent = round((chunk_idx + 1) / len(chunks) * 100, 1)
            
            console.print(f"\n   📅 [blue]Processing {chunk.description}[/blue] ({chunk_idx + 1}/{len(chunks)} - {progress_percent}%)")
            console.print(f"      📊 Date range: [cyan]{chunk.start_date}[/cyan] to [cyan]{chunk.end_date}[/cyan]")
            
            # Fetch PRs for this chunk
            chunk_prs = _fetch_prs_for_chunk(chunk, [user], owner, repo_name, fetch_all, limit)
            
            if not chunk_prs:
                console.print(f"      ✅ No PRs found for [blue]{chunk.description}[/blue]")
                continue
            
            console.print(f"      📥 Found [cyan]{len(chunk_prs)}[/cyan] PRs to process")
            
            # Process PRs in this chunk
            chunk_processed, chunk_new, chunk_updated = _process_chunk_prs(
                chunk_prs, cache_manager, use_incremental, chunk.description
            )
            
            total_processed += chunk_processed
            total_new += chunk_new
            total_updated += chunk_updated
            
            console.print(f"      ✅ [blue]{chunk.description}[/blue]: [cyan]{chunk_processed}[/cyan] PRs processed ([green]{chunk_new}[/green] new, [yellow]{chunk_updated}[/yellow] updated)")
            
            # Add small delay to avoid API rate limits
            if chunk_idx < len(chunks) - 1:  # Don't delay after last chunk
                time.sleep(1)
        
        # Show summary for this user
        console.print(f"\n   [bold green]✅ User {user} Summary:[/bold green]")
        console.print(f"      • Total processed: [cyan]{total_processed}[/cyan] PRs")
        console.print(f"      • New: [green]{total_new}[/green]")
        console.print(f"      • Updated: [yellow]{total_updated}[/yellow]")
        
        # Show incremental update summary if applicable
        if use_incremental and hasattr(cache_manager, 'get_update_summary'):
            update_summary = cache_manager.get_update_summary()
            console.print(f"      • Data quality improvements: [magenta]{update_summary.get('data_quality_improvements', 0)}[/magenta]")
            console.print(f"      • Conflicts detected: [red]{update_summary.get('conflicts_detected', 0)}[/red]")
    
    console.print(f"\n\n[bold green]🎉 Chunk-based history build complete![/bold green]")
    console.print(f"   📊 Processed [cyan]{len(chunks)}[/cyan] quarterly chunks")
    console.print(f"   👥 Processed [cyan]{len(target_users)}[/cyan] users")
    console.print(f"   📅 Time range: [cyan]{chunks[0].start_date}[/cyan] to [cyan]{chunks[-1].end_date}[/cyan]")
    
    # Show analytics summary for the primary user
    primary_user = target_users[0] if len(target_users) == 1 else username
    if use_incremental:
        cache_manager = IncrementalPRCacheManager(primary_user, owner, repo_name)
    else:
        cache_manager = PRCacheManager(primary_user, owner, repo_name)
    
    analytics = cache_manager.compute_analytics()
    console.print(f"\n[bold yellow]📊 Final Summary:[/bold yellow]")
    console.print(f"   • Total PRs in history: [cyan]{analytics['total_prs']}[/cyan]")
    if analytics['prs_by_state']:
        for state, count in analytics['prs_by_state'].items():
            state_color = "green" if state.upper() == "MERGED" else "yellow" if state.upper() == "OPEN" else "red"
            console.print(f"   • {state.capitalize()}: [{state_color}]{count}[/{state_color}]")
    
    console.print()  # Empty line


def _fetch_prs_for_chunk(chunk: QuarterChunk, users: list, owner: str, repo_name: str, fetch_all: bool, limit: int) -> list:
    """Fetch PRs for a specific quarterly chunk."""
    all_prs = []
    
    for user in users:
        # Build query for this chunk
        if fetch_all:
            query = f"repo:{owner}/{repo_name} is:pr author:{user} created:{chunk.date_range}"
        else:
            # Fetch both open and closed PRs for this time range
            for state in ['open', 'closed']:
                query = f"repo:{owner}/{repo_name} is:pr is:{state} author:{user} created:{chunk.date_range}"
                
                gh_args = [
                    "gh",
                    "api",
                    "-X",
                    "GET",
                    "search/issues",
                    "-f",
                    f"q={query}",
                    "-f",
                    f"per_page=100",
                    "--jq",
                    ".items | .[] | .number"
                ]
                
                try:
                    output = subprocess.check_output(gh_args, text=True)
                    pr_numbers = [int(num) for num in output.strip().split('\n') if num]
                    all_prs.extend(pr_numbers)
                except subprocess.CalledProcessError:
                    continue
        
        if fetch_all:
            # Single query for all states
            gh_args = [
                "gh",
                "api",
                "-X",
                "GET",
                "search/issues",
                "-f",
                f"q={query}",
                "-f",
                f"per_page=100",
                "--jq",
                ".items | .[] | .number"
            ]
            
            try:
                output = subprocess.check_output(gh_args, text=True)
                pr_numbers = [int(num) for num in output.strip().split('\n') if num]
                all_prs.extend(pr_numbers)
            except subprocess.CalledProcessError:
                continue
    
    # Remove duplicates and apply limit
    unique_prs = list(set(all_prs))
    if limit and len(unique_prs) > limit:
        unique_prs = unique_prs[:limit]
    
    return unique_prs


def _process_chunk_prs(pr_numbers: list, cache_manager, use_incremental: bool, chunk_label: str) -> tuple:
    """Process PRs for a specific chunk."""
    console = Console()
    processed = 0
    new_prs = 0
    updated_prs = 0
    
    for i, pr_id in enumerate(pr_numbers):
        # Progress will be shown via Rich status messages
        
        # Get full PR details with error handling and retry logic
        retry_count = 0
        max_retries = 3
        pr_data = None
        
        while retry_count <= max_retries:
            try:
                pr_data = get_pr_full_details(pr_id)
                if not pr_data:
                    break  # No data returned, skip this PR
                break  # Success, exit retry loop
            except Exception as e:
                should_retry, wait_time, error_msg = handle_chunk_api_errors(e, chunk_label, retry_count)
                
                if should_retry and retry_count < max_retries:
                    if len(pr_numbers) > 5:
                        console = Console()
                        console.print(f"\n      [yellow]⚠️  {error_msg}[/yellow]")
                    time.sleep(wait_time)
                    retry_count += 1
                else:
                    if len(pr_numbers) > 5:
                        console = Console()
                        console.print(f"\n      [red]❌ {error_msg}[/red]")
                    break  # Exit retry loop
        
        if not pr_data:
            continue  # Skip this PR if we couldn't get data
        
        # Prepare cache data
        cache_data = {
            "id": pr_data.get("number"),
            "title": pr_data.get("title"),
            "author": pr_data.get("author", {}).get("login", ""),
            "created_at": pr_data.get("createdAt"),
            "updated_at": pr_data.get("updatedAt"),
            "state": pr_data.get("state", "OPEN"),
            "is_draft": pr_data.get("isDraft", False),
            "additions": pr_data.get("additions", 0),
            "deletions": pr_data.get("deletions", 0),
            "changed_files": pr_data.get("changedFiles", 0),
            "reviews": pr_data.get("reviews", []),
            "review_requests": [r.get("login", "") for r in pr_data.get("reviewRequests", []) if r],
            "labels": [lbl.get("name", "") for lbl in pr_data.get("labels", [])],
            "merged": pr_data.get("mergedAt") is not None,
            "merged_at": pr_data.get("mergedAt"),
            "closed_at": pr_data.get("closedAt"),
            "merged_by": pr_data.get("mergedBy", {}).get("login") if pr_data.get("mergedBy") else None,
            "commits": pr_data.get("commits", []),
            "commit_count": len(pr_data.get("commits", [])),
            "checks": {}
        }
        
        # Pass detailed checks information for enhanced analysis
        checks = pr_data.get("statusCheckRollup", [])
        if checks:
            cache_data["checks"] = checks
        
        # Update cache (incremental or traditional)
        if use_incremental:
            # Use incremental update with intelligent merging
            update_result = cache_manager.incremental_update_pr(cache_data, "chunk_api")
            if update_result.update_type.value in ['created', 'updated', 'enriched', 'merged']:
                if update_result.update_type.value == 'created':
                    new_prs += 1
                else:
                    updated_prs += 1
                processed += 1
        else:
            # Use traditional update
            is_new = cache_manager.update_pr(cache_data)
            if is_new:
                new_prs += 1
            else:
                updated_prs += 1
            processed += 1
    
    # Rich console handles progress display automatically
    
    return processed, new_prs, updated_prs


def _build_history_traditional(options: dict, username: str, owner: str, repo_name: str):
    """Build PR history using traditional approach (existing logic)."""
    console = Console()
    
    # Get options
    limit = options.get("limit", 50)
    fetch_all = options.get("all", False)
    users_option = options.get("users")
    
    # Parse users if provided
    target_users = None
    if users_option:
        target_users = [user.strip() for user in users_option.split(",") if user.strip()]
        print(f"🎯 Target users: {', '.join(target_users)}")
    else:
        target_users = read_authors()
        print(f"📋 Using config authors: {', '.join(target_users)}")
    
    print(f"📦 Repository: {color_text(f'{owner}/{repo_name}', 'blue')}")
    print(f"👤 Current User: {color_text(username, 'yellow')}")
    
    # Handle multi-user builds differently
    if users_option and len(target_users) > 1:
        print(f"\n🔄 Building history for multiple users...")
        print(f"💡 Tip: For large datasets, consider using --chunk to avoid API rate limits")
        for user in target_users:
            print(f"\n👤 Processing user: {color_text(user, 'cyan')}")
            _build_single_user_history(user, owner, repo_name, limit, fetch_all)
        return
    
    # Single user build (current user or single specified user)
    cache_user = target_users[0] if users_option and len(target_users) == 1 else username
    cache_manager = PRCacheManager(cache_user, owner, repo_name)
    
    # Determine what to fetch
    if fetch_all:
        print(f"\n📥 Fetching ALL PRs (open, closed, merged)...")
        pr_numbers = fetch_all_prs_for_history("all", limit, target_users)
    else:
        print(f"\n📥 Fetching last {limit} PRs...")
        # Fetch open PRs
        open_prs = fetch_all_prs_for_history("open", limit, target_users)
        # Fetch closed PRs
        closed_prs = fetch_all_prs_for_history("closed", limit, target_users)
        pr_numbers = list(set(open_prs + closed_prs))[:limit]
    
    print(f"Found {len(pr_numbers)} PRs to process")
    
    # Process each PR
    processed = 0
    new_prs = 0
    updated_prs = 0
    
    for i, pr_id in enumerate(pr_numbers):
        print(f"\r⚙️  Processing PR #{pr_id} ({i+1}/{len(pr_numbers)})... ", end='', flush=True)
        
        # Get full PR details
        pr_data = get_pr_full_details(pr_id)
        if not pr_data:
            continue
        
        # Prepare cache data
        cache_data = {
            "id": pr_data.get("number"),
            "title": pr_data.get("title"),
            "author": pr_data.get("author", {}).get("login", ""),
            "created_at": pr_data.get("createdAt"),
            "updated_at": pr_data.get("updatedAt"),
            "state": pr_data.get("state", "OPEN"),
            "is_draft": pr_data.get("isDraft", False),
            "additions": pr_data.get("additions", 0),
            "deletions": pr_data.get("deletions", 0),
            "changed_files": pr_data.get("changedFiles", 0),
            "reviews": pr_data.get("reviews", []),
            "review_requests": [r.get("login", "") for r in pr_data.get("reviewRequests", []) if r],
            "labels": [lbl.get("name", "") for lbl in pr_data.get("labels", [])],
            "merged": pr_data.get("mergedAt") is not None,
            "merged_at": pr_data.get("mergedAt"),
            "closed_at": pr_data.get("closedAt"),
            "merged_by": pr_data.get("mergedBy", {}).get("login") if pr_data.get("mergedBy") else None,
            "commits": pr_data.get("commits", []),
            "commit_count": len(pr_data.get("commits", [])),
            "checks": {}
        }
        
        # Pass detailed checks information for enhanced analysis
        checks = pr_data.get("statusCheckRollup", [])
        if checks:
            cache_data["checks"] = checks
        
        # Update cache
        is_new = cache_manager.update_pr(cache_data)
        if is_new:
            new_prs += 1
        else:
            updated_prs += 1
        processed += 1
    
    # Compute analytics
    print(f"\n\n✅ History build complete!")
    print(f"   • Processed: {processed} PRs")
    print(f"   • New: {new_prs}")
    print(f"   • Updated: {updated_prs}")
    
    # Show analytics summary
    analytics = cache_manager.compute_analytics()
    print(f"\n📊 {color_text('Summary:', 'yellow')}")
    print(f"   • Total PRs in history: {analytics['total_prs']}")
    if analytics['prs_by_state']:
        for state, count in analytics['prs_by_state'].items():
            print(f"   • {state.capitalize()}: {count}")
    
    print()  # Empty line


def validate_chunk_options(options: dict) -> dict:
    """Validate chunk-based processing options and provide feedback."""
    validation_result = {
        "valid": True,
        "warnings": [],
        "errors": [],
        "recommendations": []
    }
    
    # Validate year range
    start_year = options.get("start_year")
    end_year = options.get("end_year")
    current_year = datetime.now().year
    
    if start_year and start_year > current_year:
        validation_result["errors"].append(f"Start year ({start_year}) cannot be in the future")
        validation_result["valid"] = False
    
    if end_year and end_year > current_year:
        validation_result["errors"].append(f"End year ({end_year}) cannot be in the future")
        validation_result["valid"] = False
    
    if start_year and end_year and start_year > end_year:
        validation_result["errors"].append(f"Start year ({start_year}) cannot be after end year ({end_year})")
        validation_result["valid"] = False
    
    # Validate max_chunks
    max_chunks = options.get("max_chunks")
    if max_chunks and max_chunks < 1:
        validation_result["errors"].append("Max chunks must be at least 1")
        validation_result["valid"] = False
    
    # Validate limit
    limit = options.get("limit", 50)
    if limit < 1:
        validation_result["errors"].append("Limit must be at least 1")
        validation_result["valid"] = False
    elif limit > 100:
        validation_result["warnings"].append(f"Limit ({limit}) is high, may hit API rate limits")
    
    # Provide recommendations
    if not options.get("incremental") and options.get("chunk"):
        validation_result["recommendations"].append("Consider using --incremental with --chunk for better data merging")
    
    if max_chunks and max_chunks > 20:
        validation_result["recommendations"].append("Large number of chunks may take significant time to process")
    
    return validation_result


def handle_chunk_api_errors(error: Exception, chunk_label: str, retry_count: int = 0) -> tuple:
    """
    Handle API errors during chunk processing.
    
    Returns:
        tuple: (should_retry, wait_time, error_message)
    """
    error_str = str(error).lower()
    
    # Rate limit errors
    if "rate limit" in error_str or "403" in error_str:
        if retry_count < 3:
            wait_time = min(60 * (2 ** retry_count), 300)  # Exponential backoff, max 5 minutes
            return True, wait_time, f"API rate limit hit for {chunk_label}. Retrying in {wait_time} seconds..."
        else:
            return False, 0, f"API rate limit exceeded for {chunk_label}. Max retries reached."
    
    # Network errors
    elif "network" in error_str or "timeout" in error_str or "connection" in error_str:
        if retry_count < 2:
            wait_time = 30
            return True, wait_time, f"Network error for {chunk_label}. Retrying in {wait_time} seconds..."
        else:
            return False, 0, f"Network error for {chunk_label}. Max retries reached."
    
    # GitHub API errors
    elif "api" in error_str or "github" in error_str:
        if retry_count < 1:
            wait_time = 10
            return True, wait_time, f"GitHub API error for {chunk_label}. Retrying in {wait_time} seconds..."
        else:
            return False, 0, f"GitHub API error for {chunk_label}. Skipping chunk."
    
    # Other errors - don't retry
    else:
        return False, 0, f"Unexpected error for {chunk_label}: {str(error)[:100]}..."


def clear_pr_history(options: dict):
    """Clear PR history cache."""
    username = get("git", "username")
    owner = resolve_owner()
    repo_name = get("git", "repo_name")
    
    if not username or not owner or not repo_name:
        console.print("[red]Error: Missing configuration[/red]")
        return
    
    cache_manager = PRCacheManager(username, owner, repo_name)
    
    # Clear the cache
    cache_manager.history = {}
    cache_manager.index = {}
    cache_manager.analytics = {}
    cache_manager._save_history()
    cache_manager._save_json({}, cache_manager.analytics_file)
    
    print(f"✅ Cleared PR history for {color_text(f'{owner}/{repo_name}', 'blue')}")


def update_pr_history(options: dict):
    """Update existing PR history with latest data."""
    print(f"\n🔄 {color_text('Updating PR History', 'cyan')}")
    
    # Get configuration
    username = get("git", "username")
    owner = resolve_owner()
    repo_name = get("git", "repo_name")
    
    if not username or not owner or not repo_name:
        console.print("[red]Error: Missing configuration[/red]")
        return
    
    # Get options
    users_option = options.get("users")
    limit = options.get("limit")
    force_update = options.get("force", False)
    
    # Parse users if provided
    target_users = None
    if users_option:
        target_users = [user.strip() for user in users_option.split(",") if user.strip()]
        print(f"🎯 Target users: {', '.join(target_users)}")
    else:
        # Default to current user
        target_users = [username]
        print(f"👤 Updating for current user: {username}")
    
    print(f"📦 Repository: {color_text(f'{owner}/{repo_name}', 'blue')}")
    print(f"🔧 Force update: {color_text('Yes' if force_update else 'No', 'yellow')}")
    
    # Process each user
    for user_idx, user in enumerate(target_users):
        print(f"\n👤 Updating history for: {color_text(user, 'cyan')} ({user_idx + 1}/{len(target_users)})")
        
        # Initialize cache manager (prefer incremental for better merging)
        try:
            cache_manager = IncrementalPRCacheManager(user, owner, repo_name)
            use_incremental = True
            print(f"   📊 Using incremental cache manager with intelligent merging")
        except:
            # Fallback to traditional if incremental not available
            cache_manager = PRCacheManager(user, owner, repo_name)
            use_incremental = False
            print(f"   📊 Using traditional cache manager")
        
        # Get existing PRs from cache
        if hasattr(cache_manager, 'get_all_prs'):
            existing_prs = cache_manager.get_all_prs()
        else:
            # For IncrementalPRCacheManager, access index directly
            existing_prs = cache_manager.index
        
        if not existing_prs:
            print(f"   ⚠️  No existing PR history found for {user}")
            print(f"   💡 Use 'nprs build-history --users=\"{user}\"' to build initial history")
            continue
        
        print(f"   📋 Found {len(existing_prs)} PRs in cache")
        
        # Apply limit if specified
        pr_ids_to_update = [pr['id'] for pr in existing_prs.values()]
        if limit:
            pr_ids_to_update = pr_ids_to_update[:limit]
            print(f"   🎯 Limiting update to {limit} most recent PRs")
        
        # Update each PR
        updated_count = 0
        enriched_count = 0
        failed_count = 0
        
        for i, pr_id in enumerate(pr_ids_to_update):
            print(f"\r   ⚙️  Updating PR #{pr_id} ({i+1}/{len(pr_ids_to_update)})... ", end='', flush=True)
            
            # Get fresh PR data
            try:
                pr_data = get_pr_full_details(pr_id)
                if not pr_data:
                    failed_count += 1
                    continue
            except Exception as e:
                failed_count += 1
                if "rate limit" in str(e).lower():
                    print(f"\n   🛑 API rate limit hit. Stopping updates for {user}.")
                    break
                continue
            
            # Prepare cache data with all fields
            cache_data = {
                "id": pr_data.get("number"),
                "title": pr_data.get("title"),
                "author": pr_data.get("author", {}).get("login", ""),
                "created_at": pr_data.get("createdAt"),
                "updated_at": pr_data.get("updatedAt"),
                "state": pr_data.get("state", "OPEN"),
                "is_draft": pr_data.get("isDraft", False),
                "additions": pr_data.get("additions", 0),
                "deletions": pr_data.get("deletions", 0),
                "changed_files": pr_data.get("changedFiles", 0),
                "reviews": pr_data.get("reviews", []),
                "review_requests": [r.get("login", "") for r in pr_data.get("reviewRequests", []) if r],
                "labels": [lbl.get("name", "") for lbl in pr_data.get("labels", [])],
                "merged": pr_data.get("mergedAt") is not None,
                "merged_at": pr_data.get("mergedAt"),
                "closed_at": pr_data.get("closedAt"),
                "merged_by": pr_data.get("mergedBy", {}).get("login") if pr_data.get("mergedBy") else None,
                "commits": pr_data.get("commits", []),
                "commit_count": len(pr_data.get("commits", [])),
                "checks": pr_data.get("statusCheckRollup", []) or {},
                "url": pr_data.get("url"),
                "headRefName": pr_data.get("headRefName"),
                "comments": pr_data.get("comments", [])
            }
            
            # Update using appropriate method
            if use_incremental:
                # For incremental manager, check if we should update
                existing_pr = cache_manager.history.get(str(pr_id), {})
                
                # Always update if force is True or if there are significant changes
                if force_update or not existing_pr or _has_significant_changes(existing_pr, cache_data):
                    # Use incremental update
                    update_result = cache_manager.incremental_update_pr(
                        cache_data, 
                        "update_command"
                    )
                    
                    if update_result.update_type.value in ['created', 'updated', 'enriched', 'merged']:
                        if update_result.update_type.value == 'enriched':
                            enriched_count += 1
                        elif update_result.update_type.value == 'created':
                            # This shouldn't happen in update-history, but handle it
                            updated_count += 1
                        else:
                            updated_count += 1
            else:
                # Traditional update - always updates if force is True
                existing_pr = cache_manager.history.get(pr_id, {})
                if force_update or _has_significant_changes(existing_pr, cache_data):
                    cache_manager.update_pr(cache_data)
                    updated_count += 1
        
        print(f"\n   ✅ Update complete for {user}:")
        print(f"      • Updated: {updated_count} PRs")
        if use_incremental:
            print(f"      • Enriched: {enriched_count} PRs")
        print(f"      • Failed: {failed_count} PRs")
        
        # Show data quality summary if using incremental
        if use_incremental and hasattr(cache_manager, 'get_data_quality_summary'):
            quality_summary = cache_manager.get_data_quality_summary()
            print(f"      • Data quality: {quality_summary}")
    
    print(f"\n🎉 {color_text('PR history update complete!', 'green')}")


def _has_significant_changes(existing_pr: dict, new_pr: dict) -> bool:
    """Check if there are significant changes worth updating."""
    # Always update if force is enabled
    if not existing_pr:
        return True
    
    # Check for changes in important fields
    important_fields = [
        'state', 'is_draft', 'merged', 'additions', 'deletions', 
        'changed_files', 'merged_at', 'closed_at', 'updated_at'
    ]
    
    for field in important_fields:
        if existing_pr.get(field) != new_pr.get(field):
            return True
    
    # Check for review changes
    existing_reviews = len(existing_pr.get('reviews', []))
    new_reviews = len(new_pr.get('reviews', []))
    if existing_reviews != new_reviews:
        return True
    
    # Check for label changes
    existing_labels = set(existing_pr.get('labels', []))
    new_labels = set(new_pr.get('labels', []))
    if existing_labels != new_labels:
        return True
    
    # Check for check status changes
    existing_checks = existing_pr.get('checks', {})
    new_checks = new_pr.get('checks', {})
    if existing_checks != new_checks:
        return True
    
    return False