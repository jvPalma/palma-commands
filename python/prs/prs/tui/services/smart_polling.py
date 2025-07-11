"""
Smart polling system with exponential backoff and adaptive strategies.

This module provides intelligent polling mechanisms that adapt to activity
levels, reduce API calls when possible, and boost frequency during active periods.
"""

import asyncio
import threading
import time
import math
from typing import Dict, List, Optional, Set, Callable, Any, NamedTuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import random

from prs.tui.data.data_manager import TUIDataManager
from prs.tui.services.realtime_service import RealTimeStreamService, StreamEvent, StreamEventType


class PollingMode(Enum):
    """Different polling modes for different scenarios."""
    CONSERVATIVE = "conservative"  # Slow polling, minimal API usage
    NORMAL = "normal"             # Standard polling
    AGGRESSIVE = "aggressive"     # Fast polling for active periods
    BURST = "burst"              # Very fast polling for critical updates


class ActivityLevel(Enum):
    """Activity levels for adaptive polling."""
    IDLE = "idle"           # No recent activity
    LOW = "low"             # Minimal activity
    MEDIUM = "medium"       # Moderate activity
    HIGH = "high"           # High activity
    CRITICAL = "critical"   # Critical updates happening


@dataclass
class PollingConfig:
    """Configuration for polling strategies."""
    mode: PollingMode
    base_interval: int          # Base polling interval in seconds
    max_interval: int          # Maximum interval with backoff
    min_interval: int          # Minimum interval during burst mode
    backoff_multiplier: float  # Exponential backoff multiplier
    jitter_factor: float       # Random jitter to prevent thundering herd
    activity_threshold: int    # Events threshold for activity detection
    boost_duration: int        # Duration to maintain boost in seconds


class PollingMetrics(NamedTuple):
    """Metrics for polling performance."""
    total_polls: int
    successful_polls: int
    failed_polls: int
    cache_hits: int
    api_calls_saved: int
    average_response_time: float
    last_poll_time: datetime


class SmartPoller:
    """
    Smart polling strategy for a single resource or PR.
    
    Adapts polling frequency based on activity, implements exponential
    backoff on failures, and provides burst mode for critical updates.
    """
    
    def __init__(self, identifier: str, config: PollingConfig):
        self.identifier = identifier
        self.config = config
        
        # State tracking
        self.current_interval = config.base_interval
        self.consecutive_failures = 0
        self.consecutive_no_changes = 0
        self.last_poll_time: Optional[datetime] = None
        self.last_activity_time: Optional[datetime] = None
        
        # Activity tracking
        self.recent_events: List[datetime] = []
        self.activity_level = ActivityLevel.IDLE
        self.boost_until: Optional[datetime] = None
        
        # Metrics
        self.metrics = PollingMetrics(
            total_polls=0,
            successful_polls=0,
            failed_polls=0,
            cache_hits=0,
            api_calls_saved=0,
            average_response_time=0.0,
            last_poll_time=datetime.min
        )
        
        # Performance tracking
        self._response_times: List[float] = []
        
    def should_poll_now(self) -> bool:
        """Determine if polling should happen now."""
        if not self.last_poll_time:
            return True
            
        elapsed = (datetime.now() - self.last_poll_time).total_seconds()
        return elapsed >= self.get_current_interval()
        
    def get_current_interval(self) -> float:
        """Get the current polling interval with all adjustments applied."""
        base_interval = self._calculate_base_interval()
        
        # Apply jitter to prevent synchronization
        jitter = random.uniform(
            1.0 - self.config.jitter_factor,
            1.0 + self.config.jitter_factor
        )
        
        return max(base_interval * jitter, self.config.min_interval)
        
    def _calculate_base_interval(self) -> float:
        """Calculate base interval based on current state."""
        # Start with config base interval
        interval = self.config.base_interval
        
        # Apply activity-based adjustments
        if self.boost_until and datetime.now() < self.boost_until:
            # Boost mode - use minimum interval
            interval = self.config.min_interval
        elif self.activity_level == ActivityLevel.CRITICAL:
            interval = self.config.min_interval
        elif self.activity_level == ActivityLevel.HIGH:
            interval = max(self.config.base_interval // 2, self.config.min_interval)
        elif self.activity_level == ActivityLevel.MEDIUM:
            interval = self.config.base_interval
        elif self.activity_level == ActivityLevel.LOW:
            interval = self.config.base_interval * 1.5
        else:  # IDLE
            interval = self.config.base_interval * 2
            
        # Apply exponential backoff for consecutive failures
        if self.consecutive_failures > 0:
            backoff_factor = math.pow(self.config.backoff_multiplier, self.consecutive_failures)
            interval = min(interval * backoff_factor, self.config.max_interval)
            
        # Apply exponential backoff for consecutive no-changes
        if self.consecutive_no_changes > 3:
            no_change_factor = math.pow(1.2, min(self.consecutive_no_changes - 3, 5))
            interval = min(interval * no_change_factor, self.config.max_interval)
            
        return interval
        
    def record_poll_result(self, success: bool, has_changes: bool = False, 
                          response_time: float = 0.0, cached: bool = False):
        """Record the result of a polling operation."""
        now = datetime.now()
        self.last_poll_time = now
        
        # Update metrics
        total_polls = self.metrics.total_polls + 1
        successful_polls = self.metrics.successful_polls + (1 if success else 0)
        failed_polls = self.metrics.failed_polls + (0 if success else 1)
        cache_hits = self.metrics.cache_hits + (1 if cached else 0)
        
        # Update response times
        if response_time > 0:
            self._response_times.append(response_time)
            if len(self._response_times) > 100:  # Keep last 100 measurements
                self._response_times.pop(0)
                
        avg_response_time = sum(self._response_times) / len(self._response_times) if self._response_times else 0.0
        
        self.metrics = PollingMetrics(
            total_polls=total_polls,
            successful_polls=successful_polls,
            failed_polls=failed_polls,
            cache_hits=cache_hits,
            api_calls_saved=self.metrics.api_calls_saved + (1 if cached else 0),
            average_response_time=avg_response_time,
            last_poll_time=now
        )
        
        # Update failure tracking
        if success:
            self.consecutive_failures = 0
            if has_changes:
                self.consecutive_no_changes = 0
                self.record_activity()
            else:
                self.consecutive_no_changes += 1
        else:
            self.consecutive_failures += 1
            
        # Update activity level
        self._update_activity_level()
        
    def record_activity(self):
        """Record activity for this resource."""
        now = datetime.now()
        self.last_activity_time = now
        self.recent_events.append(now)
        
        # Clean old events (keep last hour)
        cutoff = now - timedelta(hours=1)
        self.recent_events = [event for event in self.recent_events if event > cutoff]
        
        # Update activity level
        self._update_activity_level()
        
    def _update_activity_level(self):
        """Update activity level based on recent events."""
        if not self.recent_events:
            self.activity_level = ActivityLevel.IDLE
            return
            
        now = datetime.now()
        
        # Count events in different time windows
        last_5_min = sum(1 for event in self.recent_events if now - event <= timedelta(minutes=5))
        last_15_min = sum(1 for event in self.recent_events if now - event <= timedelta(minutes=15))
        last_60_min = len(self.recent_events)
        
        # Determine activity level
        if last_5_min >= 3:
            self.activity_level = ActivityLevel.CRITICAL
        elif last_15_min >= 5:
            self.activity_level = ActivityLevel.HIGH
        elif last_60_min >= 10:
            self.activity_level = ActivityLevel.MEDIUM
        elif last_60_min >= 3:
            self.activity_level = ActivityLevel.LOW
        else:
            self.activity_level = ActivityLevel.IDLE
            
    def boost_frequency(self, duration_seconds: int = None):
        """Temporarily boost polling frequency."""
        duration = duration_seconds or self.config.boost_duration
        self.boost_until = datetime.now() + timedelta(seconds=duration)
        self.consecutive_no_changes = 0
        
    def get_stats(self) -> Dict[str, Any]:
        """Get polling statistics."""
        return {
            'identifier': self.identifier,
            'current_interval': self.get_current_interval(),
            'activity_level': self.activity_level.value,
            'consecutive_failures': self.consecutive_failures,
            'consecutive_no_changes': self.consecutive_no_changes,
            'recent_events_count': len(self.recent_events),
            'boost_active': self.boost_until and datetime.now() < self.boost_until,
            'metrics': self.metrics._asdict()
        }


class SmartPollingManager:
    """
    Manages multiple smart pollers with global optimization and coordination.
    
    Provides centralized control over polling strategies, implements global
    rate limiting, and coordinates polling to minimize API usage.
    """
    
    def __init__(self, data_manager: TUIDataManager, stream_service: RealTimeStreamService):
        self.data_manager = data_manager
        self.stream_service = stream_service
        
        # Polling management
        self.pollers: Dict[str, SmartPoller] = {}
        self.global_config = self._create_default_config()
        
        # Rate limiting
        self.global_rate_limit = 120  # API calls per minute
        self.rate_limit_window = timedelta(minutes=1)
        self.api_call_times: List[datetime] = []
        
        # Coordination
        self._polling_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        
        # Caching
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(minutes=2)
        
        # Event handling
        self.stream_service.add_event_callback(self._on_stream_event)
        
    def _create_default_config(self) -> Dict[str, PollingConfig]:
        """Create default polling configurations for different modes."""
        return {
            PollingMode.CONSERVATIVE.value: PollingConfig(
                mode=PollingMode.CONSERVATIVE,
                base_interval=60,
                max_interval=300,
                min_interval=30,
                backoff_multiplier=1.5,
                jitter_factor=0.1,
                activity_threshold=3,
                boost_duration=300
            ),
            PollingMode.NORMAL.value: PollingConfig(
                mode=PollingMode.NORMAL,
                base_interval=30,
                max_interval=180,
                min_interval=10,
                backoff_multiplier=1.5,
                jitter_factor=0.2,
                activity_threshold=5,
                boost_duration=180
            ),
            PollingMode.AGGRESSIVE.value: PollingConfig(
                mode=PollingMode.AGGRESSIVE,
                base_interval=15,
                max_interval=60,
                min_interval=5,
                backoff_multiplier=1.3,
                jitter_factor=0.15,
                activity_threshold=3,
                boost_duration=120
            ),
            PollingMode.BURST.value: PollingConfig(
                mode=PollingMode.BURST,
                base_interval=5,
                max_interval=30,
                min_interval=2,
                backoff_multiplier=1.2,
                jitter_factor=0.05,
                activity_threshold=1,
                boost_duration=60
            )
        }
        
    def start_polling(self):
        """Start the smart polling manager."""
        if self._running:
            return
            
        self._running = True
        self._stop_event.clear()
        
        self._polling_thread = threading.Thread(
            target=self._polling_loop,
            daemon=True,
            name="SmartPolling"
        )
        self._polling_thread.start()
        
    def stop_polling(self):
        """Stop the smart polling manager."""
        self._running = False
        self._stop_event.set()
        
        if self._polling_thread:
            self._polling_thread.join(timeout=5.0)
            
    def register_pr_poller(self, pr_id: int, mode: PollingMode = PollingMode.NORMAL):
        """Register a poller for a specific PR."""
        identifier = f"pr_{pr_id}"
        config = self.global_config[mode.value]
        
        self.pollers[identifier] = SmartPoller(identifier, config)
        
    def unregister_poller(self, identifier: str):
        """Unregister a poller."""
        self.pollers.pop(identifier, None)
        
    def boost_pr_polling(self, pr_id: int, duration_seconds: int = 60):
        """Boost polling frequency for a specific PR."""
        identifier = f"pr_{pr_id}"
        if identifier in self.pollers:
            self.pollers[identifier].boost_frequency(duration_seconds)
            
    def _polling_loop(self):
        """Main polling coordination loop."""
        while not self._stop_event.is_set():
            try:
                self._coordinate_polling()
                self._cleanup_cache()
                self._stop_event.wait(1.0)  # Check every second
            except Exception:
                # Don't let errors break the polling loop
                self._stop_event.wait(5.0)
                
    def _coordinate_polling(self):
        """Coordinate polling across all registered pollers."""
        if not self.pollers:
            return
            
        # Check rate limiting
        if not self._can_make_api_call():
            return
            
        # Find pollers that need to poll
        ready_pollers = [
            (identifier, poller) for identifier, poller in self.pollers.items()
            if poller.should_poll_now()
        ]
        
        if not ready_pollers:
            return
            
        # Sort by priority (activity level and last poll time)
        ready_pollers.sort(key=lambda x: self._get_poller_priority(x[1]))
        
        # Execute polls with rate limiting
        for identifier, poller in ready_pollers:
            if not self._can_make_api_call():
                break
                
            self._execute_poll(identifier, poller)
            
    def _get_poller_priority(self, poller: SmartPoller) -> tuple:
        """Get priority score for poller scheduling."""
        # Higher activity gets higher priority (lower sort value)
        activity_priority = {
            ActivityLevel.CRITICAL: 0,
            ActivityLevel.HIGH: 1,
            ActivityLevel.MEDIUM: 2,
            ActivityLevel.LOW: 3,
            ActivityLevel.IDLE: 4
        }
        
        # Time since last poll (older gets higher priority)
        time_priority = 0
        if poller.last_poll_time:
            time_priority = -(datetime.now() - poller.last_poll_time).total_seconds()
            
        return (activity_priority[poller.activity_level], time_priority)
        
    def _execute_poll(self, identifier: str, poller: SmartPoller):
        """Execute a poll for a specific poller."""
        start_time = time.time()
        
        try:
            # Check cache first
            cached_result = self._check_cache(identifier)
            if cached_result:
                poller.record_poll_result(
                    success=True,
                    has_changes=False,
                    response_time=0.0,
                    cached=True
                )
                return
                
            # Execute actual poll
            if identifier.startswith("pr_"):
                pr_id = int(identifier[3:])
                result = self._poll_pr_data(pr_id)
            else:
                result = self._poll_general_data(identifier)
                
            response_time = time.time() - start_time
            self._record_api_call()
            
            # Process result
            success = result is not None
            has_changes = self._detect_changes(identifier, result)
            
            # Update cache
            if success:
                self._update_cache(identifier, result)
                
            # Record result
            poller.record_poll_result(
                success=success,
                has_changes=has_changes,
                response_time=response_time,
                cached=False
            )
            
            # Trigger data refresh if changes detected
            if has_changes and identifier.startswith("pr_"):
                pr_id = int(identifier[3:])
                asyncio.run(self.data_manager.refresh_pr_data(pr_id))
                
        except Exception:
            response_time = time.time() - start_time
            poller.record_poll_result(
                success=False,
                has_changes=False,
                response_time=response_time,
                cached=False
            )
            
    def _poll_pr_data(self, pr_id: int) -> Optional[Dict[str, Any]]:
        """Poll data for a specific PR."""
        try:
            # Get current PR data
            pr = self.data_manager.get_pr_by_id(pr_id)
            if not pr:
                return None
                
            # Create snapshot for comparison
            return {
                'id': pr.id,
                'title': pr.title,
                'updated_at': pr.updated_at,
                'reviews_count': len(pr.reviews) if pr.reviews else 0,
                'comments_count': len(pr.comments) if pr.comments else 0,
                'checks_count': len(pr.checks) if pr.checks else 0,
                'ci_state': getattr(pr, 'ci_data', None)
            }
        except Exception:
            return None
            
    def _poll_general_data(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Poll general data for non-PR resources."""
        # Placeholder for other types of polling
        return {}
        
    def _detect_changes(self, identifier: str, new_data: Dict[str, Any]) -> bool:
        """Detect if data has changed since last poll."""
        if identifier not in self._cache:
            return True  # First time polling
            
        old_data = self._cache[identifier]
        
        # Compare relevant fields
        if identifier.startswith("pr_"):
            # For PRs, compare key fields
            key_fields = ['updated_at', 'reviews_count', 'comments_count', 'checks_count']
            for field in key_fields:
                if new_data.get(field) != old_data.get(field):
                    return True
                    
            # Special handling for CI state
            if new_data.get('ci_state') != old_data.get('ci_state'):
                return True
                
        return False
        
    def _can_make_api_call(self) -> bool:
        """Check if we can make an API call within rate limits."""
        now = datetime.now()
        
        # Clean old API call records
        cutoff = now - self.rate_limit_window
        self.api_call_times = [call_time for call_time in self.api_call_times if call_time > cutoff]
        
        # Check if we're under the rate limit
        return len(self.api_call_times) < self.global_rate_limit
        
    def _record_api_call(self):
        """Record an API call for rate limiting."""
        self.api_call_times.append(datetime.now())
        
    def _check_cache(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Check if cached data is available and fresh."""
        if identifier not in self._cache:
            return None
            
        cache_time = self._cache_timestamps.get(identifier)
        if not cache_time:
            return None
            
        # Check if cache is still fresh
        if datetime.now() - cache_time <= self._cache_ttl:
            return self._cache[identifier]
            
        return None
        
    def _update_cache(self, identifier: str, data: Dict[str, Any]):
        """Update cache with new data."""
        self._cache[identifier] = data
        self._cache_timestamps[identifier] = datetime.now()
        
    def _cleanup_cache(self):
        """Clean up stale cache entries."""
        now = datetime.now()
        stale_keys = []
        
        for identifier, timestamp in self._cache_timestamps.items():
            if now - timestamp > self._cache_ttl * 2:  # Remove cache older than 2x TTL
                stale_keys.append(identifier)
                
        for key in stale_keys:
            self._cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
            
    def _on_stream_event(self, event: StreamEvent):
        """Handle stream events to optimize polling."""
        pr_identifier = f"pr_{event.pr_id}"
        
        if pr_identifier in self.pollers:
            poller = self.pollers[pr_identifier]
            
            # Record activity for the PR
            poller.record_activity()
            
            # Boost polling for specific event types
            if event.event_type in [StreamEventType.BUILD_START, StreamEventType.BUILD_PROGRESS]:
                poller.boost_frequency(60)  # Boost for 1 minute
            elif event.event_type == StreamEventType.CI_STATUS_CHANGE:
                poller.boost_frequency(30)  # Boost for 30 seconds
                
    def get_polling_stats(self) -> Dict[str, Any]:
        """Get comprehensive polling statistics."""
        total_pollers = len(self.pollers)
        active_pollers = sum(1 for p in self.pollers.values() if p.activity_level != ActivityLevel.IDLE)
        
        # Aggregate metrics
        total_polls = sum(p.metrics.total_polls for p in self.pollers.values())
        total_cache_hits = sum(p.metrics.cache_hits for p in self.pollers.values())
        total_api_calls_saved = sum(p.metrics.api_calls_saved for p in self.pollers.values())
        
        return {
            'total_pollers': total_pollers,
            'active_pollers': active_pollers,
            'total_polls': total_polls,
            'cache_hit_rate': total_cache_hits / total_polls if total_polls > 0 else 0,
            'api_calls_saved': total_api_calls_saved,
            'current_api_calls_per_minute': len(self.api_call_times),
            'rate_limit_utilization': len(self.api_call_times) / self.global_rate_limit,
            'cache_size': len(self._cache),
            'pollers': {identifier: poller.get_stats() for identifier, poller in self.pollers.items()}
        }
        
    def optimize_polling_modes(self):
        """Optimize polling modes based on current system state."""
        # Analyze current load and adjust modes accordingly
        stats = self.get_polling_stats()
        
        # If rate limit utilization is high, switch to more conservative polling
        if stats['rate_limit_utilization'] > 0.8:
            for poller in self.pollers.values():
                if poller.config.mode not in [PollingMode.CONSERVATIVE]:
                    # Switch to more conservative mode
                    new_config = self.global_config[PollingMode.CONSERVATIVE.value]
                    poller.config = new_config
                    
        # If cache hit rate is low, increase cache TTL
        elif stats['cache_hit_rate'] < 0.3:
            self._cache_ttl = min(self._cache_ttl * 1.2, timedelta(minutes=5))
            
    def cleanup(self):
        """Clean up resources."""
        self.stop_polling()
        self.pollers.clear()
        self._cache.clear()
        self._cache_timestamps.clear()
        self.api_call_times.clear()
        
        # Remove stream event callback
        self.stream_service.remove_event_callback(self._on_stream_event)