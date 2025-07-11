"""
TUI-specific data models for the PRS application.

These models provide reactive data binding, caching, and state management
for the terminal user interface components.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable, Set
from enum import Enum
import time
from datetime import datetime, timedelta

from ...core.models import PullRequest


class SortOrder(Enum):
    """Sort order for PR lists."""
    ASC = "asc"
    DESC = "desc"


class SortField(Enum):
    """Available sort fields for PR lists."""
    NUMBER = "number"
    TITLE = "title"
    AUTHOR = "author"
    STATUS = "status"
    CREATED = "created"
    UPDATED = "updated"
    CHECKS = "checks"
    REVIEWS = "reviews"


class PRStatus(Enum):
    """Overall PR status based on checks and reviews."""
    HEALTHY = "healthy"        # All checks pass, approved
    WARNING = "warning"        # Some issues but not critical
    CRITICAL = "critical"      # Failing checks or blocked
    PENDING = "pending"        # Checks running or awaiting review
    DRAFT = "draft"           # Draft PR


class TabType(Enum):
    """Available tabs in PR detail view."""
    OVERVIEW = "overview"
    CHECKS = "checks"
    REVIEWS = "reviews"
    COMMENTS = "comments"
    COMMITS = "commits"
    FILES = "files"


@dataclass
class PRHealth:
    """Health status indicators for a PR."""
    checks_passing: int = 0
    checks_failing: int = 0
    checks_pending: int = 0
    reviews_approved: int = 0
    reviews_requested: int = 0
    reviews_changes: int = 0
    
    @property
    def status(self) -> PRStatus:
        """Calculate overall PR status."""
        if self.checks_failing > 0:
            return PRStatus.CRITICAL
        if self.checks_pending > 0:
            return PRStatus.PENDING
        if self.reviews_changes > 0:
            return PRStatus.WARNING
        if self.checks_passing > 0 and self.reviews_approved > 0:
            return PRStatus.HEALTHY
        return PRStatus.PENDING
    
    @property
    def health_dots(self) -> str:
        """Generate health dots representation (●●●, ●●○, ●○○, ●××)."""
        if self.status == PRStatus.HEALTHY:
            return "●●●"
        elif self.status == PRStatus.WARNING:
            return "●●○"
        elif self.status == PRStatus.PENDING:
            return "●○○"
        else:  # CRITICAL
            return "●××"


@dataclass
class PRListItem:
    """Enhanced PR data for list display."""
    pr: PullRequest
    health: PRHealth = field(default_factory=PRHealth)
    cached_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Calculate health after initialization."""
        self._calculate_health()
    
    def _calculate_health(self):
        """Calculate health metrics from PR data."""
        # Reset counters
        self.health = PRHealth()
        
        # Calculate check status
        for check in self.pr.checks:
            status = check.get('conclusion', check.get('status', 'pending')).lower()
            if status in ['success', 'passed']:
                self.health.checks_passing += 1
            elif status in ['failure', 'failed', 'error']:
                self.health.checks_failing += 1
            else:
                self.health.checks_pending += 1
        
        # Calculate review status
        for review in self.pr.reviews:
            state = review.get('state', '').lower()
            if state == 'approved':
                self.health.reviews_approved += 1
            elif state == 'changes_requested':
                self.health.reviews_changes += 1
            elif state == 'review_requested':
                self.health.reviews_requested += 1
    
    @property
    def is_stale(self, max_age_minutes: int = 5) -> bool:
        """Check if cached data is stale."""
        return datetime.now() - self.cached_at > timedelta(minutes=max_age_minutes)


@dataclass
class PRSelection:
    """Manages PR selection state."""
    selected_indices: Set[int] = field(default_factory=set)
    focused_index: int = 0
    multi_select_mode: bool = False
    
    def toggle_selection(self, index: int):
        """Toggle selection for an index."""
        if index in self.selected_indices:
            self.selected_indices.remove(index)
        else:
            self.selected_indices.add(index)
    
    def select_range(self, start: int, end: int):
        """Select a range of indices."""
        for i in range(min(start, end), max(start, end) + 1):
            self.selected_indices.add(i)
    
    def clear_selection(self):
        """Clear all selections."""
        self.selected_indices.clear()
    
    def is_selected(self, index: int) -> bool:
        """Check if index is selected."""
        return index in self.selected_indices


@dataclass
class FilterState:
    """Filter state for PR lists."""
    search_query: str = ""
    author_filter: str = ""
    label_filters: List[str] = field(default_factory=list)
    status_filters: List[PRStatus] = field(default_factory=list)
    show_drafts: bool = True
    show_merged: bool = False
    
    def matches_pr(self, pr_item: PRListItem) -> bool:
        """Check if PR matches current filters."""
        pr = pr_item.pr
        
        # Search query
        if self.search_query:
            query_lower = self.search_query.lower()
            if not (query_lower in pr.title.lower() or 
                   query_lower in pr.author.lower() or
                   query_lower in str(pr.id)):
                return False
        
        # Author filter
        if self.author_filter and self.author_filter.lower() not in pr.author.lower():
            return False
        
        # Label filters
        if self.label_filters:
            pr_labels = [label.lower() for label in pr.labels]
            if not any(filter_label.lower() in pr_labels for filter_label in self.label_filters):
                return False
        
        # Status filters
        if self.status_filters and pr_item.health.status not in self.status_filters:
            return False
        
        # Draft filter
        if not self.show_drafts and pr.is_draft:
            return False
        
        # Merged filter
        if not self.show_merged and pr.merged:
            return False
        
        return True


@dataclass
class SortState:
    """Sort state for PR lists."""
    field: SortField = SortField.UPDATED
    order: SortOrder = SortOrder.DESC
    
    def sort_key(self, pr_item: PRListItem) -> Any:
        """Get sort key for a PR item."""
        pr = pr_item.pr
        
        if self.field == SortField.NUMBER:
            return pr.id
        elif self.field == SortField.TITLE:
            return pr.title.lower()
        elif self.field == SortField.AUTHOR:
            return pr.author.lower()
        elif self.field == SortField.STATUS:
            return pr_item.health.status.value
        elif self.field == SortField.CREATED:
            return pr.created_at or ""
        elif self.field == SortField.UPDATED:
            return pr.updated_at or ""
        elif self.field == SortField.CHECKS:
            return pr_item.health.checks_passing - pr_item.health.checks_failing
        elif self.field == SortField.REVIEWS:
            return pr_item.health.reviews_approved
        
        return ""


@dataclass
class DetailViewState:
    """State for PR detail view."""
    active_tab: TabType = TabType.OVERVIEW
    expanded_sections: Set[str] = field(default_factory=set)
    scroll_positions: Dict[TabType, int] = field(default_factory=dict)
    
    def toggle_section(self, section_name: str):
        """Toggle expansion of a section."""
        if section_name in self.expanded_sections:
            self.expanded_sections.remove(section_name)
        else:
            self.expanded_sections.add(section_name)
    
    def is_expanded(self, section_name: str) -> bool:
        """Check if section is expanded."""
        return section_name in self.expanded_sections


@dataclass
class CacheEntry:
    """Cache entry for PR data."""
    data: Any
    timestamp: datetime = field(default_factory=datetime.now)
    ttl_seconds: int = 300  # 5 minutes default
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return datetime.now() - self.timestamp > timedelta(seconds=self.ttl_seconds)


class DataCache:
    """Simple in-memory cache for PR data."""
    
    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached data if not expired."""
        entry = self._cache.get(key)
        if entry and not entry.is_expired:
            return entry.data
        elif entry:
            # Remove expired entry
            del self._cache[key]
        return None
    
    def set(self, key: str, data: Any, ttl_seconds: int = 300):
        """Set cached data with TTL."""
        self._cache[key] = CacheEntry(data=data, ttl_seconds=ttl_seconds)
    
    def invalidate(self, key: str):
        """Invalidate specific cache entry."""
        self._cache.pop(key, None)
    
    def clear(self):
        """Clear all cache entries."""
        self._cache.clear()


@dataclass
class TUIState:
    """Main state container for the TUI application."""
    pr_items: List[PRListItem] = field(default_factory=list)
    selection: PRSelection = field(default_factory=PRSelection)
    filter_state: FilterState = field(default_factory=FilterState)
    sort_state: SortState = field(default_factory=SortState)
    detail_state: DetailViewState = field(default_factory=DetailViewState)
    cache: DataCache = field(default_factory=DataCache)
    
    # UI state
    show_detail_panel: bool = True
    detail_panel_width: int = 60
    list_panel_height: int = 20
    
    # Update callbacks
    _update_callbacks: List[Callable] = field(default_factory=list)
    
    def add_update_callback(self, callback: Callable):
        """Add callback to be called on state updates."""
        self._update_callbacks.append(callback)
    
    def notify_update(self):
        """Notify all callbacks of state update."""
        for callback in self._update_callbacks:
            try:
                callback()
            except Exception:
                pass  # Ignore callback errors
    
    def get_filtered_sorted_items(self) -> List[PRListItem]:
        """Get filtered and sorted PR items."""
        # Filter items
        filtered = [item for item in self.pr_items if self.filter_state.matches_pr(item)]
        
        # Sort items
        reverse = self.sort_state.order == SortOrder.DESC
        sorted_items = sorted(filtered, key=self.sort_state.sort_key, reverse=reverse)
        
        return sorted_items
    
    def get_selected_pr(self) -> Optional[PullRequest]:
        """Get currently focused PR."""
        filtered_items = self.get_filtered_sorted_items()
        if 0 <= self.selection.focused_index < len(filtered_items):
            return filtered_items[self.selection.focused_index].pr
        return None
    
    def update_pr_data(self, prs: List[PullRequest]):
        """Update PR data and refresh health calculations."""
        # Convert to PR items and preserve selection state
        old_focused_pr_id = None
        if self.pr_items and 0 <= self.selection.focused_index < len(self.pr_items):
            old_focused_pr_id = self.pr_items[self.selection.focused_index].pr.id
        
        self.pr_items = [PRListItem(pr=pr) for pr in prs]
        
        # Restore focus if possible
        if old_focused_pr_id:
            for i, item in enumerate(self.pr_items):
                if item.pr.id == old_focused_pr_id:
                    self.selection.focused_index = i
                    break
        
        # Clamp focus index
        filtered_items = self.get_filtered_sorted_items()
        if filtered_items:
            self.selection.focused_index = min(self.selection.focused_index, len(filtered_items) - 1)
        else:
            self.selection.focused_index = 0
        
        self.notify_update()
    
    def refresh_pr_health(self):
        """Refresh health calculations for all PR items."""
        for item in self.pr_items:
            item._calculate_health()
        self.notify_update()