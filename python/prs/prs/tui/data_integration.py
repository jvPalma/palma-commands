"""
Data integration module for TUI application.

Provides reactive data binding, automatic updates, caching mechanisms,
and efficient handling of large PR lists with pagination/virtualization.
"""

import asyncio
import threading
import time
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from .models.tui_models import TUIState, PRListItem, DataCache
from .events.events import EventBus, Event, EventType
from ..core.models import PullRequest
from ..vc_tools.github.client import GitHubClient
from ..vc_tools.github.adapter import GitHubAdapter


@dataclass
class RefreshConfig:
    """Configuration for data refresh behavior."""
    auto_refresh_enabled: bool = True
    auto_refresh_interval: int = 300  # 5 minutes
    stale_data_threshold: int = 60    # 1 minute
    max_concurrent_requests: int = 3
    retry_attempts: int = 3
    retry_delay: int = 2


class DataProvider:
    """Handles data fetching and caching for PR information."""
    
    def __init__(self, github_client: GitHubClient, github_adapter: GitHubAdapter):
        self.github_client = github_client
        self.github_adapter = github_adapter
        self.cache = DataCache()
        
        # Request tracking
        self._active_requests: Dict[str, bool] = {}
        self._request_lock = threading.Lock()
    
    async def fetch_prs(self, query: str = "is:open is:pr", 
                       use_cache: bool = True) -> List[PullRequest]:
        """Fetch PRs with caching support."""
        cache_key = f"prs:{query}"
        
        # Check cache first
        if use_cache:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return cached_data
        
        # Prevent duplicate requests
        with self._request_lock:
            if self._active_requests.get(cache_key, False):
                # Wait for existing request
                while self._active_requests.get(cache_key, False):
                    time.sleep(0.1)
                # Try cache again
                cached_data = self.cache.get(cache_key)
                if cached_data:
                    return cached_data
            
            self._active_requests[cache_key] = True
        
        try:
            # Fetch data
            raw_prs = await self._fetch_prs_raw(query)
            prs = [self.github_adapter.to_pull_request(raw_pr) for raw_pr in raw_prs]
            
            # Cache results
            self.cache.set(cache_key, prs, ttl_seconds=300)
            
            return prs
        
        finally:
            with self._request_lock:
                self._active_requests[cache_key] = False
    
    async def _fetch_prs_raw(self, query: str) -> List[Dict[str, Any]]:
        """Fetch raw PR data from GitHub."""
        # This would be implemented to use the actual GitHub client
        # For now, return empty list as placeholder
        return []
    
    async def fetch_pr_details(self, pr_id: int, use_cache: bool = True) -> Optional[PullRequest]:
        """Fetch detailed information for a specific PR."""
        cache_key = f"pr_details:{pr_id}"
        
        if use_cache:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return cached_data
        
        try:
            # Fetch detailed PR data
            raw_pr = await self._fetch_pr_raw(pr_id)
            if raw_pr:
                pr = self.github_adapter.to_pull_request(raw_pr)
                self.cache.set(cache_key, pr, ttl_seconds=180)  # 3 minutes for details
                return pr
        except Exception:
            pass
        
        return None
    
    async def _fetch_pr_raw(self, pr_id: int) -> Optional[Dict[str, Any]]:
        """Fetch raw PR data for specific ID."""
        # Placeholder implementation
        return None
    
    def invalidate_cache(self, pattern: str = None):
        """Invalidate cache entries matching pattern."""
        if pattern:
            # Would implement pattern matching
            pass
        else:
            self.cache.clear()


class AutoRefreshManager:
    """Manages automatic data refresh in the background."""
    
    def __init__(self, data_provider: DataProvider, tui_state: TUIState, 
                 event_bus: EventBus, config: RefreshConfig):
        self.data_provider = data_provider
        self.tui_state = tui_state
        self.event_bus = event_bus
        self.config = config
        
        self._refresh_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_refresh = datetime.now()
        
    def start(self):
        """Start auto-refresh in background thread."""
        if self.config.auto_refresh_enabled and not self._refresh_thread:
            self._stop_event.clear()
            self._refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
            self._refresh_thread.start()
    
    def stop(self):
        """Stop auto-refresh."""
        if self._refresh_thread:
            self._stop_event.set()
            self._refresh_thread.join(timeout=5)
            self._refresh_thread = None
    
    def _refresh_loop(self):
        """Main refresh loop running in background thread."""
        while not self._stop_event.is_set():
            try:
                # Check if refresh is needed
                if self._should_refresh():
                    asyncio.run(self._perform_refresh())
                    self._last_refresh = datetime.now()
                
                # Wait for next check
                self._stop_event.wait(min(self.config.auto_refresh_interval, 30))
                
            except Exception as e:
                # Log error and continue
                error_event = Event(
                    type=EventType.DATA_REFRESH,
                    data={"error": str(e), "component": "auto_refresh"},
                    source="auto_refresh_manager"
                )
                self.event_bus.emit(error_event)
                
                # Wait before retrying
                self._stop_event.wait(self.config.retry_delay)
    
    def _should_refresh(self) -> bool:
        """Check if data should be refreshed."""
        time_since_refresh = datetime.now() - self._last_refresh
        return time_since_refresh.total_seconds() >= self.config.auto_refresh_interval
    
    async def _perform_refresh(self):
        """Perform data refresh."""
        try:
            # Emit refresh start event
            start_event = Event(
                type=EventType.DATA_REFRESH,
                data={"status": "started", "component": "auto_refresh"},
                source="auto_refresh_manager"
            )
            self.event_bus.emit(start_event)
            
            # Fetch fresh data
            prs = await self.data_provider.fetch_prs(use_cache=False)
            
            # Update TUI state
            self.tui_state.update_pr_data(prs)
            
            # Emit refresh complete event
            complete_event = Event(
                type=EventType.DATA_REFRESH,
                data={"status": "completed", "count": len(prs), "component": "auto_refresh"},
                source="auto_refresh_manager"
            )
            self.event_bus.emit(complete_event)
            
        except Exception as e:
            # Emit error event
            error_event = Event(
                type=EventType.DATA_REFRESH,
                data={"status": "error", "error": str(e), "component": "auto_refresh"},
                source="auto_refresh_manager"
            )
            self.event_bus.emit(error_event)


class PaginationManager:
    """Manages pagination and virtualization for large PR lists."""
    
    def __init__(self, page_size: int = 100):
        self.page_size = page_size
        self.current_page = 0
        self.total_items = 0
        self.has_more = True
        
        # Virtualization settings
        self.virtual_buffer_size = 50  # Items to keep in memory outside visible area
        
    def get_page_info(self) -> Dict[str, Any]:
        """Get current pagination information."""
        return {
            "current_page": self.current_page,
            "page_size": self.page_size,
            "total_items": self.total_items,
            "has_more": self.has_more,
            "total_pages": (self.total_items + self.page_size - 1) // self.page_size
        }
    
    def calculate_visible_range(self, scroll_position: int, 
                              visible_count: int) -> tuple[int, int]:
        """Calculate range of items that should be loaded for virtualization."""
        start = max(0, scroll_position - self.virtual_buffer_size)
        end = min(self.total_items, scroll_position + visible_count + self.virtual_buffer_size)
        return start, end
    
    def needs_more_data(self, current_items_count: int, 
                       scroll_position: int, visible_count: int) -> bool:
        """Check if more data needs to be loaded."""
        if not self.has_more:
            return False
        
        # Load more if scrolling near the end
        buffer_threshold = visible_count * 2
        return (scroll_position + visible_count + buffer_threshold) >= current_items_count


class ReactiveDataBinding:
    """Provides reactive data binding with automatic UI updates."""
    
    def __init__(self, tui_state: TUIState, event_bus: EventBus):
        self.tui_state = tui_state
        self.event_bus = event_bus
        self._update_callbacks: List[Callable] = []
        
        # Setup state change listeners
        self.tui_state.add_update_callback(self._on_state_update)
    
    def add_update_callback(self, callback: Callable):
        """Add callback for UI updates."""
        self._update_callbacks.append(callback)
    
    def remove_update_callback(self, callback: Callable):
        """Remove update callback."""
        try:
            self._update_callbacks.remove(callback)
        except ValueError:
            pass
    
    def _on_state_update(self):
        """Handle state updates and notify UI components."""
        # Emit update event
        update_event = Event(
            type=EventType.DATA_REFRESH,
            data={"status": "state_updated", "component": "reactive_binding"},
            source="reactive_data_binding"
        )
        self.event_bus.emit(update_event)
        
        # Notify UI callbacks
        for callback in self._update_callbacks:
            try:
                callback()
            except Exception:
                pass  # Ignore callback errors
    
    def bind_filter_changes(self):
        """Setup automatic filter change notifications."""
        # This would set up watchers for filter state changes
        pass
    
    def bind_sort_changes(self):
        """Setup automatic sort change notifications."""
        # This would set up watchers for sort state changes
        pass


class DataIntegrationManager:
    """Main manager for all data integration features."""
    
    def __init__(self, github_client: GitHubClient, github_adapter: GitHubAdapter,
                 tui_state: TUIState, event_bus: EventBus, 
                 config: RefreshConfig = None):
        
        self.config = config or RefreshConfig()
        
        # Components
        self.data_provider = DataProvider(github_client, github_adapter)
        self.tui_state = tui_state
        self.event_bus = event_bus
        
        # Managers
        self.auto_refresh = AutoRefreshManager(
            self.data_provider, tui_state, event_bus, self.config
        )
        self.pagination = PaginationManager()
        self.reactive_binding = ReactiveDataBinding(tui_state, event_bus)
        
        # State
        self._initial_load_complete = False
        
        # Setup event handlers
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Setup event handlers for data operations."""
        self.event_bus.subscribe(EventType.DATA_REFRESH, self._handle_refresh_request)
        self.event_bus.subscribe(EventType.FILTER_CHANGE, self._handle_filter_change)
        self.event_bus.subscribe(EventType.SORT_CHANGE, self._handle_sort_change)
    
    async def initialize(self):
        """Initialize data integration and perform initial load."""
        try:
            # Emit initialization start
            init_event = Event(
                type=EventType.DATA_REFRESH,
                data={"status": "initializing", "component": "data_integration"},
                source="data_integration_manager"
            )
            self.event_bus.emit(init_event)
            
            # Initial data load
            prs = await self.data_provider.fetch_prs()
            self.tui_state.update_pr_data(prs)
            
            # Start auto-refresh
            self.auto_refresh.start()
            
            self._initial_load_complete = True
            
            # Emit initialization complete
            complete_event = Event(
                type=EventType.DATA_REFRESH,
                data={"status": "initialized", "count": len(prs), "component": "data_integration"},
                source="data_integration_manager"
            )
            self.event_bus.emit(complete_event)
            
        except Exception as e:
            error_event = Event(
                type=EventType.DATA_REFRESH,
                data={"status": "error", "error": str(e), "component": "data_integration"},
                source="data_integration_manager"
            )
            self.event_bus.emit(error_event)
            raise
    
    def shutdown(self):
        """Shutdown data integration and cleanup resources."""
        self.auto_refresh.stop()
    
    async def manual_refresh(self):
        """Perform manual data refresh."""
        try:
            self.data_provider.invalidate_cache()
            prs = await self.data_provider.fetch_prs(use_cache=False)
            self.tui_state.update_pr_data(prs)
            
            refresh_event = Event(
                type=EventType.DATA_REFRESH,
                data={"status": "manual_refresh_complete", "count": len(prs)},
                source="data_integration_manager"
            )
            self.event_bus.emit(refresh_event)
            
        except Exception as e:
            error_event = Event(
                type=EventType.DATA_REFRESH,
                data={"status": "manual_refresh_error", "error": str(e)},
                source="data_integration_manager"
            )
            self.event_bus.emit(error_event)
    
    async def load_pr_details(self, pr_id: int) -> Optional[PullRequest]:
        """Load detailed information for a specific PR."""
        return await self.data_provider.fetch_pr_details(pr_id)
    
    def _handle_refresh_request(self, event: Event):
        """Handle refresh request events."""
        if event.data.get("manual", False):
            # Manual refresh requested
            asyncio.create_task(self.manual_refresh())
    
    def _handle_filter_change(self, event: Event):
        """Handle filter change events."""
        # Filter changes don't require new data, just UI update
        self.tui_state.notify_update()
    
    def _handle_sort_change(self, event: Event):
        """Handle sort change events."""
        # Sort changes don't require new data, just UI update
        self.tui_state.notify_update()
    
    @property
    def is_ready(self) -> bool:
        """Check if data integration is ready."""
        return self._initial_load_complete
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cache_size": len(self.data_provider.cache._cache),
            "auto_refresh_enabled": self.config.auto_refresh_enabled,
            "last_refresh": self.auto_refresh._last_refresh.isoformat(),
            "pagination_info": self.pagination.get_page_info()
        }