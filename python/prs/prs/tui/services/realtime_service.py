"""
Real-time streaming service for CI status and PR updates.

This service provides WebSocket-like functionality for real-time updates
without requiring an actual WebSocket server. It uses intelligent polling
with event-driven updates to provide near real-time user experience.
"""

import asyncio
import threading
import time
import json
from typing import Dict, List, Optional, Set, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib

from prs.tui.data.data_manager import TUIDataManager, TUIDataUpdate
from prs.core.ci.manager import get_ci_manager


class StreamEventType(Enum):
    """Types of streaming events."""
    CI_STATUS_CHANGE = "ci_status_change"
    PR_UPDATE = "pr_update"
    BUILD_PROGRESS = "build_progress"
    BUILD_START = "build_start"
    BUILD_COMPLETE = "build_complete"
    BUILD_FAILURE = "build_failure"
    REVIEW_UPDATE = "review_update"
    COMMENT_UPDATE = "comment_update"


@dataclass
class StreamEvent:
    """Represents a real-time stream event."""
    event_type: StreamEventType
    timestamp: datetime
    pr_id: int
    data: Dict[str, Any]
    source: str = "github"  # Source provider
    checksum: Optional[str] = None
    
    def __post_init__(self):
        """Generate checksum for deduplication."""
        if not self.checksum:
            content = f"{self.event_type.value}:{self.pr_id}:{json.dumps(self.data, sort_keys=True)}"
            self.checksum = hashlib.md5(content.encode()).hexdigest()


class PollingStrategy:
    """Adaptive polling strategy with exponential backoff."""
    
    def __init__(self, base_interval: int = 10, max_interval: int = 300):
        self.base_interval = base_interval
        self.max_interval = max_interval
        self.current_interval = base_interval
        self.consecutive_no_changes = 0
        self.activity_boost = False
        
    def get_next_interval(self, has_changes: bool = False) -> int:
        """Get the next polling interval based on activity."""
        if has_changes:
            # Reset to base interval on activity
            self.current_interval = self.base_interval
            self.consecutive_no_changes = 0
            self.activity_boost = True
        else:
            self.consecutive_no_changes += 1
            # Exponential backoff with jitter
            if self.consecutive_no_changes > 3:
                self.current_interval = min(
                    self.current_interval * 1.5,
                    self.max_interval
                )
                self.activity_boost = False
        
        # Add small random jitter to prevent thundering herd
        import random
        jitter = random.uniform(0.8, 1.2)
        return int(self.current_interval * jitter)
    
    def boost_for_activity(self):
        """Temporarily boost polling frequency for active periods."""
        self.activity_boost = True
        self.current_interval = max(self.base_interval // 2, 5)
        self.consecutive_no_changes = 0


class RealTimeStreamService:
    """
    Provides real-time streaming of CI status and PR updates.
    
    This service simulates WebSocket-like functionality using intelligent
    polling strategies, event deduplication, and push-like notifications.
    """
    
    def __init__(self, data_manager: TUIDataManager):
        self.data_manager = data_manager
        self.ci_manager = get_ci_manager()
        
        # Event streaming
        self._event_callbacks: List[Callable[[StreamEvent], None]] = []
        self._event_history: List[StreamEvent] = []
        self._seen_checksums: Set[str] = set()
        
        # Polling configuration
        self._polling_strategies: Dict[int, PollingStrategy] = {}
        self._default_strategy = PollingStrategy(base_interval=15, max_interval=180)
        self._high_priority_prs: Set[int] = set()  # PRs with active builds
        
        # State tracking
        self._last_known_states: Dict[int, Dict[str, Any]] = {}
        self._active_builds: Dict[int, Dict[str, Any]] = {}
        
        # Threading
        self._streaming_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        
        # Performance optimization
        self._batch_events = True
        self._batch_size = 5
        self._batch_timeout = 2.0  # seconds
        self._pending_batch: List[StreamEvent] = []
        self._last_batch_time = time.time()
        
    def start_streaming(self):
        """Start the real-time streaming service."""
        if self._running:
            return
            
        self._running = True
        self._stop_event.clear()
        
        self._streaming_thread = threading.Thread(
            target=self._streaming_loop,
            daemon=True,
            name="RealTimeStream"
        )
        self._streaming_thread.start()
        
    def stop_streaming(self):
        """Stop the real-time streaming service."""
        self._running = False
        self._stop_event.set()
        
        if self._streaming_thread:
            self._streaming_thread.join(timeout=5.0)
            
    def add_event_callback(self, callback: Callable[[StreamEvent], None]):
        """Add a callback for streaming events."""
        self._event_callbacks.append(callback)
        
    def remove_event_callback(self, callback: Callable[[StreamEvent], None]):
        """Remove an event callback."""
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)
            
    def _emit_event(self, event: StreamEvent):
        """Emit an event to all registered callbacks."""
        # Deduplicate events
        if event.checksum in self._seen_checksums:
            return
            
        self._seen_checksums.add(event.checksum)
        self._event_history.append(event)
        
        # Limit history size
        if len(self._event_history) > 1000:
            # Remove oldest events and their checksums
            removed_event = self._event_history.pop(0)
            self._seen_checksums.discard(removed_event.checksum)
            
        if self._batch_events:
            self._add_to_batch(event)
        else:
            self._notify_callbacks([event])
            
    def _add_to_batch(self, event: StreamEvent):
        """Add event to batch for efficient processing."""
        self._pending_batch.append(event)
        
        # Emit batch if size or timeout reached
        current_time = time.time()
        if (len(self._pending_batch) >= self._batch_size or
            current_time - self._last_batch_time >= self._batch_timeout):
            self._flush_batch()
            
    def _flush_batch(self):
        """Flush pending batch of events."""
        if not self._pending_batch:
            return
            
        batch = self._pending_batch.copy()
        self._pending_batch.clear()
        self._last_batch_time = time.time()
        
        self._notify_callbacks(batch)
        
    def _notify_callbacks(self, events: List[StreamEvent]):
        """Notify all callbacks of events."""
        for callback in self._event_callbacks:
            try:
                for event in events:
                    callback(event)
            except Exception:
                # Don't let callback errors break streaming
                pass
                
    def _streaming_loop(self):
        """Main streaming loop."""
        while not self._stop_event.is_set():
            try:
                self._poll_for_updates()
                
                # Flush any pending batched events
                if self._pending_batch:
                    self._flush_batch()
                    
                # Dynamic sleep based on activity
                sleep_time = self._calculate_sleep_time()
                self._stop_event.wait(sleep_time)
                
            except Exception:
                # Don't let errors break the streaming loop
                self._stop_event.wait(10.0)
                
    def _poll_for_updates(self):
        """Poll for updates and generate stream events."""
        prs = self.data_manager.get_prs()
        has_changes = False
        
        for pr in prs:
            pr_changes = self._check_pr_for_updates(pr)
            if pr_changes:
                has_changes = True
                
        # Update polling strategies based on activity
        for pr_id, strategy in self._polling_strategies.items():
            strategy.get_next_interval(has_changes)
            
    def _check_pr_for_updates(self, pr) -> bool:
        """Check a single PR for updates and emit events."""
        pr_id = pr.id
        has_changes = False
        
        # Get current state
        current_state = self._get_pr_state_snapshot(pr)
        last_state = self._last_known_states.get(pr_id, {})
        
        # Check for CI status changes
        if self._check_ci_changes(pr, current_state, last_state):
            has_changes = True
            
        # Check for build progress
        if self._check_build_progress(pr, current_state, last_state):
            has_changes = True
            
        # Check for PR metadata changes
        if self._check_pr_metadata_changes(pr, current_state, last_state):
            has_changes = True
            
        # Update known state
        self._last_known_states[pr_id] = current_state
        
        return has_changes
        
    def _get_pr_state_snapshot(self, pr) -> Dict[str, Any]:
        """Create a state snapshot of a PR for comparison."""
        state = {
            'title': pr.title,
            'updated_at': pr.updated_at,
            'reviews_count': len(pr.reviews) if pr.reviews else 0,
            'comments_count': len(pr.comments) if pr.comments else 0,
            'checks_count': len(pr.checks) if pr.checks else 0,
        }
        
        # CI-specific state
        if hasattr(pr, 'ci_data') and pr.ci_data:
            state['ci_state'] = {
                'total_workflows': pr.ci_data.total_workflows,
                'successful_workflows': pr.ci_data.successful_workflows,
                'failed_workflows': pr.ci_data.failed_workflows,
                'pending_workflows': pr.ci_data.pending_workflows,
                'workflows': []
            }
            
            # Track individual workflow states
            for workflow in pr.ci_data.workflows:
                workflow_state = {
                    'id': workflow.id,
                    'name': workflow.name,
                    'status': workflow.status,
                    'conclusion': workflow.conclusion,
                    'updated_at': workflow.updated_at
                }
                state['ci_state']['workflows'].append(workflow_state)
                
        return state
        
    def _check_ci_changes(self, pr, current_state: Dict, last_state: Dict) -> bool:
        """Check for CI status changes."""
        pr_id = pr.id
        current_ci = current_state.get('ci_state', {})
        last_ci = last_state.get('ci_state', {})
        
        # Check overall CI status changes
        if current_ci != last_ci:
            # Determine what changed
            changes = {}
            
            # Check workflow count changes
            if current_ci.get('total_workflows') != last_ci.get('total_workflows'):
                changes['workflow_count_changed'] = True
                
            # Check status changes
            status_fields = ['successful_workflows', 'failed_workflows', 'pending_workflows']
            for field in status_fields:
                if current_ci.get(field) != last_ci.get(field):
                    changes[f'{field}_changed'] = True
                    
            # Check individual workflow changes
            current_workflows = {w['id']: w for w in current_ci.get('workflows', [])}
            last_workflows = {w['id']: w for w in last_ci.get('workflows', [])}
            
            workflow_changes = []
            for workflow_id, workflow in current_workflows.items():
                last_workflow = last_workflows.get(workflow_id)
                
                if not last_workflow:
                    # New workflow
                    workflow_changes.append({
                        'type': 'new',
                        'workflow': workflow
                    })
                    
                    # Emit build start event
                    if workflow['status'] in ['in_progress', 'queued']:
                        self._emit_build_start_event(pr_id, workflow)
                        
                elif (workflow['status'] != last_workflow['status'] or
                      workflow['conclusion'] != last_workflow['conclusion']):
                    # Status change
                    workflow_changes.append({
                        'type': 'status_change',
                        'workflow': workflow,
                        'previous': last_workflow
                    })
                    
                    # Emit specific events
                    if workflow['status'] == 'completed':
                        if workflow['conclusion'] == 'success':
                            self._emit_build_complete_event(pr_id, workflow, success=True)
                        else:
                            self._emit_build_failure_event(pr_id, workflow)
                    elif workflow['status'] == 'in_progress':
                        self._emit_build_progress_event(pr_id, workflow)
                        # Add to high priority monitoring
                        self._high_priority_prs.add(pr_id)
                        
            if workflow_changes:
                changes['workflow_changes'] = workflow_changes
                
            # Emit CI status change event
            event = StreamEvent(
                event_type=StreamEventType.CI_STATUS_CHANGE,
                timestamp=datetime.now(),
                pr_id=pr_id,
                data={
                    'current_state': current_ci,
                    'previous_state': last_ci,
                    'changes': changes
                }
            )
            self._emit_event(event)
            
            return True
            
        return False
        
    def _check_build_progress(self, pr, current_state: Dict, last_state: Dict) -> bool:
        """Check for build progress updates."""
        pr_id = pr.id
        
        # Check if PR has active builds
        current_ci = current_state.get('ci_state', {})
        active_workflows = [
            w for w in current_ci.get('workflows', [])
            if w['status'] in ['in_progress', 'queued']
        ]
        
        if active_workflows:
            # Update active builds tracking
            self._active_builds[pr_id] = {
                'workflows': active_workflows,
                'last_update': datetime.now()
            }
            
            # Emit progress events for active builds
            for workflow in active_workflows:
                self._emit_build_progress_event(pr_id, workflow)
                
            return True
        else:
            # Remove from active builds if no longer active
            if pr_id in self._active_builds:
                del self._active_builds[pr_id]
                self._high_priority_prs.discard(pr_id)
                
        return False
        
    def _check_pr_metadata_changes(self, pr, current_state: Dict, last_state: Dict) -> bool:
        """Check for PR metadata changes (reviews, comments, etc.)."""
        pr_id = pr.id
        
        # Check for review changes
        if current_state.get('reviews_count') != last_state.get('reviews_count'):
            event = StreamEvent(
                event_type=StreamEventType.REVIEW_UPDATE,
                timestamp=datetime.now(),
                pr_id=pr_id,
                data={
                    'reviews_count': current_state.get('reviews_count'),
                    'previous_count': last_state.get('reviews_count', 0)
                }
            )
            self._emit_event(event)
            return True
            
        # Check for comment changes
        if current_state.get('comments_count') != last_state.get('comments_count'):
            event = StreamEvent(
                event_type=StreamEventType.COMMENT_UPDATE,
                timestamp=datetime.now(),
                pr_id=pr_id,
                data={
                    'comments_count': current_state.get('comments_count'),
                    'previous_count': last_state.get('comments_count', 0)
                }
            )
            self._emit_event(event)
            return True
            
        return False
        
    def _emit_build_start_event(self, pr_id: int, workflow: Dict):
        """Emit a build start event."""
        event = StreamEvent(
            event_type=StreamEventType.BUILD_START,
            timestamp=datetime.now(),
            pr_id=pr_id,
            data={
                'workflow_id': workflow['id'],
                'workflow_name': workflow['name'],
                'status': workflow['status']
            }
        )
        self._emit_event(event)
        
    def _emit_build_progress_event(self, pr_id: int, workflow: Dict):
        """Emit a build progress event."""
        event = StreamEvent(
            event_type=StreamEventType.BUILD_PROGRESS,
            timestamp=datetime.now(),
            pr_id=pr_id,
            data={
                'workflow_id': workflow['id'],
                'workflow_name': workflow['name'],
                'status': workflow['status'],
                'progress': self._estimate_build_progress(workflow)
            }
        )
        self._emit_event(event)
        
    def _emit_build_complete_event(self, pr_id: int, workflow: Dict, success: bool = True):
        """Emit a build complete event."""
        event_type = StreamEventType.BUILD_COMPLETE if success else StreamEventType.BUILD_FAILURE
        
        event = StreamEvent(
            event_type=event_type,
            timestamp=datetime.now(),
            pr_id=pr_id,
            data={
                'workflow_id': workflow['id'],
                'workflow_name': workflow['name'],
                'conclusion': workflow['conclusion'],
                'success': success
            }
        )
        self._emit_event(event)
        
    def _emit_build_failure_event(self, pr_id: int, workflow: Dict):
        """Emit a build failure event."""
        self._emit_build_complete_event(pr_id, workflow, success=False)
        
    def _estimate_build_progress(self, workflow: Dict) -> float:
        """Estimate build progress as a percentage (0.0 to 1.0)."""
        # This is a simplified estimation - in practice, you might
        # integrate with CI provider APIs for actual progress
        status = workflow.get('status', '')
        
        if status == 'queued':
            return 0.0
        elif status == 'in_progress':
            # Use heuristics based on time or workflow history
            return 0.5  # Simplified - assume 50% when in progress
        elif status == 'completed':
            return 1.0
        else:
            return 0.0
            
    def _calculate_sleep_time(self) -> float:
        """Calculate dynamic sleep time based on activity."""
        # Base sleep time
        base_sleep = self._default_strategy.current_interval
        
        # Boost frequency for active builds
        if self._high_priority_prs:
            base_sleep = min(base_sleep, 5.0)
            
        # Add some randomness to prevent synchronization
        import random
        return base_sleep * random.uniform(0.8, 1.2)
        
    def get_active_builds(self) -> Dict[int, Dict[str, Any]]:
        """Get currently active builds."""
        # Clean up stale entries
        current_time = datetime.now()
        stale_cutoff = current_time - timedelta(minutes=30)
        
        active_builds = {}
        for pr_id, build_info in self._active_builds.items():
            if build_info['last_update'] > stale_cutoff:
                active_builds[pr_id] = build_info
                
        return active_builds
        
    def get_event_history(self, pr_id: Optional[int] = None, 
                         event_types: Optional[List[StreamEventType]] = None,
                         limit: int = 100) -> List[StreamEvent]:
        """Get event history with optional filtering."""
        events = self._event_history
        
        # Filter by PR ID
        if pr_id is not None:
            events = [e for e in events if e.pr_id == pr_id]
            
        # Filter by event types
        if event_types:
            events = [e for e in events if e.event_type in event_types]
            
        # Return most recent events
        return events[-limit:]
        
    def boost_pr_monitoring(self, pr_id: int):
        """Boost monitoring frequency for a specific PR."""
        if pr_id not in self._polling_strategies:
            self._polling_strategies[pr_id] = PollingStrategy(base_interval=5, max_interval=60)
        else:
            self._polling_strategies[pr_id].boost_for_activity()
            
        self._high_priority_prs.add(pr_id)
        
    def get_streaming_stats(self) -> Dict[str, Any]:
        """Get streaming service statistics."""
        return {
            'running': self._running,
            'total_events': len(self._event_history),
            'active_builds': len(self._active_builds),
            'high_priority_prs': len(self._high_priority_prs),
            'polling_strategies': len(self._polling_strategies),
            'pending_batch_size': len(self._pending_batch),
            'seen_checksums': len(self._seen_checksums)
        }
        
    def cleanup(self):
        """Clean up resources."""
        self.stop_streaming()
        self._event_callbacks.clear()
        self._event_history.clear()
        self._seen_checksums.clear()
        self._active_builds.clear()
        self._high_priority_prs.clear()
        self._polling_strategies.clear()