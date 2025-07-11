"""
Performance optimizations for TUI.

Provides utilities for efficient rendering, data loading,
and memory management in the TUI interface.
"""

import asyncio
import time
import threading
from typing import List, Dict, Any, Optional, Callable, TypeVar, Generic
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """Cache entry with timestamp and data."""
    data: T
    timestamp: datetime
    ttl: Optional[timedelta] = None
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.ttl is None:
            return False
        return datetime.now() - self.timestamp > self.ttl


class LRUCache(Generic[T]):
    """LRU Cache implementation for efficient data caching."""
    
    def __init__(self, max_size: int = 100, default_ttl: Optional[timedelta] = None):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry[T]] = {}
        self._access_order: deque = deque()
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[T]:
        """Get value from cache."""
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            if entry.is_expired():
                del self._cache[key]
                self._access_order.remove(key)
                return None
            
            # Move to end (most recently used)
            self._access_order.remove(key)
            self._access_order.append(key)
            
            return entry.data
    
    def put(self, key: str, value: T, ttl: Optional[timedelta] = None) -> None:
        """Put value into cache."""
        with self._lock:
            if key in self._cache:
                # Update existing entry
                self._cache[key] = CacheEntry(value, datetime.now(), ttl or self.default_ttl)
                self._access_order.remove(key)
                self._access_order.append(key)
            else:
                # Add new entry
                if len(self._cache) >= self.max_size:
                    # Remove least recently used
                    lru_key = self._access_order.popleft()
                    del self._cache[lru_key]
                
                self._cache[key] = CacheEntry(value, datetime.now(), ttl or self.default_ttl)
                self._access_order.append(key)
    
    def clear(self) -> None:
        """Clear the cache."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
    
    def size(self) -> int:
        """Get cache size."""
        with self._lock:
            return len(self._cache)


class RateLimiter:
    """Rate limiter to prevent excessive API calls."""
    
    def __init__(self, max_calls: int, time_window: timedelta):
        self.max_calls = max_calls
        self.time_window = time_window
        self._calls: deque = deque()
        self._lock = threading.Lock()
    
    def can_proceed(self) -> bool:
        """Check if a call can proceed."""
        with self._lock:
            now = datetime.now()
            
            # Remove old calls outside the time window
            while self._calls and now - self._calls[0] > self.time_window:
                self._calls.popleft()
            
            return len(self._calls) < self.max_calls
    
    def record_call(self) -> None:
        """Record a new call."""
        with self._lock:
            self._calls.append(datetime.now())
    
    async def wait_if_needed(self) -> None:
        """Wait if rate limit is exceeded."""
        if not self.can_proceed():
            # Calculate wait time
            with self._lock:
                if self._calls:
                    oldest_call = self._calls[0]
                    wait_time = (oldest_call + self.time_window - datetime.now()).total_seconds()
                    if wait_time > 0:
                        await asyncio.sleep(wait_time)


class DataPaginator:
    """Efficient data pagination for large datasets."""
    
    def __init__(self, data: List[T], page_size: int = 50):
        self.data = data
        self.page_size = page_size
        self.current_page = 0
        self._total_pages = (len(data) + page_size - 1) // page_size if data else 0
    
    def get_page(self, page: int) -> List[T]:
        """Get a specific page of data."""
        if page < 0 or page >= self._total_pages:
            return []
        
        start_idx = page * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.data))
        return self.data[start_idx:end_idx]
    
    def get_current_page(self) -> List[T]:
        """Get the current page of data."""
        return self.get_page(self.current_page)
    
    def next_page(self) -> bool:
        """Move to next page. Returns True if successful."""
        if self.current_page < self._total_pages - 1:
            self.current_page += 1
            return True
        return False
    
    def prev_page(self) -> bool:
        """Move to previous page. Returns True if successful."""
        if self.current_page > 0:
            self.current_page -= 1
            return True
        return False
    
    def goto_page(self, page: int) -> bool:
        """Go to specific page. Returns True if successful."""
        if 0 <= page < self._total_pages:
            self.current_page = page
            return True
        return False
    
    @property
    def total_pages(self) -> int:
        """Get total number of pages."""
        return self._total_pages
    
    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.current_page < self._total_pages - 1
    
    @property
    def has_prev(self) -> bool:
        """Check if there's a previous page."""
        return self.current_page > 0


class AsyncTaskManager:
    """Manages background async tasks for the TUI."""
    
    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self._tasks: List[asyncio.Task] = []
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._lock = asyncio.Lock()
    
    async def submit_task(self, coro, callback: Optional[Callable] = None) -> asyncio.Task:
        """Submit a new async task."""
        async def _wrapped_task():
            async with self._semaphore:
                try:
                    result = await coro
                    if callback:
                        callback(result, None)
                    return result
                except Exception as e:
                    if callback:
                        callback(None, e)
                    raise
        
        task = asyncio.create_task(_wrapped_task())
        
        async with self._lock:
            self._tasks.append(task)
            
            # Clean up completed tasks
            self._tasks = [t for t in self._tasks if not t.done()]
        
        return task
    
    async def wait_for_completion(self, timeout: Optional[float] = None) -> None:
        """Wait for all tasks to complete."""
        async with self._lock:
            if self._tasks:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*self._tasks, return_exceptions=True),
                        timeout=timeout
                    )
                except asyncio.TimeoutError:
                    # Cancel remaining tasks
                    for task in self._tasks:
                        if not task.done():
                            task.cancel()
    
    async def cancel_all_tasks(self) -> None:
        """Cancel all running tasks."""
        async with self._lock:
            for task in self._tasks:
                if not task.done():
                    task.cancel()
            self._tasks.clear()
    
    def get_running_tasks_count(self) -> int:
        """Get number of running tasks."""
        return len([t for t in self._tasks if not t.done()])


class RenderOptimizer:
    """Optimizes rendering performance for large datasets."""
    
    def __init__(self, viewport_size: int = 20, buffer_size: int = 10):
        self.viewport_size = viewport_size
        self.buffer_size = buffer_size
        self._visible_range = (0, viewport_size)
        self._last_scroll_position = 0
    
    def update_viewport(self, scroll_position: int, total_items: int) -> tuple[int, int]:
        """Update viewport based on scroll position."""
        # Calculate visible range with buffer
        start = max(0, scroll_position - self.buffer_size)
        end = min(total_items, scroll_position + self.viewport_size + self.buffer_size)
        
        self._visible_range = (start, end)
        self._last_scroll_position = scroll_position
        
        return self._visible_range
    
    def should_render_item(self, item_index: int) -> bool:
        """Check if an item should be rendered."""
        start, end = self._visible_range
        return start <= item_index < end
    
    def get_visible_range(self) -> tuple[int, int]:
        """Get current visible range."""
        return self._visible_range


class MemoryMonitor:
    """Monitors memory usage and triggers cleanup when needed."""
    
    def __init__(self, threshold_mb: int = 100):
        self.threshold_mb = threshold_mb
        self._cleanup_callbacks: List[Callable] = []
    
    def add_cleanup_callback(self, callback: Callable) -> None:
        """Add a cleanup callback."""
        self._cleanup_callbacks.append(callback)
    
    def check_memory_usage(self) -> bool:
        """Check if memory usage exceeds threshold."""
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            return memory_mb > self.threshold_mb
        except ImportError:
            # psutil not available, assume memory is fine
            return False
    
    def trigger_cleanup(self) -> None:
        """Trigger cleanup callbacks."""
        for callback in self._cleanup_callbacks:
            try:
                callback()
            except Exception:
                # Don't let cleanup failures break the app
                pass


class PerformanceProfiler:
    """Simple performance profiler for identifying bottlenecks."""
    
    def __init__(self):
        self._timings: Dict[str, List[float]] = {}
        self._active_timers: Dict[str, float] = {}
        self._lock = threading.Lock()
    
    def start_timer(self, name: str) -> None:
        """Start timing an operation."""
        with self._lock:
            self._active_timers[name] = time.time()
    
    def end_timer(self, name: str) -> Optional[float]:
        """End timing an operation and return duration."""
        with self._lock:
            if name not in self._active_timers:
                return None
            
            duration = time.time() - self._active_timers[name]
            del self._active_timers[name]
            
            if name not in self._timings:
                self._timings[name] = []
            
            self._timings[name].append(duration)
            
            # Keep only last 100 measurements
            if len(self._timings[name]) > 100:
                self._timings[name] = self._timings[name][-100:]
            
            return duration
    
    def get_stats(self, name: str) -> Optional[Dict[str, float]]:
        """Get statistics for a timer."""
        with self._lock:
            if name not in self._timings or not self._timings[name]:
                return None
            
            timings = self._timings[name]
            return {
                'count': len(timings),
                'total': sum(timings),
                'average': sum(timings) / len(timings),
                'min': min(timings),
                'max': max(timings)
            }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all timers."""
        with self._lock:
            return {name: self.get_stats(name) for name in self._timings if self._timings[name]}


# Global instances
profiler = PerformanceProfiler()
memory_monitor = MemoryMonitor()


def profile_function(name: str):
    """Decorator to profile function execution time."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            profiler.start_timer(name)
            try:
                return func(*args, **kwargs)
            finally:
                profiler.end_timer(name)
        return wrapper
    return decorator


def profile_async_function(name: str):
    """Decorator to profile async function execution time."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            profiler.start_timer(name)
            try:
                return await func(*args, **kwargs)
            finally:
                profiler.end_timer(name)
        return wrapper
    return decorator