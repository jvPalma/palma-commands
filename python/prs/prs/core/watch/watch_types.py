"""
Type definitions and interfaces for the watch system.
"""

from typing import Dict, List, Optional, Any, NamedTuple
from dataclasses import dataclass
from enum import Enum


class ChangeType(Enum):
    """Types of changes that can be detected."""
    NEW_PR = "new_pr"
    STATUS_CHANGE = "status_change"
    CHECKS_CHANGE = "checks_change"
    REVIEWS_CHANGE = "reviews_change"
    LABELS_CHANGE = "labels_change"
    PR_CLOSED = "pr_closed"
    PR_MERGED = "pr_merged"


@dataclass
class WatchConfig:
    """Configuration for watch mode."""
    interval: int = 30  # Seconds between updates
    show_update_time: bool = True
    highlight_changes: bool = True
    max_cache_size: int = 1000  # Maximum number of PR snapshots to cache


@dataclass
class PRSnapshot:
    """Serializable snapshot of a PR's state for comparison."""
    id: str
    title: str
    status: str
    checks_summary: str
    reviews_summary: str
    labels_summary: str
    last_updated: str
    hash: str  # Hash of all fields for quick comparison
    
    @classmethod
    def from_pr(cls, pr) -> 'PRSnapshot':
        """Create snapshot from PullRequest object."""
        # Create summary strings for comparison
        checks_summary = cls._create_checks_summary(pr.checks)
        reviews_summary = cls._create_reviews_summary(pr.reviews)
        labels_summary = cls._create_labels_summary(pr.labels)
        
        # Determine status based on PR properties
        status = "DRAFT" if pr.is_draft else "OPEN"
        
        # Create hash for quick comparison
        content = f"{pr.id}|{pr.title}|{status}|{checks_summary}|{reviews_summary}|{labels_summary}"
        import hashlib
        hash_value = hashlib.md5(content.encode()).hexdigest()
        
        return cls(
            id=str(pr.id),
            title=pr.title,
            status=status,
            checks_summary=checks_summary,
            reviews_summary=reviews_summary,
            labels_summary=labels_summary,
            last_updated='',  # PR model doesn't have timestamp
            hash=hash_value
        )
    
    @staticmethod
    def _create_checks_summary(checks: List[Dict]) -> str:
        """Create a summary string for checks."""
        if not checks:
            return "0/0/0"
        
        success = sum(1 for check in checks if check.get('state') == 'SUCCESS')
        pending = sum(1 for check in checks if check.get('state') == 'PENDING')
        failure = sum(1 for check in checks if check.get('state') in ['FAILURE', 'ERROR'])
        
        return f"{success}/{pending}/{failure}"
    
    @staticmethod
    def _create_reviews_summary(reviews: List[Dict]) -> str:
        """Create a summary string for reviews."""
        if not reviews:
            return "0/0/0"
        
        approved = sum(1 for review in reviews if review.get('state') == 'APPROVED')
        changes_requested = sum(1 for review in reviews if review.get('state') == 'CHANGES_REQUESTED')
        commented = sum(1 for review in reviews if review.get('state') == 'COMMENTED')
        
        return f"{approved}/{changes_requested}/{commented}"
    
    @staticmethod
    def _create_labels_summary(labels: List[str]) -> str:
        """Create a summary string for labels."""
        return ",".join(sorted(labels)) if labels else ""


class Change(NamedTuple):
    """Represents a single change detected between snapshots."""
    pr_id: str
    change_type: ChangeType
    old_value: str
    new_value: str
    description: str


@dataclass
class ChangeSet:
    """Collection of changes detected between two snapshots."""
    changes: List[Change]
    new_prs: List[str]  # IDs of newly appeared PRs
    removed_prs: List[str]  # IDs of PRs that disappeared
    timestamp: str
    
    def has_changes(self) -> bool:
        """Check if there are any changes in this set."""
        return bool(self.changes or self.new_prs or self.removed_prs)
    
    def get_changed_pr_ids(self) -> set:
        """Get set of all PR IDs that have changes."""
        changed_ids = {change.pr_id for change in self.changes}
        changed_ids.update(self.new_prs)
        return changed_ids


@dataclass
class ModeChangeCommand:
    """Command to change verbosity mode for a feature."""
    feature: str  # "checks", "reviews", "labels"
    new_mode: str  # "none", "short", "normal", "long"
    timestamp: str


@dataclass 
class WatchState:
    """Current state of the watch system."""
    is_running: bool = False
    update_count: int = 0
    last_update: Optional[str] = None
    last_error: Optional[str] = None
    connection_status: str = "disconnected"  # disconnected, connecting, connected, error