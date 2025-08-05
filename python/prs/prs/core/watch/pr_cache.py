"""
PR State Cache System

Manages caching and comparison of PR states for efficient change detection.
"""

from typing import Dict, List, Optional, Set
from datetime import datetime
import logging

from .watch_types import PRSnapshot, ChangeSet, Change, ChangeType, WatchConfig


class PRStateCache:
    """
    Manages caching of PR states and efficient change detection.
    
    Uses hash-based comparison for performance with large PR lists.
    """
    
    def __init__(self, config: WatchConfig):
        self.config = config
        self.snapshots: Dict[str, PRSnapshot] = {}
        self.snapshot_history: List[Dict[str, PRSnapshot]] = []
        self.logger = logging.getLogger(__name__)
    
    def store_snapshot(self, prs: List) -> None:
        """Store a new snapshot of PR states."""
        new_snapshots = {}
        
        for pr in prs:
            snapshot = PRSnapshot.from_pr(pr)
            new_snapshots[snapshot.id] = snapshot
        
        # Store current snapshots as history before replacing
        if self.snapshots:
            self.snapshot_history.append(self.snapshots.copy())
        
        # Limit history size to prevent memory bloat
        if len(self.snapshot_history) > 10:
            self.snapshot_history.pop(0)
        
        self.snapshots = new_snapshots
        self.logger.debug(f"Stored snapshot with {len(new_snapshots)} PRs")
    
    def detect_changes(self, new_prs: List) -> ChangeSet:
        """
        Detect changes between current cached state and new PR data.
        
        Returns ChangeSet with all detected changes.
        """
        if not self.snapshots:
            # First run - everything is "new"
            self.store_snapshot(new_prs)
            return ChangeSet(
                changes=[],
                new_prs=[pr.id for pr in new_prs],
                removed_prs=[],
                timestamp=datetime.now().strftime("%H:%M:%S")
            )
        
        # Create new snapshots for comparison
        new_snapshots = {PRSnapshot.from_pr(pr).id: PRSnapshot.from_pr(pr) for pr in new_prs}
        
        changes = []
        new_pr_ids = []
        removed_pr_ids = []
        
        # Find new and changed PRs
        for pr_id, new_snapshot in new_snapshots.items():
            if pr_id not in self.snapshots:
                # New PR
                new_pr_ids.append(pr_id)
            else:
                # Check for changes in existing PR
                old_snapshot = self.snapshots[pr_id]
                pr_changes = self._compare_snapshots(old_snapshot, new_snapshot)
                changes.extend(pr_changes)
        
        # Find removed PRs
        for pr_id in self.snapshots:
            if pr_id not in new_snapshots:
                removed_pr_ids.append(pr_id)
        
        # Store the new snapshots
        self.store_snapshot(new_prs)
        
        return ChangeSet(
            changes=changes,
            new_prs=new_pr_ids,
            removed_prs=removed_pr_ids,
            timestamp=datetime.now().strftime("%H:%M:%S")
        )
    
    def _compare_snapshots(self, old: PRSnapshot, new: PRSnapshot) -> List[Change]:
        """Compare two snapshots and return list of changes."""
        changes = []
        
        # Quick hash comparison first
        if old.hash == new.hash:
            return changes  # No changes
        
        # Detailed comparison for specific changes
        if old.status != new.status:
            changes.append(Change(
                pr_id=new.id,
                change_type=ChangeType.STATUS_CHANGE,
                old_value=old.status,
                new_value=new.status,
                description=f"Status changed from {old.status} to {new.status}"
            ))
        
        if old.checks_summary != new.checks_summary:
            changes.append(Change(
                pr_id=new.id,
                change_type=ChangeType.CHECKS_CHANGE,
                old_value=old.checks_summary,
                new_value=new.checks_summary,
                description=f"Checks changed from {old.checks_summary} to {new.checks_summary}"
            ))
        
        if old.reviews_summary != new.reviews_summary:
            changes.append(Change(
                pr_id=new.id,
                change_type=ChangeType.REVIEWS_CHANGE,
                old_value=old.reviews_summary,
                new_value=new.reviews_summary,
                description=f"Reviews changed from {old.reviews_summary} to {new.reviews_summary}"
            ))
        
        if old.labels_summary != new.labels_summary:
            changes.append(Change(
                pr_id=new.id,
                change_type=ChangeType.LABELS_CHANGE,
                old_value=old.labels_summary,
                new_value=new.labels_summary,
                description=f"Labels changed from {old.labels_summary} to {new.labels_summary}"
            ))
        
        return changes
    
    def get_last_snapshot(self) -> Optional[Dict[str, PRSnapshot]]:
        """Get the most recent snapshot."""
        return self.snapshots.copy() if self.snapshots else None
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self.snapshots.clear()
        self.snapshot_history.clear()
        self.logger.debug("Cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "current_prs": len(self.snapshots),
            "history_entries": len(self.snapshot_history),
            "total_memory_entries": len(self.snapshots) + sum(len(h) for h in self.snapshot_history)
        }