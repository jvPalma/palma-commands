"""
Smart notifications service for PRS TUI.
Provides configurable alerts for PR events with multiple delivery channels.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import threading
import queue
import subprocess
import requests
from pathlib import Path

from ...ci_tools.base.models import BuildStatus
from ...core.models import PullRequest
from ..events.events import CIStatusUpdateEvent, PRUpdateEvent


class NotificationChannel(Enum):
    """Available notification channels."""
    DESKTOP = "desktop"
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SOUND = "sound"
    TUI_TOAST = "tui_toast"


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class NotificationEventType(Enum):
    """Types of events that can trigger notifications."""
    CI_FAILURE = "ci_failure"
    CI_SUCCESS = "ci_success"
    REVIEW_REQUESTED = "review_requested"
    REVIEW_APPROVED = "review_approved"
    REVIEW_REJECTED = "review_rejected"
    PR_MERGED = "pr_merged"
    PR_CLOSED = "pr_closed"
    COMMENT_ADDED = "comment_added"
    MENTION = "mention"
    CUSTOM = "custom"


@dataclass
class NotificationRule:
    """Configuration for notification rules."""
    id: str
    name: str
    event_types: List[NotificationEventType]
    channels: List[NotificationChannel]
    priority: NotificationPriority
    conditions: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    quiet_hours: Optional[Dict[str, str]] = None  # {"start": "22:00", "end": "08:00"}
    rate_limit: Optional[int] = None  # Max notifications per hour
    filters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationMessage:
    """Individual notification message."""
    id: str
    title: str
    message: str
    priority: NotificationPriority
    event_type: NotificationEventType
    timestamp: datetime
    pr_id: Optional[int] = None
    author: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    channels: List[NotificationChannel] = field(default_factory=list)
    delivered: Set[NotificationChannel] = field(default_factory=set)
    failed: Set[NotificationChannel] = field(default_factory=set)


@dataclass
class NotificationConfig:
    """Global notification configuration."""
    enabled: bool = True
    default_channels: List[NotificationChannel] = field(default_factory=lambda: [NotificationChannel.TUI_TOAST])
    sound_enabled: bool = True
    sound_file: Optional[str] = None
    desktop_timeout: int = 5000  # milliseconds
    email_smtp_server: Optional[str] = None
    email_smtp_port: int = 587
    email_username: Optional[str] = None
    email_password: Optional[str] = None
    email_from: Optional[str] = None
    email_to: List[str] = field(default_factory=list)
    slack_webhook_url: Optional[str] = None
    slack_channel: Optional[str] = None
    slack_username: str = "PRS Bot"
    webhook_urls: List[str] = field(default_factory=list)
    max_queue_size: int = 1000
    retry_attempts: int = 3
    retry_delay: int = 5  # seconds


class NotificationService:
    """
    Smart notifications service for PRS TUI.
    
    Features:
    - Multiple notification channels (desktop, email, Slack, webhook)
    - Configurable rules and filters
    - Rate limiting and quiet hours
    - Priority-based delivery
    - Retry logic for failed deliveries
    - Custom event types and conditions
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or str(Path.home() / ".prs" / "notifications.json")
        self.config = NotificationConfig()
        self.rules: List[NotificationRule] = []
        self.notification_queue = queue.Queue(maxsize=1000)
        self.delivery_stats: Dict[str, int] = {"sent": 0, "failed": 0, "queued": 0}
        self.rate_limits: Dict[str, List[datetime]] = {}
        
        # Event callbacks
        self.tui_callback: Optional[Callable[[NotificationMessage], None]] = None
        
        # Background workers
        self.worker_thread: Optional[threading.Thread] = None
        self.running = False
        
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.load_config()
        self.setup_default_rules()
    
    def load_config(self) -> None:
        """Load notification configuration from file."""
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    self.config = NotificationConfig(**data.get('config', {}))
                    
                    # Load rules
                    self.rules = []
                    for rule_data in data.get('rules', []):
                        rule = NotificationRule(
                            id=rule_data['id'],
                            name=rule_data['name'],
                            event_types=[NotificationEventType(t) for t in rule_data['event_types']],
                            channels=[NotificationChannel(c) for c in rule_data['channels']],
                            priority=NotificationPriority(rule_data['priority']),
                            conditions=rule_data.get('conditions', {}),
                            enabled=rule_data.get('enabled', True),
                            quiet_hours=rule_data.get('quiet_hours'),
                            rate_limit=rule_data.get('rate_limit'),
                            filters=rule_data.get('filters', {})
                        )
                        self.rules.append(rule)
                        
        except Exception as e:
            self.logger.error(f"Error loading notification config: {e}")
    
    def save_config(self) -> None:
        """Save notification configuration to file."""
        try:
            Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'config': {
                    'enabled': self.config.enabled,
                    'default_channels': [c.value for c in self.config.default_channels],
                    'sound_enabled': self.config.sound_enabled,
                    'sound_file': self.config.sound_file,
                    'desktop_timeout': self.config.desktop_timeout,
                    'email_smtp_server': self.config.email_smtp_server,
                    'email_smtp_port': self.config.email_smtp_port,
                    'email_username': self.config.email_username,
                    'email_from': self.config.email_from,
                    'email_to': self.config.email_to,
                    'slack_webhook_url': self.config.slack_webhook_url,
                    'slack_channel': self.config.slack_channel,
                    'slack_username': self.config.slack_username,
                    'webhook_urls': self.config.webhook_urls,
                    'max_queue_size': self.config.max_queue_size,
                    'retry_attempts': self.config.retry_attempts,
                    'retry_delay': self.config.retry_delay
                },
                'rules': [
                    {
                        'id': rule.id,
                        'name': rule.name,
                        'event_types': [t.value for t in rule.event_types],
                        'channels': [c.value for c in rule.channels],
                        'priority': rule.priority.value,
                        'conditions': rule.conditions,
                        'enabled': rule.enabled,
                        'quiet_hours': rule.quiet_hours,
                        'rate_limit': rule.rate_limit,
                        'filters': rule.filters
                    }
                    for rule in self.rules
                ]
            }
            
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving notification config: {e}")
    
    def setup_default_rules(self) -> None:
        """Set up default notification rules."""
        if not self.rules:
            default_rules = [
                NotificationRule(
                    id="ci_failure",
                    name="CI Failure Alert",
                    event_types=[NotificationEventType.CI_FAILURE],
                    channels=[NotificationChannel.DESKTOP, NotificationChannel.TUI_TOAST],
                    priority=NotificationPriority.HIGH,
                    conditions={"author": "me"},
                    rate_limit=5
                ),
                NotificationRule(
                    id="review_requested",
                    name="Review Requested",
                    event_types=[NotificationEventType.REVIEW_REQUESTED],
                    channels=[NotificationChannel.TUI_TOAST],
                    priority=NotificationPriority.MEDIUM,
                    filters={"exclude_authors": ["bot"]}
                ),
                NotificationRule(
                    id="pr_merged",
                    name="PR Merged",
                    event_types=[NotificationEventType.PR_MERGED],
                    channels=[NotificationChannel.DESKTOP, NotificationChannel.SOUND],
                    priority=NotificationPriority.MEDIUM,
                    conditions={"author": "me"}
                ),
                NotificationRule(
                    id="mention",
                    name="Mentioned in PR",
                    event_types=[NotificationEventType.MENTION],
                    channels=[NotificationChannel.DESKTOP, NotificationChannel.TUI_TOAST],
                    priority=NotificationPriority.HIGH
                )
            ]
            
            self.rules.extend(default_rules)
            self.save_config()
    
    def start(self) -> None:
        """Start the notification service."""
        if self.running:
            return
        
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
        self.logger.info("Notification service started")
    
    def stop(self) -> None:
        """Stop the notification service."""
        self.running = False
        
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        
        self.logger.info("Notification service stopped")
    
    def set_tui_callback(self, callback: Callable[[NotificationMessage], None]) -> None:
        """Set callback for TUI notifications."""
        self.tui_callback = callback
    
    def handle_ci_status_update(self, event: CIStatusUpdateEvent) -> None:
        """Handle CI status update events."""
        if event.status == BuildStatus.FAILED:
            self.send_notification(
                title=f"CI Failed - PR #{event.pr_id}",
                message=f"CI checks failed for PR #{event.pr_id}",
                event_type=NotificationEventType.CI_FAILURE,
                priority=NotificationPriority.HIGH,
                pr_id=event.pr_id,
                data={"status": event.status.value, "checks": len(event.checks)}
            )
        elif event.status == BuildStatus.PASSED:
            self.send_notification(
                title=f"CI Passed - PR #{event.pr_id}",
                message=f"All CI checks passed for PR #{event.pr_id}",
                event_type=NotificationEventType.CI_SUCCESS,
                priority=NotificationPriority.LOW,
                pr_id=event.pr_id,
                data={"status": event.status.value, "checks": len(event.checks)}
            )
    
    def handle_pr_update(self, event: PRUpdateEvent) -> None:
        """Handle PR update events."""
        if event.update_type == "merged":
            self.send_notification(
                title=f"PR Merged - #{event.pr_id}",
                message=f"PR #{event.pr_id} has been merged",
                event_type=NotificationEventType.PR_MERGED,
                priority=NotificationPriority.MEDIUM,
                pr_id=event.pr_id,
                data=event.data
            )
        elif event.update_type == "review_requested":
            self.send_notification(
                title=f"Review Requested - #{event.pr_id}",
                message=f"Your review is requested for PR #{event.pr_id}",
                event_type=NotificationEventType.REVIEW_REQUESTED,
                priority=NotificationPriority.MEDIUM,
                pr_id=event.pr_id,
                data=event.data
            )
    
    def send_notification(self, title: str, message: str, 
                         event_type: NotificationEventType,
                         priority: NotificationPriority = NotificationPriority.MEDIUM,
                         pr_id: Optional[int] = None,
                         author: Optional[str] = None,
                         data: Optional[Dict[str, Any]] = None) -> str:
        """Send a notification through configured channels."""
        if not self.config.enabled:
            return ""
        
        notification = NotificationMessage(
            id=f"notif_{datetime.now().timestamp()}",
            title=title,
            message=message,
            priority=priority,
            event_type=event_type,
            timestamp=datetime.now(),
            pr_id=pr_id,
            author=author,
            data=data or {}
        )
        
        # Find matching rules
        matching_rules = self._find_matching_rules(notification)
        
        if not matching_rules:
            # Use default channels
            notification.channels = self.config.default_channels
        else:
            # Combine channels from all matching rules
            channels = set()
            for rule in matching_rules:
                channels.update(rule.channels)
            notification.channels = list(channels)
        
        # Check rate limits and quiet hours
        if self._should_send_notification(notification, matching_rules):
            try:
                self.notification_queue.put(notification, timeout=1)
                self.delivery_stats["queued"] += 1
                return notification.id
            except queue.Full:
                self.logger.warning("Notification queue full, dropping message")
                return ""
        
        return ""
    
    def _find_matching_rules(self, notification: NotificationMessage) -> List[NotificationRule]:
        """Find rules that match a notification."""
        matching_rules = []
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            # Check event type
            if notification.event_type not in rule.event_types:
                continue
            
            # Check conditions
            if not self._check_conditions(notification, rule.conditions):
                continue
            
            # Check filters
            if not self._check_filters(notification, rule.filters):
                continue
            
            matching_rules.append(rule)
        
        return matching_rules
    
    def _check_conditions(self, notification: NotificationMessage, conditions: Dict[str, Any]) -> bool:
        """Check if notification matches rule conditions."""
        for key, value in conditions.items():
            if key == "author" and value == "me":
                # This would check if the PR author is the current user
                # Implementation would depend on configuration
                continue
            elif key == "priority":
                if notification.priority != NotificationPriority(value):
                    return False
            elif key == "pr_id":
                if notification.pr_id != value:
                    return False
            
        return True
    
    def _check_filters(self, notification: NotificationMessage, filters: Dict[str, Any]) -> bool:
        """Check if notification passes rule filters."""
        for key, value in filters.items():
            if key == "exclude_authors":
                if notification.author and notification.author in value:
                    return False
            elif key == "include_authors":
                if notification.author and notification.author not in value:
                    return False
            elif key == "min_priority":
                min_priority = NotificationPriority(value)
                priority_order = [NotificationPriority.LOW, NotificationPriority.MEDIUM, 
                                NotificationPriority.HIGH, NotificationPriority.URGENT]
                if priority_order.index(notification.priority) < priority_order.index(min_priority):
                    return False
        
        return True
    
    def _should_send_notification(self, notification: NotificationMessage, rules: List[NotificationRule]) -> bool:
        """Check if notification should be sent based on rate limits and quiet hours."""
        # Check quiet hours
        for rule in rules:
            if rule.quiet_hours and self._is_quiet_hours(rule.quiet_hours):
                if notification.priority not in [NotificationPriority.HIGH, NotificationPriority.URGENT]:
                    return False
        
        # Check rate limits
        for rule in rules:
            if rule.rate_limit and self._is_rate_limited(rule.id, rule.rate_limit):
                return False
        
        return True
    
    def _is_quiet_hours(self, quiet_hours: Dict[str, str]) -> bool:
        """Check if current time is within quiet hours."""
        try:
            now = datetime.now().time()
            start_time = datetime.strptime(quiet_hours["start"], "%H:%M").time()
            end_time = datetime.strptime(quiet_hours["end"], "%H:%M").time()
            
            if start_time <= end_time:
                return start_time <= now <= end_time
            else:
                return now >= start_time or now <= end_time
        except:
            return False
    
    def _is_rate_limited(self, rule_id: str, limit: int) -> bool:
        """Check if rule is rate limited."""
        if rule_id not in self.rate_limits:
            self.rate_limits[rule_id] = []
        
        now = datetime.now()
        cutoff = now - timedelta(hours=1)
        
        # Remove old entries
        self.rate_limits[rule_id] = [
            timestamp for timestamp in self.rate_limits[rule_id]
            if timestamp > cutoff
        ]
        
        # Check if we've exceeded the limit
        if len(self.rate_limits[rule_id]) >= limit:
            return True
        
        # Add current timestamp
        self.rate_limits[rule_id].append(now)
        return False
    
    def _worker_loop(self) -> None:
        """Background worker loop for processing notifications."""
        while self.running:
            try:
                notification = self.notification_queue.get(timeout=1)
                self._deliver_notification(notification)
                self.notification_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error in notification worker: {e}")
    
    def _deliver_notification(self, notification: NotificationMessage) -> None:
        """Deliver a notification to all configured channels."""
        for channel in notification.channels:
            try:
                success = False
                
                if channel == NotificationChannel.DESKTOP:
                    success = self._send_desktop_notification(notification)
                elif channel == NotificationChannel.TUI_TOAST:
                    success = self._send_tui_notification(notification)
                elif channel == NotificationChannel.SOUND:
                    success = self._play_notification_sound(notification)
                elif channel == NotificationChannel.EMAIL:
                    success = self._send_email_notification(notification)
                elif channel == NotificationChannel.SLACK:
                    success = self._send_slack_notification(notification)
                elif channel == NotificationChannel.WEBHOOK:
                    success = self._send_webhook_notification(notification)
                
                if success:
                    notification.delivered.add(channel)
                    self.delivery_stats["sent"] += 1
                else:
                    notification.failed.add(channel)
                    self.delivery_stats["failed"] += 1
                    
            except Exception as e:
                self.logger.error(f"Error delivering notification to {channel.value}: {e}")
                notification.failed.add(channel)
                self.delivery_stats["failed"] += 1
    
    def _send_desktop_notification(self, notification: NotificationMessage) -> bool:
        """Send desktop notification."""
        try:
            # Use different commands based on platform
            if Path("/usr/bin/notify-send").exists():
                # Linux
                cmd = [
                    "notify-send",
                    f"--expire-time={self.config.desktop_timeout}",
                    f"--urgency={'critical' if notification.priority == NotificationPriority.URGENT else 'normal'}",
                    notification.title,
                    notification.message
                ]
            elif Path("/usr/local/bin/terminal-notifier").exists():
                # macOS
                cmd = [
                    "terminal-notifier",
                    "-title", notification.title,
                    "-message", notification.message,
                    "-timeout", str(self.config.desktop_timeout // 1000)
                ]
            else:
                return False
            
            subprocess.run(cmd, check=True, capture_output=True)
            return True
            
        except Exception as e:
            self.logger.error(f"Desktop notification failed: {e}")
            return False
    
    def _send_tui_notification(self, notification: NotificationMessage) -> bool:
        """Send TUI toast notification."""
        try:
            if self.tui_callback:
                self.tui_callback(notification)
                return True
            return False
        except Exception as e:
            self.logger.error(f"TUI notification failed: {e}")
            return False
    
    def _play_notification_sound(self, notification: NotificationMessage) -> bool:
        """Play notification sound."""
        try:
            if not self.config.sound_enabled:
                return True
            
            sound_file = self.config.sound_file
            if not sound_file:
                # Use system default sound
                if Path("/usr/bin/paplay").exists():
                    subprocess.run(["paplay", "/usr/share/sounds/alsa/Front_Left.wav"], 
                                 check=True, capture_output=True)
                elif Path("/usr/bin/afplay").exists():
                    subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], 
                                 check=True, capture_output=True)
                else:
                    return False
            else:
                # Use custom sound file
                if Path(sound_file).exists():
                    subprocess.run(["paplay", sound_file], check=True, capture_output=True)
                else:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Sound notification failed: {e}")
            return False
    
    def _send_email_notification(self, notification: NotificationMessage) -> bool:
        """Send email notification."""
        try:
            if not all([self.config.email_smtp_server, self.config.email_username, 
                       self.config.email_from, self.config.email_to]):
                return False
            
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart()
            msg['From'] = self.config.email_from
            msg['To'] = ', '.join(self.config.email_to)
            msg['Subject'] = notification.title
            
            body = f"{notification.message}\n\n"
            if notification.pr_id:
                body += f"PR #{notification.pr_id}\n"
            body += f"Time: {notification.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.config.email_smtp_server, self.config.email_smtp_port)
            server.starttls()
            server.login(self.config.email_username, self.config.email_password)
            server.send_message(msg)
            server.quit()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Email notification failed: {e}")
            return False
    
    def _send_slack_notification(self, notification: NotificationMessage) -> bool:
        """Send Slack notification."""
        try:
            if not self.config.slack_webhook_url:
                return False
            
            payload = {
                "username": self.config.slack_username,
                "channel": self.config.slack_channel,
                "text": f"*{notification.title}*\n{notification.message}",
                "attachments": [
                    {
                        "color": self._get_slack_color(notification.priority),
                        "fields": [
                            {"title": "Priority", "value": notification.priority.value, "short": True},
                            {"title": "Time", "value": notification.timestamp.strftime('%Y-%m-%d %H:%M:%S'), "short": True}
                        ]
                    }
                ]
            }
            
            if notification.pr_id:
                payload["attachments"][0]["fields"].append(
                    {"title": "PR", "value": f"#{notification.pr_id}", "short": True}
                )
            
            response = requests.post(
                self.config.slack_webhook_url,
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            self.logger.error(f"Slack notification failed: {e}")
            return False
    
    def _send_webhook_notification(self, notification: NotificationMessage) -> bool:
        """Send webhook notification."""
        try:
            if not self.config.webhook_urls:
                return False
            
            payload = {
                "id": notification.id,
                "title": notification.title,
                "message": notification.message,
                "priority": notification.priority.value,
                "event_type": notification.event_type.value,
                "timestamp": notification.timestamp.isoformat(),
                "pr_id": notification.pr_id,
                "author": notification.author,
                "data": notification.data
            }
            
            success = True
            for url in self.config.webhook_urls:
                try:
                    response = requests.post(url, json=payload, timeout=10)
                    if response.status_code != 200:
                        success = False
                except Exception as e:
                    self.logger.error(f"Webhook notification failed for {url}: {e}")
                    success = False
            
            return success
            
        except Exception as e:
            self.logger.error(f"Webhook notification failed: {e}")
            return False
    
    def _get_slack_color(self, priority: NotificationPriority) -> str:
        """Get Slack color for priority."""
        color_map = {
            NotificationPriority.LOW: "good",
            NotificationPriority.MEDIUM: "warning",
            NotificationPriority.HIGH: "danger",
            NotificationPriority.URGENT: "danger"
        }
        return color_map.get(priority, "good")
    
    def add_rule(self, rule: NotificationRule) -> None:
        """Add a new notification rule."""
        self.rules.append(rule)
        self.save_config()
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a notification rule."""
        for i, rule in enumerate(self.rules):
            if rule.id == rule_id:
                del self.rules[i]
                self.save_config()
                return True
        return False
    
    def get_rules(self) -> List[NotificationRule]:
        """Get all notification rules."""
        return self.rules.copy()
    
    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """Update a notification rule."""
        for rule in self.rules:
            if rule.id == rule_id:
                for key, value in updates.items():
                    if hasattr(rule, key):
                        setattr(rule, key, value)
                self.save_config()
                return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get notification service statistics."""
        return {
            "enabled": self.config.enabled,
            "rules_count": len(self.rules),
            "active_rules": len([r for r in self.rules if r.enabled]),
            "queue_size": self.notification_queue.qsize(),
            "delivery_stats": self.delivery_stats.copy(),
            "rate_limits": {rule_id: len(timestamps) for rule_id, timestamps in self.rate_limits.items()},
            "channels_configured": len(self.config.default_channels)
        }
    
    def test_notification(self, channel: NotificationChannel) -> bool:
        """Test a notification channel."""
        test_notification = NotificationMessage(
            id="test",
            title="PRS Test Notification",
            message="This is a test notification from PRS",
            priority=NotificationPriority.LOW,
            event_type=NotificationEventType.CUSTOM,
            timestamp=datetime.now(),
            channels=[channel]
        )
        
        self._deliver_notification(test_notification)
        return channel in test_notification.delivered