"""
Build logs viewer widget for TUI.

Provides real-time log viewing, filtering, searching, and analysis
for CI/CD build logs within the terminal interface.
"""

import asyncio
import re
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Static, Label, Input, Button, Select, Switch, ProgressBar
from textual.reactive import reactive
from textual.binding import Binding
from textual.message import Message
from textual.scroll_view import ScrollView
from textual.timer import Timer

from prs.ci_tools.buildkite.client import BuildkiteClient, BuildkiteBuild, BuildkiteJob


class LogLevel(Enum):
    """Log level classifications."""
    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    FATAL = "fatal"


@dataclass
class LogLine:
    """Represents a single log line."""
    number: int
    timestamp: Optional[datetime]
    level: LogLevel
    content: str
    source: str = ""  # job name, step, etc.
    raw_line: str = ""
    
    @property
    def is_error(self) -> bool:
        """Check if this is an error line."""
        return self.level in [LogLevel.ERROR, LogLevel.FATAL]
    
    @property
    def is_warning(self) -> bool:
        """Check if this is a warning line."""
        return self.level == LogLevel.WARN


class LogParser:
    """Parses and classifies log lines."""
    
    # Common log patterns
    TIMESTAMP_PATTERNS = [
        r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)',
        r'(\d{2}:\d{2}:\d{2})',
        r'(\[\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\])',
    ]
    
    LEVEL_PATTERNS = {
        LogLevel.TRACE: [r'\btrace\b', r'\bTRACE\b'],
        LogLevel.DEBUG: [r'\bdebug\b', r'\bDEBUG\b', r'\bDBG\b'],
        LogLevel.INFO: [r'\binfo\b', r'\bINFO\b', r'\binformation\b'],
        LogLevel.WARN: [r'\bwarn\b', r'\bWARN\b', r'\bwarning\b', r'\bWARNING\b'],
        LogLevel.ERROR: [r'\berror\b', r'\bERROR\b', r'\bfail\b', r'\bFAIL\b', r'\bfailed\b'],
        LogLevel.FATAL: [r'\bfatal\b', r'\bFATAL\b', r'\bcritical\b', r'\bCRITICAL\b']
    }
    
    # CI-specific patterns
    ERROR_INDICATORS = [
        r'exit\s+code\s+[1-9]',
        r'command\s+failed',
        r'build\s+failed',
        r'test\s+failed',
        r'compilation\s+error',
        r'syntax\s+error',
        r'permission\s+denied',
        r'no\s+such\s+file',
        r'connection\s+refused',
        r'timeout',
    ]
    
    @classmethod
    def parse_line(cls, line: str, line_number: int) -> LogLine:
        """Parse a single log line."""
        raw_line = line
        content = line.strip()
        
        # Extract timestamp
        timestamp = cls._extract_timestamp(content)
        
        # Determine log level
        level = cls._determine_level(content)
        
        # Extract source if available (job name, step, etc.)
        source = cls._extract_source(content)
        
        return LogLine(
            number=line_number,
            timestamp=timestamp,
            level=level,
            content=content,
            source=source,
            raw_line=raw_line
        )
    
    @classmethod
    def _extract_timestamp(cls, content: str) -> Optional[datetime]:
        """Extract timestamp from log line."""
        for pattern in cls.TIMESTAMP_PATTERNS:
            match = re.search(pattern, content)
            if match:
                timestamp_str = match.group(1)
                try:
                    # Try different timestamp formats
                    formats = [
                        '%Y-%m-%dT%H:%M:%S.%fZ',
                        '%Y-%m-%dT%H:%M:%SZ',
                        '%Y-%m-%d %H:%M:%S.%f',
                        '%Y-%m-%d %H:%M:%S',
                        '%H:%M:%S',
                        '[%Y-%m-%d %H:%M:%S]'
                    ]
                    
                    for fmt in formats:
                        try:
                            return datetime.strptime(timestamp_str, fmt)
                        except ValueError:
                            continue
                except ValueError:
                    pass
        return None
    
    @classmethod
    def _determine_level(cls, content: str) -> LogLevel:
        """Determine log level from content."""
        content_lower = content.lower()
        
        # Check explicit level patterns
        for level, patterns in cls.LEVEL_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return level
        
        # Check error indicators
        for pattern in cls.ERROR_INDICATORS:
            if re.search(pattern, content_lower):
                return LogLevel.ERROR
        
        # Default to info
        return LogLevel.INFO
    
    @classmethod
    def _extract_source(cls, content: str) -> str:
        """Extract source information from log line."""
        # Common source patterns
        patterns = [
            r'\[([^\]]+)\]',  # [source]
            r'(\w+):\s',      # source: 
            r'^(\w+)\s+\|',   # source |
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1)
        
        return ""


class LogFilterWidget(Container):
    """Widget for filtering and searching logs."""
    
    def compose(self) -> ComposeResult:
        """Compose filter widget."""
        with Horizontal(classes="log-filter-bar"):
            yield Input(placeholder="Search logs...", id="search-input")
            yield Select([
                ("All Levels", "all"),
                ("Errors Only", "error"),
                ("Warnings+", "warn"),
                ("Info+", "info")
            ], value="all", id="level-filter")
            yield Switch(id="auto-scroll-switch", value=True)
            yield Label("Auto-scroll", classes="switch-label")
            yield Button("Clear", id="clear-btn", variant="default")
            
    def get_filter_config(self) -> Dict[str, Any]:
        """Get current filter configuration."""
        try:
            search_input = self.query_one("#search-input", Input)
            level_filter = self.query_one("#level-filter", Select)
            auto_scroll = self.query_one("#auto-scroll-switch", Switch)
            
            return {
                "search_text": search_input.value,
                "level_filter": level_filter.value,
                "auto_scroll": auto_scroll.value
            }
        except:
            return {
                "search_text": "",
                "level_filter": "all",
                "auto_scroll": True
            }


class LogDisplayWidget(ScrollView):
    """Widget for displaying filtered logs with syntax highlighting."""
    
    logs = reactive([], recompose=True)
    filter_config = reactive({})
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.filtered_logs: List[LogLine] = []
        self.search_highlights: List[Tuple[int, int]] = []
        
    def render(self) -> str:
        """Render logs with filtering and highlighting."""
        if not self.logs:
            return "No logs available"
        
        # Apply filters
        self._apply_filters()
        
        # Format logs for display
        lines = []
        for log_line in self.filtered_logs:
            formatted_line = self._format_log_line(log_line)
            lines.append(formatted_line)
            
        return "\n".join(lines)
    
    def _apply_filters(self):
        """Apply current filters to logs."""
        filtered = self.logs
        
        # Apply level filter
        level_filter = self.filter_config.get("level_filter", "all")
        if level_filter != "all":
            if level_filter == "error":
                filtered = [log for log in filtered if log.level in [LogLevel.ERROR, LogLevel.FATAL]]
            elif level_filter == "warn":
                filtered = [log for log in filtered if log.level in [LogLevel.WARN, LogLevel.ERROR, LogLevel.FATAL]]
            elif level_filter == "info":
                filtered = [log for log in filtered if log.level != LogLevel.DEBUG and log.level != LogLevel.TRACE]
        
        # Apply search filter
        search_text = self.filter_config.get("search_text", "").strip()
        if search_text:
            search_lower = search_text.lower()
            filtered = [log for log in filtered if search_lower in log.content.lower()]
        
        self.filtered_logs = filtered
    
    def _format_log_line(self, log_line: LogLine) -> str:
        """Format a log line for display with color coding."""
        # Color codes for different log levels
        level_colors = {
            LogLevel.TRACE: "dim",
            LogLevel.DEBUG: "cyan",
            LogLevel.INFO: "white",
            LogLevel.WARN: "yellow",
            LogLevel.ERROR: "red",
            LogLevel.FATAL: "bright_red"
        }
        
        # Build formatted line
        parts = []
        
        # Line number
        parts.append(f"{log_line.number:>4}")
        
        # Timestamp
        if log_line.timestamp:
            time_str = log_line.timestamp.strftime("%H:%M:%S")
            parts.append(f"[{time_str}]")
        
        # Level indicator
        level_char = {
            LogLevel.TRACE: "T",
            LogLevel.DEBUG: "D", 
            LogLevel.INFO: "I",
            LogLevel.WARN: "W",
            LogLevel.ERROR: "E",
            LogLevel.FATAL: "F"
        }
        parts.append(f"[{level_char.get(log_line.level, '?')}]")
        
        # Source
        if log_line.source:
            parts.append(f"[{log_line.source}]")
        
        # Content
        content = log_line.content
        
        # Highlight search terms
        search_text = self.filter_config.get("search_text", "").strip()
        if search_text:
            # Simple highlighting - replace with bold in terminal
            content = re.sub(
                re.escape(search_text),
                f"**{search_text}**",
                content,
                flags=re.IGNORECASE
            )
        
        parts.append(content)
        
        return " ".join(parts)
    
    def scroll_to_bottom(self):
        """Scroll to the bottom of the logs."""
        self.scroll_end()
    
    def add_log_line(self, log_line: LogLine):
        """Add a new log line and auto-scroll if enabled."""
        self.logs = self.logs + [log_line]
        
        if self.filter_config.get("auto_scroll", True):
            self.call_after_refresh(self.scroll_to_bottom)


class LogStatsWidget(Container):
    """Widget displaying log statistics."""
    
    stats = reactive({}, recompose=True)
    
    def compose(self) -> ComposeResult:
        """Compose stats widget."""
        with Container(classes="log-stats"):
            if not self.stats:
                yield Label("No statistics available")
                return
                
            with Horizontal(classes="stats-row"):
                yield Label(f"📊 Lines: {self.stats.get('total_lines', 0)}")
                yield Label(f"❌ Errors: {self.stats.get('error_count', 0)}")
                yield Label(f"⚠️ Warnings: {self.stats.get('warning_count', 0)}")
                yield Label(f"ℹ️ Info: {self.stats.get('info_count', 0)}")
                
            # Error rate progress bar
            if self.stats.get('total_lines', 0) > 0:
                error_rate = self.stats.get('error_count', 0) / self.stats['total_lines']
                yield Label(f"Error Rate: {error_rate:.1%}")
                yield ProgressBar(progress=error_rate, id="error-rate-bar")
    
    def update_stats(self, logs: List[LogLine]):
        """Update statistics from logs."""
        if not logs:
            self.stats = {}
            return
            
        total_lines = len(logs)
        error_count = sum(1 for log in logs if log.level in [LogLevel.ERROR, LogLevel.FATAL])
        warning_count = sum(1 for log in logs if log.level == LogLevel.WARN)
        info_count = sum(1 for log in logs if log.level == LogLevel.INFO)
        debug_count = sum(1 for log in logs if log.level in [LogLevel.DEBUG, LogLevel.TRACE])
        
        self.stats = {
            "total_lines": total_lines,
            "error_count": error_count,
            "warning_count": warning_count,
            "info_count": info_count,
            "debug_count": debug_count
        }


class LogsViewerWidget(Container):
    """
    Main logs viewer widget.
    
    Provides comprehensive log viewing with real-time updates,
    filtering, searching, and analysis capabilities.
    """
    
    BINDINGS = [
        Binding("ctrl+f", "focus_search", "Search"),
        Binding("ctrl+c", "clear_logs", "Clear"),
        Binding("ctrl+s", "save_logs", "Save"),
        Binding("f", "toggle_filter", "Filter"),
        Binding("g", "goto_line", "Go to Line"),
        Binding("e", "show_errors_only", "Errors Only"),
        Binding("escape", "clear_search", "Clear Search"),
    ]
    
    logs = reactive([], recompose=True)
    current_build = reactive(None)
    current_job = reactive(None)
    loading = reactive(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client: Optional[BuildkiteClient] = None
        self._refresh_timer: Optional[Timer] = None
        self._auto_refresh = False
        
    def compose(self) -> ComposeResult:
        """Compose the logs viewer."""
        with Container(id="logs-viewer-container"):
            # Header
            with Horizontal(classes="logs-header"):
                if self.current_build:
                    build_title = f"🔧 Build #{self.current_build.number}"
                    if self.current_job:
                        build_title += f" - {self.current_job.name}"
                    yield Label(build_title, classes="logs-title")
                else:
                    yield Label("📄 Logs Viewer", classes="logs-title")
                    
                if self.loading:
                    yield Label("Loading...", classes="loading-indicator")
                    
                yield Button("🔄 Refresh", id="refresh-btn", variant="primary")
                yield Button("💾 Save", id="save-btn", variant="default")
                
            # Filter bar
            yield LogFilterWidget(id="log-filter")
            
            # Main log display
            with Container(classes="logs-main"):
                yield LogDisplayWidget(id="log-display")
                
            # Stats footer
            yield LogStatsWidget(id="log-stats")
            
    async def load_build_logs(self, client: BuildkiteClient, 
                             build: BuildkiteBuild, job: BuildkiteJob = None):
        """Load logs for a specific build or job."""
        self.client = client
        self.current_build = build
        self.current_job = job
        self.loading = True
        
        try:
            if job:
                # Load specific job logs
                await self._load_job_logs(build, job)
            else:
                # Load all build logs
                await self._load_build_logs(build)
        finally:
            self.loading = False
            
    async def _load_job_logs(self, build: BuildkiteBuild, job: BuildkiteJob):
        """Load logs for a specific job."""
        pipeline_slug = build.pipeline.get('slug', '')
        
        # Get job log content
        log_content = self.client.get_job_log(pipeline_slug, build.number, job.id)
        
        if log_content:
            # Parse log lines
            log_lines = []
            for i, line in enumerate(log_content.split('\n'), 1):
                if line.strip():  # Skip empty lines
                    log_line = LogParser.parse_line(line, i)
                    log_line.source = job.name or "job"
                    log_lines.append(log_line)
                    
            self.logs = log_lines
        else:
            self.logs = []
            
        # Update display
        await self._update_display()
        
    async def _load_build_logs(self, build: BuildkiteBuild):
        """Load logs for all jobs in a build."""
        pipeline_slug = build.pipeline.get('slug', '')
        
        # Get all jobs for the build
        jobs = self.client.get_build_jobs(pipeline_slug, build.number)
        
        all_logs = []
        line_number = 1
        
        for job in jobs:
            # Get job logs
            log_content = self.client.get_job_log(pipeline_slug, build.number, job.id)
            
            if log_content:
                # Add job header
                header_line = LogLine(
                    number=line_number,
                    timestamp=job.started_at,
                    level=LogLevel.INFO,
                    content=f"=== Job: {job.name or 'Unnamed'} ===",
                    source="system"
                )
                all_logs.append(header_line)
                line_number += 1
                
                # Parse job log lines
                for line in log_content.split('\n'):
                    if line.strip():
                        log_line = LogParser.parse_line(line, line_number)
                        log_line.source = job.name or "job"
                        all_logs.append(log_line)
                        line_number += 1
                        
        self.logs = all_logs
        await self._update_display()
        
    async def _update_display(self):
        """Update log display and statistics."""
        # Update display widget
        try:
            display_widget = self.query_one("#log-display", LogDisplayWidget)
            display_widget.logs = self.logs
            
            # Apply current filters
            filter_widget = self.query_one("#log-filter", LogFilterWidget)
            filter_config = filter_widget.get_filter_config()
            display_widget.filter_config = filter_config
            
            display_widget.refresh()
        except:
            pass
            
        # Update statistics
        try:
            stats_widget = self.query_one("#log-stats", LogStatsWidget)
            stats_widget.update_stats(self.logs)
        except:
            pass
            
    def start_auto_refresh(self, interval: float = 5.0):
        """Start automatic log refresh for running builds."""
        if self._refresh_timer:
            self._refresh_timer.stop()
            
        self._auto_refresh = True
        self._refresh_timer = self.set_interval(interval, self._auto_refresh_callback)
        
    def stop_auto_refresh(self):
        """Stop automatic log refresh."""
        self._auto_refresh = False
        if self._refresh_timer:
            self._refresh_timer.stop()
            self._refresh_timer = None
            
    async def _auto_refresh_callback(self):
        """Auto-refresh callback for live logs."""
        if (self._auto_refresh and self.current_build and 
            self.current_build.state in ["running", "scheduled"]):
            await self._refresh_logs()
            
    async def _refresh_logs(self):
        """Refresh current logs."""
        if self.current_build and self.client:
            if self.current_job:
                await self._load_job_logs(self.current_build, self.current_job)
            else:
                await self._load_build_logs(self.current_build)
                
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "search-input":
            asyncio.create_task(self._update_display())
            
    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle filter changes."""
        if event.select.id == "level-filter":
            asyncio.create_task(self._update_display())
            
    def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handle switch changes."""
        if event.switch.id == "auto-scroll-switch":
            # Update auto-scroll behavior
            pass
            
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "refresh-btn":
            asyncio.create_task(self._refresh_logs())
        elif event.button.id == "save-btn":
            self._save_logs()
        elif event.button.id == "clear-btn":
            self.logs = []
            asyncio.create_task(self._update_display())
            
    def _save_logs(self):
        """Save current logs to file."""
        if not self.logs:
            return
            
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if self.current_build:
            filename = f"build_{self.current_build.number}_{timestamp}.log"
            if self.current_job:
                job_name = self.current_job.name or "job"
                filename = f"build_{self.current_build.number}_{job_name}_{timestamp}.log"
        else:
            filename = f"logs_{timestamp}.log"
            
        try:
            with open(filename, 'w') as f:
                for log_line in self.logs:
                    f.write(f"{log_line.raw_line}\n")
            self.post_message(self.LogsSaved(filename))
        except Exception as e:
            self.post_message(self.SaveFailed(str(e)))
            
    # Action handlers
    def action_focus_search(self) -> None:
        """Focus the search input."""
        try:
            search_input = self.query_one("#search-input", Input)
            search_input.focus()
        except:
            pass
            
    def action_clear_logs(self) -> None:
        """Clear all logs."""
        self.logs = []
        asyncio.create_task(self._update_display())
        
    def action_save_logs(self) -> None:
        """Save logs to file."""
        self._save_logs()
        
    def action_toggle_filter(self) -> None:
        """Cycle through filter levels."""
        try:
            level_filter = self.query_one("#level-filter", Select)
            options = ["all", "error", "warn", "info"]
            current_index = options.index(level_filter.value)
            next_index = (current_index + 1) % len(options)
            level_filter.value = options[next_index]
        except:
            pass
            
    def action_goto_line(self) -> None:
        """Go to specific line number."""
        # TODO: Implement go to line dialog
        pass
        
    def action_show_errors_only(self) -> None:
        """Show only error lines."""
        try:
            level_filter = self.query_one("#level-filter", Select)
            level_filter.value = "error"
        except:
            pass
            
    def action_clear_search(self) -> None:
        """Clear search input."""
        try:
            search_input = self.query_one("#search-input", Input)
            search_input.value = ""
        except:
            pass
            
    def on_mount(self) -> None:
        """Handle widget mounting."""
        # Start auto-refresh for running builds
        if (self.current_build and 
            self.current_build.state in ["running", "scheduled"]):
            self.start_auto_refresh()
            
    def on_unmount(self) -> None:
        """Handle widget unmounting."""
        self.stop_auto_refresh()
        
    class LogsSaved(Message):
        def __init__(self, filename: str):
            super().__init__()
            self.filename = filename
            
    class SaveFailed(Message):
        def __init__(self, error: str):
            super().__init__()
            self.error = error