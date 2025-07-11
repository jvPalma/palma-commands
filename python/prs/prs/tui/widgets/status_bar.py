"""
Status bar widget for the PRS TUI application.

Displays loading status, statistics, and operational information.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from textual.widgets import Static, ProgressBar
from textual.containers import Horizontal
from textual.reactive import reactive


class StatusBarWidget(Static):
    """
    Status bar widget showing application status and statistics.
    
    Displays:
    - Loading indicators and progress
    - Pull request counts and statistics  
    - Filter status and active filters
    - Error messages and warnings
    - Auto-refresh status
    """
    
    # Reactive attributes
    loading = reactive(False)
    progress = reactive(0.0)  # 0.0 to 1.0
    total_prs = reactive(0)
    filtered_prs = reactive(0)
    active_filter = reactive("")
    error_message = reactive("")
    warning_message = reactive("")
    auto_refresh_enabled = reactive(True)
    last_refresh = reactive(None)
    connection_status = reactive("unknown")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.progress_bar: Optional[ProgressBar] = None
    
    def compose(self):
        """Compose the status bar layout.""" 
        with Horizontal(id="status-container"):
            # Loading section
            yield Static(self.render_loading_status(), id="loading-status", classes="status-section")
            
            # Statistics section  
            yield Static(self.render_statistics(), id="statistics", classes="status-section")
            
            # Filter section
            yield Static(self.render_filter_status(), id="filter-status", classes="status-section")
            
            # Messages section
            yield Static(self.render_messages(), id="messages", classes="status-section")
            
            # Auto-refresh section
            yield Static(self.render_refresh_status(), id="refresh-status", classes="status-section")
    
    def render_loading_status(self) -> str:
        """Render the loading status section."""
        if self.loading:
            # Create a simple text-based progress indicator
            if self.progress > 0:
                progress_percent = int(self.progress * 100)
                return f"[yellow]⟳ Loading... {progress_percent}%[/yellow]"
            else:
                return "[yellow]⟳ Loading...[/yellow]"
        else:
            status_icon = {
                "connected": "[green]●[/green]",
                "error": "[red]●[/red]",
                "unknown": "[yellow]●[/yellow]"
            }.get(self.connection_status, "[dim]●[/dim]")
            return f"{status_icon} Ready"
    
    def render_statistics(self) -> str:
        """Render PR statistics."""
        if self.total_prs == 0:
            return "[dim]No PRs[/dim]"
        
        if self.active_filter and self.filtered_prs != self.total_prs:
            return f"[cyan]{self.filtered_prs}[/cyan] of [dim]{self.total_prs}[/dim] PRs"
        else:
            return f"[cyan]{self.total_prs}[/cyan] PRs"
    
    def render_filter_status(self) -> str:
        """Render active filter status."""
        if not self.active_filter:
            return ""
        
        # Truncate long filters for display
        display_filter = self.active_filter
        if len(display_filter) > 30:
            display_filter = display_filter[:27] + "..."
        
        return f"[dim]Filter:[/dim] [yellow]{display_filter}[/yellow]"
    
    def render_messages(self) -> str:
        """Render error and warning messages."""
        if self.error_message:
            # Truncate long error messages
            display_error = self.error_message
            if len(display_error) > 50:
                display_error = display_error[:47] + "..."
            return f"[red]⚠ {display_error}[/red]"
        
        if self.warning_message:
            # Truncate long warning messages
            display_warning = self.warning_message
            if len(display_warning) > 50:
                display_warning = display_warning[:47] + "..."
            return f"[yellow]⚠ {display_warning}[/yellow]"
        
        return ""
    
    def render_refresh_status(self) -> str:
        """Render auto-refresh status."""
        if self.auto_refresh_enabled:
            if self.last_refresh:
                if isinstance(self.last_refresh, datetime):
                    time_str = self.last_refresh.strftime("%H:%M")
                else:
                    time_str = str(self.last_refresh)
                return f"[dim]Auto-refresh: {time_str}[/dim]"
            else:
                return "[dim]Auto-refresh: ON[/dim]"
        else:
            return "[dim]Auto-refresh: OFF[/dim]"
    
    def update_loading(self, loading: bool, progress: float = 0.0) -> None:
        """Update loading status."""
        self.loading = loading
        self.progress = progress
        self.refresh_loading_display()
    
    def update_statistics(self, total: int, filtered: int = None) -> None:
        """Update PR statistics."""
        self.total_prs = total
        self.filtered_prs = filtered if filtered is not None else total
        self.refresh_statistics_display()
    
    def update_filter_status(self, filter_text: str) -> None:
        """Update active filter display."""
        self.active_filter = filter_text
        self.refresh_filter_display()
    
    def show_error(self, message: str) -> None:
        """Show an error message."""
        self.error_message = message
        self.warning_message = ""  # Clear warnings when showing errors
        self.refresh_messages_display()
    
    def show_warning(self, message: str) -> None:
        """Show a warning message."""
        if not self.error_message:  # Only show warnings if no errors
            self.warning_message = message
            self.refresh_messages_display()
    
    def clear_messages(self) -> None:
        """Clear all error and warning messages."""
        self.error_message = ""
        self.warning_message = ""
        self.refresh_messages_display()
    
    def update_refresh_status(self, auto_refresh: bool, last_refresh: Optional[datetime] = None) -> None:
        """Update auto-refresh status."""
        self.auto_refresh_enabled = auto_refresh
        if last_refresh:
            self.last_refresh = last_refresh
        self.refresh_refresh_display()
    
    def update_connection_status(self, status: str) -> None:
        """Update connection status."""
        if status in ("connected", "error", "unknown"):
            self.connection_status = status
            self.refresh_loading_display()
    
    # Refresh methods for individual sections
    def refresh_loading_display(self) -> None:
        """Refresh the loading status display."""
        try:
            loading_widget = self.query_one("#loading-status", Static)
            loading_widget.update(self.render_loading_status())
        except Exception:
            pass
    
    def refresh_statistics_display(self) -> None:
        """Refresh the statistics display."""
        try:
            stats_widget = self.query_one("#statistics", Static)
            stats_widget.update(self.render_statistics())
        except Exception:
            pass
    
    def refresh_filter_display(self) -> None:
        """Refresh the filter status display."""
        try:
            filter_widget = self.query_one("#filter-status", Static)
            filter_widget.update(self.render_filter_status())
        except Exception:
            pass
    
    def refresh_messages_display(self) -> None:
        """Refresh the messages display."""
        try:
            messages_widget = self.query_one("#messages", Static)
            messages_widget.update(self.render_messages())
        except Exception:
            pass
    
    def refresh_refresh_display(self) -> None:
        """Refresh the auto-refresh status display."""
        try:
            refresh_widget = self.query_one("#refresh-status", Static)
            refresh_widget.update(self.render_refresh_status())
        except Exception:
            pass
    
    # Watch methods for reactive attributes
    def watch_loading(self, new_value: bool) -> None:
        """React to loading state changes."""
        self.refresh_loading_display()
    
    def watch_progress(self, new_value: float) -> None:
        """React to progress changes."""
        self.refresh_loading_display()
    
    def watch_total_prs(self, new_value: int) -> None:
        """React to total PR count changes."""
        self.refresh_statistics_display()
    
    def watch_filtered_prs(self, new_value: int) -> None:
        """React to filtered PR count changes."""
        self.refresh_statistics_display()
    
    def watch_active_filter(self, new_value: str) -> None:
        """React to active filter changes."""
        self.refresh_filter_display()
    
    def watch_error_message(self, new_value: str) -> None:
        """React to error message changes."""
        self.refresh_messages_display()
    
    def watch_warning_message(self, new_value: str) -> None:
        """React to warning message changes."""
        self.refresh_messages_display()
    
    def watch_auto_refresh_enabled(self, new_value: bool) -> None:
        """React to auto-refresh toggle changes."""
        self.refresh_refresh_display()
    
    def watch_last_refresh(self, new_value) -> None:
        """React to last refresh time changes."""
        self.refresh_refresh_display()
    
    def watch_connection_status(self, new_value: str) -> None:
        """React to connection status changes."""
        self.refresh_loading_display()


class CompactStatusBarWidget(StatusBarWidget):
    """
    Compact version of the status bar for smaller terminals.
    """
    
    def compose(self):
        """Compose compact status bar layout."""
        with Horizontal(id="status-container"):
            # Essential info only
            yield Static(self.render_compact_status(), id="compact-status", classes="status-section")
    
    def render_compact_status(self) -> str:
        """Render all status info in compact format."""
        parts = []
        
        # Loading/connection status
        if self.loading:
            parts.append("[yellow]⟳[/yellow]")
        else:
            status_icon = {
                "connected": "[green]●[/green]",
                "error": "[red]●[/red]",
                "unknown": "[yellow]●[/yellow]"
            }.get(self.connection_status, "[dim]●[/dim]")
            parts.append(status_icon)
        
        # PR count
        if self.total_prs > 0:
            if self.active_filter and self.filtered_prs != self.total_prs:
                parts.append(f"[cyan]{self.filtered_prs}[/cyan]/[dim]{self.total_prs}[/dim]")
            else:
                parts.append(f"[cyan]{self.total_prs}[/cyan]")
        
        # Active filter indicator
        if self.active_filter:
            parts.append("[yellow]F[/yellow]")
        
        # Auto-refresh indicator
        if self.auto_refresh_enabled:
            parts.append("[dim]↻[/dim]")
        
        # Error indicator
        if self.error_message:
            parts.append("[red]⚠[/red]")
        elif self.warning_message:
            parts.append("[yellow]⚠[/yellow]")
        
        return " ".join(parts) if parts else "[dim]Ready[/dim]"
    
    def refresh_loading_display(self) -> None:
        """Refresh compact display."""
        self.refresh_compact_display()
    
    def refresh_statistics_display(self) -> None:
        """Refresh compact display."""
        self.refresh_compact_display()
    
    def refresh_filter_display(self) -> None:
        """Refresh compact display."""
        self.refresh_compact_display()
    
    def refresh_messages_display(self) -> None:
        """Refresh compact display."""
        self.refresh_compact_display()
    
    def refresh_refresh_display(self) -> None:
        """Refresh compact display."""
        self.refresh_compact_display()
    
    def refresh_compact_display(self) -> None:
        """Refresh the compact status display."""
        try:
            compact_widget = self.query_one("#compact-status", Static)
            compact_widget.update(self.render_compact_status())
        except Exception:
            pass