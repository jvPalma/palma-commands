from prs.cache.manager import PRCacheManager
from prs.config import get
from prs.core.helpers import resolve_owner
from prs.core.rich_display import display_prs_rich, display_prs_table
from prs.vc_tools.github.client import get_pull_request_details, list_pull_request_ids
from prs.core.ci.manager import get_ci_manager


def list_pull_requests(options: dict):
    # Read display modes from CLI options or config as fallback.
    include_drafts = options.get("include_draft", False)
    enable_cache = options.get("enable_cache", True)  # Cache enabled by default
    display_format = options.get("format", "panels")  # panels or table

    ci_mode = options.get("ci", get("pr-info", "ci", fallback=get("pr-info", "checks", fallback="short")))
    review_mode = options.get("reviews", get("pr-info", "reviews", fallback="short"))
    labels_mode = options.get("labels", get("pr-info", "labels", fallback="short"))
    comments_mode = options.get("comments", get("pr-info", "comments", fallback="short"))
    pr_url_mode = options.get("pr_url", get("pr-info", "pr_url", fallback="short"))
    branch_mode = options.get("branch", get("pr-info", "branch", fallback="short"))
    author_mode = options.get("author", get("pr-info", "author", fallback="short"))

    filters = {
        "state": "open",
        "include_draft": include_drafts,
    }

    # Initialize cache manager if enabled
    cache_manager = None
    if enable_cache:
        username = get("git", "username")
        owner = resolve_owner()
        repo_name = get("git", "repo_name")
        if username and owner and repo_name:
            cache_manager = PRCacheManager(username, owner, repo_name)
    
    # Initialize CI manager
    ci_manager = get_ci_manager()
    
    # Prepare repository information for CI data
    owner = resolve_owner()
    repo_name = get("git", "repo_name")
    repository = f"{owner}/{repo_name}" if owner and repo_name else None
    
    pr_refs = list_pull_request_ids(filters)
    all_prs = []
    for pr_id, source_tag, is_draft in pr_refs:
        pr_model = get_pull_request_details(pr_id)
        pr_model.source = source_tag
        pr_model.isDraft = is_draft
        
        # Fetch CI data for this PR
        if repository:
            ci_data = ci_manager.get_ci_data(repository, pr_id)
            if ci_data:
                # Add CI workflows to the PR model as additional check data
                pr_model.ci_data = ci_data
                
                # Integrate CI workflows into checks for backward compatibility
                ci_checks = []
                for workflow in ci_data.workflows:
                    ci_checks.append({
                        'name': workflow.name,
                        'status': workflow.status.upper(),
                        'conclusion': workflow.conclusion.upper(),
                        'context': f"github-actions/{workflow.name}",
                        'state': workflow.conclusion.upper() if workflow.status == 'completed' else workflow.status.upper(),
                        'target_url': workflow.html_url,
                        'description': f"GitHub Actions workflow: {workflow.name}",
                        'ci_provider': 'github_actions',
                        'workflow_id': workflow.id,
                        'run_number': workflow.run_number,
                        'duration': workflow.duration,
                        'event': workflow.event
                    })
                
                # Merge CI checks with existing checks
                pr_model.checks = pr_model.checks + ci_checks
            else:
                pr_model.ci_data = None
        
        all_prs.append(pr_model)
        
        # Update cache if enabled
        if cache_manager:
            try:
                # Prepare cache data
                cache_data = {
                    "id": pr_model.id,
                    "title": pr_model.title,
                    "author": pr_model.author,
                    "created_at": pr_model.created_at,
                    "updated_at": pr_model.updated_at,
                    "state": pr_model.state,
                    "is_draft": pr_model.is_draft,
                    "additions": pr_model.additions,
                    "deletions": pr_model.deletions,
                    "changed_files": pr_model.changed_files,
                    "checks": {
                        "status": "unknown"  # Will be enhanced
                    },
                    "reviews": pr_model.reviews,
                    "review_requests": [],  # TODO: Extract from reviewRequests
                    "labels": pr_model.labels,
                    "merged": pr_model.merged,
                    "merged_at": pr_model.merged_at,
                    "closed_at": pr_model.closed_at,
                    "merged_by": pr_model.merged_by.get("login") if pr_model.merged_by else None,
                    "commit_count": len(pr_model.commits)
                }
                
                # Pass detailed checks information for enhanced analysis
                if pr_model.checks:
                    # Pass the full checks array for detailed analysis
                    cache_data["checks"] = pr_model.checks
                
                # Add CI data to cache if available
                if hasattr(pr_model, 'ci_data') and pr_model.ci_data:
                    cache_data["ci_data"] = {
                        "total_workflows": pr_model.ci_data.total_workflows,
                        "successful_workflows": pr_model.ci_data.successful_workflows,
                        "failed_workflows": pr_model.ci_data.failed_workflows,
                        "pending_workflows": pr_model.ci_data.pending_workflows
                    }
                
                cache_manager.update_pr(cache_data)
            except Exception as e:
                # Don't fail if cache update fails
                pass

    # Prepare display options
    display_options = {
        "ci_mode": ci_mode,
        "review_mode": review_mode,
        "labels_mode": labels_mode,
        "comments_mode": comments_mode,
        "pr_url_mode": pr_url_mode,
        "branch_mode": branch_mode,
        "author_mode": author_mode,
    }
    
    # Use Rich display
    if display_format == "table":
        display_prs_table(all_prs, display_options)
    else:
        display_prs_rich(all_prs, display_options)
