"""
Real-time CI status streaming service for PRS TUI.
Provides live updates for CI status changes with smart polling and notifications.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import logging

from textual.message import Message

from ...ci_tools.base.models import CICheck, BuildStatus, CIProvider
from ...ci_tools.github_actions.provider import GitHubActionsProvider
from ...cache.ci_manager import CICacheManager
from ..events.events import CIStatusUpdateEvent, PRUpdateEvent


class PollStrategy(Enum):
    """Polling strategy for CI status updates."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    FIXED_INTERVAL = "fixed_interval"
    SMART_ADAPTIVE = "smart_adaptive"


@dataclass
class CIWatchConfig:
    """Configuration for CI watching."""
    provider: CIProvider
    repo_owner: str
    repo_name: str
    pr_ids: Set[int] = field(default_factory=set)
    poll_interval: int = 30  # seconds
    max_poll_interval: int = 300  # 5 minutes
    strategy: PollStrategy = PollStrategy.SMART_ADAPTIVE
    priority: int = 1  # 1=high, 2=medium, 3=low


@dataclass
class CIStatusSnapshot:
    """Snapshot of CI status at a point in time."""
    pr_id: int
    timestamp: datetime
    checks: List[CICheck]
    overall_status: BuildStatus
    changed_from_previous: bool = False


class RealtimeCIService:
    """
    Real-time CI status streaming service.
    
    Provides live updates for CI status changes with:
    - Smart polling with exponential backoff
    - Priority-based update scheduling
    - Change detection and notifications
    - WebSocket-like live updates
    """
    
    def __init__(self, cache_manager: CICacheManager):
        self.cache_manager = cache_manager
        self.github_provider = GitHubActionsProvider()
        
        # Service state
        self.running = False
        self.watch_configs: Dict[str, CIWatchConfig] = {}
        self.last_snapshots: Dict[int, CIStatusSnapshot] = {}
        
        # Event callbacks
        self.status_update_callbacks: List[Callable[[CIStatusUpdateEvent], None]] = []
        self.pr_update_callbacks: List[Callable[[PRUpdateEvent], None]] = []
        
        # Performance tracking
        self.poll_history: Dict[str, List[datetime]] = {}
        self.error_counts: Dict[str, int] = {}
        
        # Smart polling state
        self.active_prs: Set[int] = set()  # PRs with pending builds
        self.stable_prs: Set[int] = set()  # PRs with stable status
        
        self.logger = logging.getLogger(__name__)
    
    def add_status_update_callback(self, callback: Callable[[CIStatusUpdateEvent], None]):
        """Add callback for CI status updates."""
        self.status_update_callbacks.append(callback)
    
    def add_pr_update_callback(self, callback: Callable[[PRUpdateEvent], None]):
        """Add callback for PR updates."""
        self.pr_update_callbacks.append(callback)
    
    def watch_repository(self, repo_owner: str, repo_name: str, 
                        pr_ids: Optional[Set[int]] = None,
                        poll_interval: int = 30,
                        strategy: PollStrategy = PollStrategy.SMART_ADAPTIVE,
                        priority: int = 1):
        """
        Start watching a repository for CI status changes.
        
        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            pr_ids: Specific PR IDs to watch (None for all)
            poll_interval: Base polling interval in seconds
            strategy: Polling strategy to use
            priority: Priority level (1=high, 2=medium, 3=low)
        """
        config_key = f"{repo_owner}/{repo_name}"
        
        config = CIWatchConfig(
            provider=CIProvider.GITHUB_ACTIONS,
            repo_owner=repo_owner,
            repo_name=repo_name,
            pr_ids=pr_ids or set(),
            poll_interval=poll_interval,
            strategy=strategy,
            priority=priority
        )
        
        self.watch_configs[config_key] = config
        self.logger.info(f"Started watching {config_key} with {strategy.value} strategy")
    
    def stop_watching(self, repo_owner: str, repo_name: str):
        """Stop watching a repository."""
        config_key = f"{repo_owner}/{repo_name}"
        if config_key in self.watch_configs:
            del self.watch_configs[config_key]
            self.logger.info(f"Stopped watching {config_key}")
    
    def update_pr_list(self, pr_ids: Set[int]):
        """Update the list of PRs to watch."""
        for config in self.watch_configs.values():
            config.pr_ids = pr_ids
    
    async def start(self):
        """Start the real-time CI service."""
        self.running = True
        self.logger.info("Starting real-time CI service")
        
        # Start polling tasks for each watch config
        tasks = []
        for config_key, config in self.watch_configs.items():
            task = asyncio.create_task(self._poll_repository(config_key, config))
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def stop(self):
        """Stop the real-time CI service."""
        self.running = False
        self.logger.info("Stopping real-time CI service")
    
    async def _poll_repository(self, config_key: str, config: CIWatchConfig):
        """Poll a repository for CI status changes."""
        consecutive_errors = 0
        last_poll_time = datetime.now()
        
        while self.running:
            try:
                # Calculate next poll interval based on strategy
                poll_interval = self._calculate_poll_interval(
                    config, consecutive_errors, last_poll_time
                )
                
                # Wait for the calculated interval
                await asyncio.sleep(poll_interval)
                
                # Get PR IDs to check
                pr_ids = config.pr_ids if config.pr_ids else await self._get_all_pr_ids(config)
                
                # Check CI status for each PR
                for pr_id in pr_ids:
                    await self._check_pr_ci_status(config, pr_id)
                
                # Update polling history
                self._update_poll_history(config_key)
                last_poll_time = datetime.now()
                consecutive_errors = 0
                
            except Exception as e:
                consecutive_errors += 1
                self.error_counts[config_key] = self.error_counts.get(config_key, 0) + 1
                
                self.logger.error(f"Error polling {config_key}: {e}")
                
                # Exponential backoff on errors
                error_delay = min(30 * (2 ** consecutive_errors), 300)
                await asyncio.sleep(error_delay)
    
    def _calculate_poll_interval(self, config: CIWatchConfig, 
                               consecutive_errors: int, 
                               last_poll_time: datetime) -> int:
        """Calculate the next poll interval based on strategy."""
        base_interval = config.poll_interval
        
        if config.strategy == PollStrategy.FIXED_INTERVAL:
            return base_interval
        
        elif config.strategy == PollStrategy.EXPONENTIAL_BACKOFF:
            # Exponential backoff for stable PRs
            if consecutive_errors > 0:
                return min(base_interval * (2 ** consecutive_errors), config.max_poll_interval)
            return base_interval
        
        elif config.strategy == PollStrategy.SMART_ADAPTIVE:
            # Smart adaptive polling based on PR activity
            active_prs_count = len(self.active_prs.intersection(config.pr_ids))
            stable_prs_count = len(self.stable_prs.intersection(config.pr_ids))
            
            if active_prs_count > 0:
                # Faster polling for active PRs
                return max(base_interval // 2, 10)
            elif stable_prs_count > 0:
                # Slower polling for stable PRs
                return min(base_interval * 2, config.max_poll_interval)
            else:
                # Default interval
                return base_interval
        
        return base_interval
    
    async def _get_all_pr_ids(self, config: CIWatchConfig) -> Set[int]:
        """Get all PR IDs for a repository."""
        # This would integrate with the existing PR fetching logic
        # For now, return empty set as placeholder
        return set()
    
    async def _check_pr_ci_status(self, config: CIWatchConfig, pr_id: int):
        """Check CI status for a specific PR."""
        try:
            # Get current CI status
            checks = self.github_provider.get_pr_checks(
                pr_id, config.repo_owner, config.repo_name
            )
            
            # Determine overall status
            overall_status = self._determine_overall_status(checks)
            
            # Create snapshot
            snapshot = CIStatusSnapshot(
                pr_id=pr_id,
                timestamp=datetime.now(),
                checks=checks,
                overall_status=overall_status
            )
            
            # Check for changes
            previous_snapshot = self.last_snapshots.get(pr_id)
            if previous_snapshot:
                snapshot.changed_from_previous = self._has_status_changed(
                    previous_snapshot, snapshot
                )
            else:
                snapshot.changed_from_previous = True
            
            # Update snapshot
            self.last_snapshots[pr_id] = snapshot
            
            # Update active/stable PR sets
            self._update_pr_activity_status(pr_id, overall_status)
            
            # Send notifications if changed
            if snapshot.changed_from_previous:
                await self._notify_status_change(snapshot)
            
            # Update cache
            await self._update_cache(config, pr_id, checks)
            
        except Exception as e:
            self.logger.error(f"Error checking CI status for PR {pr_id}: {e}")
    
    def _determine_overall_status(self, checks: List[CICheck]) -> BuildStatus:
        """Determine overall build status from individual checks."""
        if not checks:
            return BuildStatus.UNKNOWN
        
        # Check for any failing checks
        for check in checks:
            if check.status == BuildStatus.FAILED:
                return BuildStatus.FAILED
        
        # Check for any pending checks
        for check in checks:
            if check.status == BuildStatus.PENDING:
                return BuildStatus.PENDING
        
        # All checks passed
        return BuildStatus.PASSED
    
    def _has_status_changed(self, previous: CIStatusSnapshot, 
                           current: CIStatusSnapshot) -> bool:
        """Check if CI status has changed between snapshots."""
        # Check overall status change
        if previous.overall_status != current.overall_status:
            return True
        
        # Check individual check changes
        prev_checks = {check.name: check.status for check in previous.checks}
        curr_checks = {check.name: check.status for check in current.checks}
        
        return prev_checks != curr_checks
    
    def _update_pr_activity_status(self, pr_id: int, status: BuildStatus):
        """Update PR activity status for smart polling."""
        if status == BuildStatus.PENDING:
            self.active_prs.add(pr_id)
            self.stable_prs.discard(pr_id)
        else:
            self.active_prs.discard(pr_id)
            self.stable_prs.add(pr_id)
    
    async def _notify_status_change(self, snapshot: CIStatusSnapshot):
        """Send notifications for status changes."""
        # Create CI status update event
        ci_event = CIStatusUpdateEvent(
            pr_id=snapshot.pr_id,
            timestamp=snapshot.timestamp,
            status=snapshot.overall_status,
            checks=snapshot.checks
        )
        
        # Notify all callbacks
        for callback in self.status_update_callbacks:
            try:
                callback(ci_event)
            except Exception as e:
                self.logger.error(f"Error in status update callback: {e}")
        
        # Create PR update event
        pr_event = PRUpdateEvent(
            pr_id=snapshot.pr_id,
            timestamp=snapshot.timestamp,
            update_type="ci_status",
            data={"status": snapshot.overall_status, "checks": snapshot.checks}
        )
        
        # Notify PR update callbacks
        for callback in self.pr_update_callbacks:
            try:
                callback(pr_event)
            except Exception as e:
                self.logger.error(f"Error in PR update callback: {e}")
    
    async def _update_cache(self, config: CIWatchConfig, pr_id: int, checks: List[CICheck]):
        """Update cache with latest CI data."""
        try:
            # Store in cache
            cache_data = {
                "pr_id": pr_id,
                "repo": f"{config.repo_owner}/{config.repo_name}",
                "checks": [check.__dict__ for check in checks],
                "timestamp": datetime.now().isoformat()
            }
            
            # Use existing cache manager
            self.cache_manager.store_build(pr_id, cache_data)
            
        except Exception as e:
            self.logger.error(f"Error updating cache for PR {pr_id}: {e}")
    
    def _update_poll_history(self, config_key: str):
        """Update polling history for performance tracking."""
        if config_key not in self.poll_history:
            self.poll_history[config_key] = []
        
        self.poll_history[config_key].append(datetime.now())
        
        # Keep only last 100 entries
        self.poll_history[config_key] = self.poll_history[config_key][-100:]
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get service performance statistics."""
        stats = {
            "running": self.running,
            "watched_repositories": len(self.watch_configs),
            "active_prs": len(self.active_prs),
            "stable_prs": len(self.stable_prs),
            "total_snapshots": len(self.last_snapshots),
            "error_counts": dict(self.error_counts),
            "polling_history": {}
        }
        
        # Add polling frequency stats
        for config_key, history in self.poll_history.items():
            if len(history) > 1:
                recent_history = history[-10:]  # Last 10 polls
                intervals = [
                    (recent_history[i] - recent_history[i-1]).total_seconds()
                    for i in range(1, len(recent_history))
                ]
                if intervals:
                    stats["polling_history"][config_key] = {
                        "avg_interval": sum(intervals) / len(intervals),
                        "last_poll": history[-1].isoformat(),
                        "poll_count": len(history)
                    }
        
        return stats
    
    def force_refresh(self, pr_id: Optional[int] = None):
        """Force immediate refresh of CI status."""
        if pr_id:
            # Force refresh specific PR
            self.active_prs.add(pr_id)
            self.stable_prs.discard(pr_id)
        else:
            # Force refresh all PRs
            for config in self.watch_configs.values():
                self.active_prs.update(config.pr_ids)
                self.stable_prs.clear()
    
    def get_latest_snapshot(self, pr_id: int) -> Optional[CIStatusSnapshot]:
        """Get the latest CI status snapshot for a PR."""
        return self.last_snapshots.get(pr_id)
    
    def get_pr_activity_level(self, pr_id: int) -> str:
        """Get activity level for a PR (active, stable, unknown)."""
        if pr_id in self.active_prs:
            return "active"
        elif pr_id in self.stable_prs:
            return "stable"
        else:
            return "unknown"