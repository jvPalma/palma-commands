"""
Footer widget for the PRS TUI application.

Displays status information, keybindings, and application state.
"""

from typing import Dict, List, Optional
from datetime import datetime

from textual.widgets import Static
from textual.containers import Horizontal
from textual.reactive import reactive


class FooterWidget(Static):
    """
    Footer widget displaying status and keybindings.
    
    Shows:
    - Current mode/context
    - Active keybindings for current context
    - Loading indicators
    - Error messages
    - Statistics (PR counts, etc.)
    """
    
    # Reactive attributes
    loading = reactive(False)
    error_message = reactive("")
    current_mode = reactive("browse")  # "browse", "filter", "help", "config"
    pr_count = reactive(0)
    filtered_count = reactive(0)
    auto_refresh = reactive(True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def compose(self):
        """Compose the footer layout."""
        with Horizontal(id="footer-container"):
            yield Static(self.render_status(), id="footer-status", classes="footer-section")
            yield Static(self.render_keybindings(), id="footer-keys", classes="footer-section")
    
    def render_status(self) -> str:
        """Render the status section."""
        parts = []
        
        # Loading indicator
        if self.loading:
            parts.append("[blink yellow]●[/blink yellow] Loading...")
        
        # Error message
        if self.error_message:
            error_text = self.error_message[:50] + "..." if len(self.error_message) > 50 else self.error_message
            parts.append(f"[red]✗[/red] {error_text}")
        
        # PR count statistics
        if self.pr_count > 0:
            if self.filtered_count != self.pr_count:
                count_text = f"{self.filtered_count}/{self.pr_count} PRs"
            else:
                count_text = f"{self.pr_count} PRs"
            parts.append(f"[cyan]{count_text}[/cyan]")
        
        # Auto-refresh indicator
        if self.auto_refresh:
            parts.append("[green]◐[/green] Auto")
        
        # Current mode indicator
        mode_display = {
            "browse": "Browse",
            "filter": "Filter",
            "help": "Help",
            "config": "Config"
        }.get(self.current_mode, self.current_mode.title())
        
        parts.append(f"[bold]{mode_display}[/bold]")
        
        return " │ ".join(parts) if parts else "[dim]Ready[/dim]"
    
    def render_keybindings(self) -> str:
        """Render keybindings for current mode."""
        bindings = self.get_mode_bindings()
        
        # Format bindings as "key: action"
        binding_parts = []
        for key, action in bindings.items():
            binding_parts.append(f"[bold]{key}[/bold]: {action}")
        
        return " │ ".join(binding_parts)
    
    def get_mode_bindings(self) -> Dict[str, str]:
        """Get keybindings for the current mode."""
        base_bindings = {
            "q": "quit",
            "r": "refresh", 
            "?": "help"
        }
        
        mode_bindings = {
            "browse": {
                **base_bindings,
                "f": "filter",
                "d": "drafts",
                "a": "auto",
                "↑↓": "navigate",
                "⏎": "open"
            },
            "filter": {
                **base_bindings,
                "⎋": "clear",
                "⏎": "apply"
            },
            "help": {
                "⎋": "close",
                "q": "quit"
            },
            "config": {
                **base_bindings,
                "⎋": "close",
                "⏎": "save"
            }
        }
        
        return mode_bindings.get(self.current_mode, base_bindings)
    
    def set_loading(self, loading: bool) -> None:
        """Set loading state."""
        self.loading = loading
        self.refresh_status()
    
    def set_error(self, error: Optional[str]) -> None:
        """Set error message."""
        self.error_message = error or ""
        self.refresh_status()
    
    def clear_error(self) -> None:
        """Clear error message."""
        self.error_message = ""
        self.refresh_status()
    
    def set_mode(self, mode: str) -> None:
        """Set current mode."""
        self.current_mode = mode
        self.refresh_both()
    
    def update_pr_counts(self, total: int, filtered: int) -> None:
        """Update PR count statistics."""
        self.pr_count = total
        self.filtered_count = filtered
        self.refresh_status()
    
    def set_auto_refresh(self, enabled: bool) -> None:
        """Set auto-refresh state."""
        self.auto_refresh = enabled
        self.refresh_status()
    
    def refresh_status(self) -> None:
        """Refresh the status section."""
        try:
            status_widget = self.query_one("#footer-status", Static)
            status_widget.update(self.render_status())
        except Exception:
            # Widget might not be mounted yet
            pass
    
    def refresh_keybindings(self) -> None:
        """Refresh the keybindings section."""
        try:
            keys_widget = self.query_one("#footer-keys", Static)
            keys_widget.update(self.render_keybindings())
        except Exception:
            # Widget might not be mounted yet
            pass
    
    def refresh_both(self) -> None:
        """Refresh both status and keybindings."""
        self.refresh_status()
        self.refresh_keybindings()
    
    # Watchers for reactive attributes
    def watch_loading(self, new_value: bool) -> None:
        """React to loading state changes."""
        self.refresh_status()
    
    def watch_error_message(self, new_value: str) -> None:
        """React to error message changes."""
        self.refresh_status()
    
    def watch_current_mode(self, new_value: str) -> None:
        """React to mode changes."""
        self.refresh_both()
    
    def watch_pr_count(self, new_value: int) -> None:
        """React to PR count changes."""
        self.refresh_status()
    
    def watch_filtered_count(self, new_value: int) -> None:
        """React to filtered count changes."""
        self.refresh_status()
    
    def watch_auto_refresh(self, new_value: bool) -> None:
        """React to auto-refresh changes."""
        self.refresh_status()


class CompactFooterWidget(FooterWidget):
    """
    Compact version of the footer for smaller terminals.
    """
    
    def render_status(self) -> str:
        """Render compact status."""
        if self.loading:
            return "[yellow]●[/yellow]"
        
        if self.error_message:
            return "[red]✗[/red]"
        
        if self.pr_count > 0:
            if self.filtered_count != self.pr_count:
                return f"[cyan]{self.filtered_count}/{self.pr_count}[/cyan]"
            else:
                return f"[cyan]{self.pr_count}[/cyan]"
        
        return "[green]●[/green]"
    
    def render_keybindings(self) -> str:
        """Render compact keybindings."""
        essential_bindings = {
            "browse": "q r f d",
            "filter": "⎋ ⏎", 
            "help": "⎋ q",
            "config": "⎋ ⏎"
        }
        
        keys = essential_bindings.get(self.current_mode, "q ? r")
        return f"[dim]{keys}[/dim]"


class StatusBarWidget(Static):
    """
    Simple status bar for current application state.
    
    This is a lighter alternative to the full footer widget.
    """
    
    status_text = reactive("Ready")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def render(self) -> str:
        """Render the status bar."""
        return self.status_text
    
    def set_status(self, text: str) -> None:
        """Set status text."""
        self.status_text = text
    
    def set_loading(self, operation: str = "Loading") -> None:
        """Set loading status."""
        self.status_text = f"[yellow]{operation}...[/yellow]"
    
    def set_error(self, error: str) -> None:
        """Set error status."""
        self.status_text = f"[red]Error: {error}[/red]"
    
    def set_success(self, message: str) -> None:
        """Set success status."""
        self.status_text = f"[green]{message}[/green]"
    
    def clear(self) -> None:
        """Clear status back to ready."""
        self.status_text = "Ready"