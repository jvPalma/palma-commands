"""
Real-time updates service for TUI.

This service manages live updates for CI status changes, PR updates,
and other real-time data without blocking the UI.
"""

import asyncio
import threading
from typing import Dict, List, Optional, Set, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from prs.tui.data.data_manager import TUIDataManager, TUIDataUpdate


class UpdatePriority(Enum):
    """Priority levels for updates."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class UpdateTask:
    """Represents an update task to be executed."""
    id: str
    priority: UpdatePriority
    update_type: str
    pr_id: Optional[int]
    callback: Callable
    scheduled_time: datetime
    retry_count: int = 0
    max_retries: int = 3


class UpdateService:
    """
    Manages real-time updates for the TUI interface.
    
    This service handles:
    - Timer-based refresh for CI status changes
    - Reactive updates when data changes
    - Priority-based update scheduling
    - Background update processing without blocking UI
    """
    
    def __init__(self, data_manager: TUIDataManager):
        self.data_manager = data_manager
        
        # Update scheduling
        self._update_queue: List[UpdateTask] = []
        self._running_tasks: Set[str] = set()
        self._task_counter = 0
        
        # Configuration
        self._watch_mode = False
        self._watch_interval = 10  # seconds
        self._ci_check_interval = 30  # seconds
        self._priority_multipliers = {
            UpdatePriority.LOW: 1.0,
            UpdatePriority.NORMAL: 0.8,
            UpdatePriority.HIGH: 0.5,
            UpdatePriority.CRITICAL: 0.1
        }
        
        # Threading
        self._update_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        
        # Callbacks
        self._update_callbacks: List[Callable[[TUIDataUpdate], None]] = []
        
        # Register with data manager
        self.data_manager.add_update_callback(self._on_data_update)
    
    def add_update_callback(self, callback: Callable[[TUIDataUpdate], None]):
        """Add a callback for update notifications."""
        self._update_callbacks.append(callback)
    
    def remove_update_callback(self, callback: Callable[[TUIDataUpdate], None]):
        """Remove an update callback."""
        if callback in self._update_callbacks:
            self._update_callbacks.remove(callback)
    
    def _notify_callbacks(self, update: TUIDataUpdate):
        """Notify all registered callbacks."""
        for callback in self._update_callbacks:
            try:
                callback(update)
            except Exception:
                # Don't let callback errors break the service
                pass
    
    def _on_data_update(self, update: TUIDataUpdate):
        """Handle data updates from the data manager."""
        # Forward the update to our callbacks
        self._notify_callbacks(update)
        
        # Schedule follow-up updates if needed
        if update.update_type == 'pr_update' and update.pr_id:
            # Schedule a CI check for updated PRs
            self.schedule_ci_check(update.pr_id, priority=UpdatePriority.NORMAL)
    
    def start(self):
        """Start the update service."""
        if self._update_thread and self._update_thread.is_alive():
            return
        
        self._stop_event.clear()
        self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self._update_thread.start()
    
    def stop(self):
        """Stop the update service."""
        self._stop_event.set()
        if self._update_thread:
            self._update_thread.join(timeout=5.0)
    
    def _update_loop(self):
        """Main update processing loop."""
        while not self._stop_event.is_set():
            try:
                self._process_updates()
                self._stop_event.wait(1.0)  # Check every second
            except Exception:
                # Don't let errors break the update loop
                self._stop_event.wait(5.0)  # Wait longer on error
    
    def _process_updates(self):
        """Process pending updates."""
        with self._lock:
            if not self._update_queue:
                return
            
            # Sort by priority and scheduled time
            self._update_queue.sort(key=lambda t: (
                t.priority.value,
                t.scheduled_time.timestamp()
            ))
            
            # Process due tasks
            now = datetime.now()
            tasks_to_process = []
            
            for task in self._update_queue[:]:
                if task.scheduled_time <= now and task.id not in self._running_tasks:
                    tasks_to_process.append(task)
                    self._update_queue.remove(task)
                    self._running_tasks.add(task.id)
                    
                    # Limit concurrent tasks
                    if len(tasks_to_process) >= 3:
                        break
        
        # Execute tasks in separate threads
        for task in tasks_to_process:
            threading.Thread(
                target=self._execute_task,
                args=(task,),
                daemon=True
            ).start()
    
    def _execute_task(self, task: UpdateTask):
        """Execute an update task."""
        try:
            task.callback()
        except Exception as e:
            # Handle task failure
            if task.retry_count < task.max_retries:
                # Reschedule with exponential backoff
                delay = (2 ** task.retry_count) * 5  # 5, 10, 20 seconds
                task.retry_count += 1
                task.scheduled_time = datetime.now() + timedelta(seconds=delay)
                
                with self._lock:
                    self._update_queue.append(task)
        finally:
            with self._lock:
                self._running_tasks.discard(task.id)
    
    def _generate_task_id(self) -> str:
        """Generate a unique task ID."""
        self._task_counter += 1
        return f"task_{self._task_counter}_{datetime.now().timestamp()}"
    
    def schedule_pr_refresh(self, pr_id: Optional[int] = None, 
                           priority: UpdatePriority = UpdatePriority.NORMAL,
                           delay_seconds: int = 0):
        """Schedule a PR data refresh."""
        task = UpdateTask(
            id=self._generate_task_id(),
            priority=priority,
            update_type='pr_refresh',
            pr_id=pr_id,
            callback=lambda: asyncio.run(self.data_manager.refresh_pr_data(pr_id)),
            scheduled_time=datetime.now() + timedelta(seconds=delay_seconds)
        )
        
        with self._lock:
            self._update_queue.append(task)
    
    def schedule_ci_check(self, pr_id: int, 
                         priority: UpdatePriority = UpdatePriority.NORMAL,
                         delay_seconds: int = 0):
        """Schedule a CI status check for a specific PR."""
        task = UpdateTask(
            id=self._generate_task_id(),
            priority=priority,
            update_type='ci_check',
            pr_id=pr_id,
            callback=lambda: asyncio.run(self.data_manager.refresh_pr_data(pr_id)),
            scheduled_time=datetime.now() + timedelta(seconds=delay_seconds)
        )
        
        with self._lock:
            self._update_queue.append(task)
    
    def schedule_full_refresh(self, priority: UpdatePriority = UpdatePriority.LOW,
                            delay_seconds: int = 0):
        """Schedule a full data refresh."""
        task = UpdateTask(
            id=self._generate_task_id(),
            priority=priority,
            update_type='full_refresh',
            pr_id=None,
            callback=lambda: asyncio.run(self.data_manager.refresh_pr_data()),
            scheduled_time=datetime.now() + timedelta(seconds=delay_seconds)
        )
        
        with self._lock:
            self._update_queue.append(task)
    
    def start_watch_mode(self, interval: int = 10):
        """Start watch mode with automatic updates."""
        self._watch_mode = True
        self._watch_interval = interval
        
        # Start data manager auto-refresh
        self.data_manager.start_auto_refresh(interval)
        
        # Schedule periodic full refreshes
        self._schedule_periodic_refresh()
    
    def stop_watch_mode(self):
        """Stop watch mode."""
        self._watch_mode = False
        self.data_manager.stop_auto_refresh()
    
    def _schedule_periodic_refresh(self):
        """Schedule periodic refresh in watch mode."""
        if not self._watch_mode:
            return
        
        # Schedule next refresh
        self.schedule_full_refresh(
            priority=UpdatePriority.LOW,
            delay_seconds=self._watch_interval
        )
        
        # Schedule the next periodic refresh
        threading.Timer(
            self._watch_interval,
            self._schedule_periodic_refresh
        ).start()
    
    def start_ci_monitoring(self, interval: int = 30):
        """Start continuous CI status monitoring."""
        self._ci_check_interval = interval
        self._schedule_ci_monitoring()
    
    def _schedule_ci_monitoring(self):
        """Schedule CI monitoring tasks."""
        if self._stop_event.is_set():
            return
        
        # Get all PRs and schedule CI checks
        prs = self.data_manager.get_prs()
        for pr in prs:
            # Check if PR has pending CI
            if (hasattr(pr, 'ci_data') and pr.ci_data and 
                pr.ci_data.pending_workflows > 0):
                
                self.schedule_ci_check(
                    pr.id,
                    priority=UpdatePriority.HIGH,
                    delay_seconds=5  # Check pending CI more frequently
                )
        
        # Schedule next monitoring cycle
        threading.Timer(
            self._ci_check_interval,
            self._schedule_ci_monitoring
        ).start()
    
    def force_refresh_pr(self, pr_id: int):
        """Force an immediate refresh of a specific PR."""
        self.schedule_pr_refresh(
            pr_id=pr_id,
            priority=UpdatePriority.CRITICAL,
            delay_seconds=0
        )
    
    def force_refresh_all(self):
        """Force an immediate refresh of all data."""
        self.schedule_full_refresh(
            priority=UpdatePriority.CRITICAL,
            delay_seconds=0
        )
    
    def get_status(self) -> Dict:
        """Get service status information."""
        with self._lock:
            return {
                'running': self._update_thread and self._update_thread.is_alive(),
                'watch_mode': self._watch_mode,
                'watch_interval': self._watch_interval,
                'ci_check_interval': self._ci_check_interval,
                'pending_tasks': len(self._update_queue),
                'running_tasks': len(self._running_tasks),
                'task_types': {
                    task.update_type: sum(1 for t in self._update_queue if t.update_type == task.update_type)
                    for task in self._update_queue
                }
            }
    
    def clear_pending_tasks(self):
        """Clear all pending update tasks."""
        with self._lock:
            self._update_queue.clear()
    
    def cleanup(self):
        """Clean up resources."""
        self.stop()
        self.stop_watch_mode()
        self.clear_pending_tasks()
        self._update_callbacks.clear()
        
        # Unregister from data manager
        self.data_manager.remove_update_callback(self._on_data_update)