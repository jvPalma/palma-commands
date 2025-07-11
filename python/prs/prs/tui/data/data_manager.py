"""
TUI Data Manager for integrating with existing PRS systems.

This module provides a unified interface for TUI components to access
PR data, CI information, and cache management while maintaining
compatibility with existing PRS functionality.
"""

import asyncio
import threading
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from prs.cache.manager import PRCacheManager
from prs.config import get
from prs.core.helpers import resolve_owner
from prs.core.models import PullRequest
from prs.vc_tools.github.client import get_pull_request_details, list_pull_request_ids
from prs.core.ci.manager import get_ci_manager


@dataclass
class TUIDataUpdate:
    """Represents a data update event for the TUI."""
    timestamp: datetime
    update_type: str  # 'initial', 'refresh', 'pr_update', 'ci_update'
    data: Any
    pr_id: Optional[int] = None


class TUIDataManager:
    """
    Manages data for the TUI interface with caching, real-time updates,
    and integration with existing PRS systems.
    """
    
    def __init__(self):
        self.username = get("git", "username")
        self.owner = resolve_owner()
        self.repo_name = get("git", "repo_name")
        self.repository = f"{self.owner}/{self.repo_name}" if self.owner and self.repo_name else None
        
        # Data storage
        self._prs: List[PullRequest] = []
        self._last_update: Optional[datetime] = None
        self._update_callbacks: List[Callable[[TUIDataUpdate], None]] = []
        
        # Managers
        self._cache_manager = None
        self._ci_manager = None
        self._update_lock = threading.Lock()
        
        # Configuration
        self._refresh_interval = 30  # seconds
        self._auto_refresh = False
        self._refresh_timer = None
        
        self._initialize_managers()
    
    def _initialize_managers(self):
        """Initialize cache and CI managers."""
        if self.username and self.owner and self.repo_name:
            self._cache_manager = PRCacheManager(self.username, self.owner, self.repo_name)
        
        self._ci_manager = get_ci_manager()
    
    def add_update_callback(self, callback: Callable[[TUIDataUpdate], None]):
        """Add a callback function to be called when data updates."""
        self._update_callbacks.append(callback)
    
    def remove_update_callback(self, callback: Callable[[TUIDataUpdate], None]):
        """Remove a callback function."""
        if callback in self._update_callbacks:
            self._update_callbacks.remove(callback)
    
    def _notify_callbacks(self, update: TUIDataUpdate):
        """Notify all registered callbacks of a data update."""
        for callback in self._update_callbacks:
            try:
                callback(update)
            except Exception:
                # Don't let callback errors break the data manager
                pass
    
    async def load_initial_data(self, include_drafts: bool = False) -> List[PullRequest]:
        """Load initial PR data."""
        filters = {
            "state": "open",
            "include_draft": include_drafts,
        }
        
        with self._update_lock:
            pr_refs = list_pull_request_ids(filters)
            self._prs = []
            
            for pr_id, source_tag, is_draft in pr_refs:
                pr_model = get_pull_request_details(pr_id)
                pr_model.source = source_tag
                pr_model.isDraft = is_draft
                
                # Fetch CI data
                if self.repository:
                    ci_data = self._ci_manager.get_ci_data(self.repository, pr_id)
                    if ci_data:
                        pr_model.ci_data = ci_data
                        self._integrate_ci_checks(pr_model, ci_data)
                    else:
                        pr_model.ci_data = None
                
                self._prs.append(pr_model)
                
                # Update cache
                if self._cache_manager:
                    self._update_cache_for_pr(pr_model)
            
            self._last_update = datetime.now()
        
        update = TUIDataUpdate(
            timestamp=self._last_update,
            update_type='initial',
            data=self._prs.copy()
        )
        self._notify_callbacks(update)
        
        return self._prs.copy()
    
    def _integrate_ci_checks(self, pr_model: PullRequest, ci_data):
        """Integrate CI workflow data into PR checks."""
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
    
    def _update_cache_for_pr(self, pr_model: PullRequest):
        """Update cache with PR data."""
        if not self._cache_manager:
            return
        
        try:
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
                "checks": pr_model.checks if pr_model.checks else {"status": "unknown"},
                "reviews": pr_model.reviews,
                "review_requests": [],
                "labels": pr_model.labels,
                "merged": pr_model.merged,
                "merged_at": pr_model.merged_at,
                "closed_at": pr_model.closed_at,
                "merged_by": pr_model.merged_by.get("login") if pr_model.merged_by else None,
                "commit_count": len(pr_model.commits)
            }
            
            # Add CI data to cache if available
            if hasattr(pr_model, 'ci_data') and pr_model.ci_data:
                cache_data["ci_data"] = {
                    "total_workflows": pr_model.ci_data.total_workflows,
                    "successful_workflows": pr_model.ci_data.successful_workflows,
                    "failed_workflows": pr_model.ci_data.failed_workflows,
                    "pending_workflows": pr_model.ci_data.pending_workflows
                }
            
            self._cache_manager.update_pr(cache_data)
        except Exception:
            # Don't fail if cache update fails
            pass
    
    async def refresh_pr_data(self, pr_id: Optional[int] = None) -> List[PullRequest]:
        """Refresh data for a specific PR or all PRs."""
        if pr_id:
            return await self._refresh_single_pr(pr_id)
        else:
            return await self._refresh_all_prs()
    
    async def _refresh_single_pr(self, pr_id: int) -> List[PullRequest]:
        """Refresh data for a single PR."""
        with self._update_lock:
            # Find the PR in our current list
            pr_index = None
            for i, pr in enumerate(self._prs):
                if pr.id == pr_id:
                    pr_index = i
                    break
            
            if pr_index is None:
                return self._prs.copy()
            
            # Refresh the PR data
            try:
                updated_pr = get_pull_request_details(pr_id)
                
                # Preserve source and draft info
                old_pr = self._prs[pr_index]
                updated_pr.source = old_pr.source
                updated_pr.isDraft = old_pr.isDraft
                
                # Fetch updated CI data
                if self.repository:
                    ci_data = self._ci_manager.get_ci_data(self.repository, pr_id)
                    if ci_data:
                        updated_pr.ci_data = ci_data
                        self._integrate_ci_checks(updated_pr, ci_data)
                    else:
                        updated_pr.ci_data = None
                
                # Replace the PR in our list
                self._prs[pr_index] = updated_pr
                
                # Update cache
                if self._cache_manager:
                    self._update_cache_for_pr(updated_pr)
                
                # Notify callbacks
                update = TUIDataUpdate(
                    timestamp=datetime.now(),
                    update_type='pr_update',
                    data=updated_pr,
                    pr_id=pr_id
                )
                self._notify_callbacks(update)
                
            except Exception:
                # If refresh fails, keep the old data
                pass
        
        return self._prs.copy()
    
    async def _refresh_all_prs(self) -> List[PullRequest]:
        """Refresh data for all PRs."""
        # For efficiency, we'll check which PRs have changed
        # and only update those that need it
        with self._update_lock:
            updated_prs = []
            for pr in self._prs:
                try:
                    # Get basic PR info to check if it's changed
                    updated_pr = get_pull_request_details(pr.id)
                    
                    # Check if we need to update (compare updated_at)
                    if (updated_pr.updated_at != pr.updated_at or 
                        not hasattr(pr, 'ci_data') or 
                        pr.ci_data is None):
                        
                        # Preserve source and draft info
                        updated_pr.source = pr.source
                        updated_pr.isDraft = pr.isDraft
                        
                        # Fetch CI data
                        if self.repository:
                            ci_data = self._ci_manager.get_ci_data(self.repository, pr.id)
                            if ci_data:
                                updated_pr.ci_data = ci_data
                                self._integrate_ci_checks(updated_pr, ci_data)
                            else:
                                updated_pr.ci_data = None
                        
                        updated_prs.append(updated_pr)
                        
                        # Update cache
                        if self._cache_manager:
                            self._update_cache_for_pr(updated_pr)
                    else:
                        updated_prs.append(pr)
                        
                except Exception:
                    # If update fails, keep the old PR
                    updated_prs.append(pr)
            
            self._prs = updated_prs
            self._last_update = datetime.now()
        
        update = TUIDataUpdate(
            timestamp=self._last_update,
            update_type='refresh',
            data=self._prs.copy()
        )
        self._notify_callbacks(update)
        
        return self._prs.copy()
    
    def get_prs(self) -> List[PullRequest]:
        """Get current PR data."""
        with self._update_lock:
            return self._prs.copy()
    
    def get_pr_by_id(self, pr_id: int) -> Optional[PullRequest]:
        """Get a specific PR by ID."""
        with self._update_lock:
            for pr in self._prs:
                if pr.id == pr_id:
                    return pr
            return None
    
    def start_auto_refresh(self, interval: int = 30):
        """Start automatic data refresh."""
        self._refresh_interval = interval
        self._auto_refresh = True
        self._schedule_refresh()
    
    def stop_auto_refresh(self):
        """Stop automatic data refresh."""
        self._auto_refresh = False
        if self._refresh_timer:
            self._refresh_timer.cancel()
            self._refresh_timer = None
    
    def _schedule_refresh(self):
        """Schedule the next refresh."""
        if not self._auto_refresh:
            return
        
        if self._refresh_timer:
            self._refresh_timer.cancel()
        
        self._refresh_timer = threading.Timer(
            self._refresh_interval,
            self._auto_refresh_callback
        )
        self._refresh_timer.start()
    
    def _auto_refresh_callback(self):
        """Callback for automatic refresh."""
        if self._auto_refresh:
            # Run refresh in a separate thread to avoid blocking
            def refresh_thread():
                try:
                    asyncio.run(self._refresh_all_prs())
                except Exception:
                    pass
                finally:
                    self._schedule_refresh()
            
            threading.Thread(target=refresh_thread, daemon=True).start()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about current data."""
        with self._update_lock:
            stats = {
                'total_prs': len(self._prs),
                'draft_prs': sum(1 for pr in self._prs if pr.isDraft),
                'last_update': self._last_update,
                'auto_refresh': self._auto_refresh,
                'refresh_interval': self._refresh_interval
            }
            
            # CI stats
            ci_stats = {
                'prs_with_ci': 0,
                'passing_ci': 0,
                'failing_ci': 0,
                'pending_ci': 0
            }
            
            for pr in self._prs:
                if hasattr(pr, 'ci_data') and pr.ci_data:
                    ci_stats['prs_with_ci'] += 1
                    if pr.ci_data.failed_workflows > 0:
                        ci_stats['failing_ci'] += 1
                    elif pr.ci_data.pending_workflows > 0:
                        ci_stats['pending_ci'] += 1
                    elif pr.ci_data.successful_workflows > 0:
                        ci_stats['passing_ci'] += 1
            
            stats['ci_stats'] = ci_stats
            
            return stats
    
    def cleanup(self):
        """Clean up resources."""
        self.stop_auto_refresh()
        self._update_callbacks.clear()