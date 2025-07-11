"""
Header widget for the PRS TUI application.

Displays repository information, current user, and global shortcuts.
"""

from typing import Optional
from datetime import datetime

from textual.widgets import Static, Label
from textual.containers import Horizontal
from textual.reactive import reactive

from prs.config import get


class HeaderWidget(Static):
    """
    Header widget displaying repository info and shortcuts.
    
    Shows:
    - Repository name and owner
    - Current user
    - Connection status
    - Last refresh time
    - Key shortcuts
    """
    
    # Reactive attributes
    repo_name = reactive("")
    owner = reactive("")
    username = reactive("")
    last_refresh = reactive(None)
    connection_status = reactive("unknown")  # "connected", "error", "unknown"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.load_repo_info()
    
    def compose(self):
        """Compose the header layout."""
        with Horizontal(id="header-container"):
            yield Static(self.render_repo_info(), id="repo-info", classes="header-section")
            yield Static(self.render_status(), id="status-info", classes="header-section")
            yield Static(self.render_shortcuts(), id="shortcuts", classes="header-section")
    
    def load_repo_info(self) -> None:
        """Load repository information from config."""
        try:
            self.repo_name = get("git", "repo_name", fallback="Unknown")
            self.username = get("git", "username", fallback="Unknown") 
            
            # Try to determine owner from config
            org_name = get("git-org", "org_name", fallback="")
            upstream = get("git", "upstream", fallback="")
            
            if org_name:
                self.owner = org_name
            elif upstream and upstream != "username":
                self.owner = upstream
            else:
                self.owner = self.username
                
        except Exception:
            self.repo_name = "Configuration Error"
            self.owner = ""
            self.username = ""
    
    def render_repo_info(self) -> str:
        """Render repository information section."""
        if not self.repo_name or self.repo_name == "Unknown":
            return "[red]⚠ Repository not configured[/red]"
        
        repo_display = f"[cyan]{self.owner}[/cyan]/[bold cyan]{self.repo_name}[/bold cyan]"
        user_display = f"[dim]@{self.username}[/dim]" if self.username else ""
        
        return f"📁 {repo_display} {user_display}"
    
    def render_status(self) -> str:
        """Render connection and refresh status."""
        # Connection status indicator
        status_icon = {
            "connected": "[green]●[/green]",
            "error": "[red]●[/red]", 
            "unknown": "[yellow]●[/yellow]"
        }.get(self.connection_status, "[dim]●[/dim]")
        
        # Last refresh time
        if self.last_refresh:
            if isinstance(self.last_refresh, datetime):
                time_str = self.last_refresh.strftime("%H:%M:%S")
            else:
                time_str = str(self.last_refresh)
            refresh_display = f"[dim]Last: {time_str}[/dim]"
        else:
            refresh_display = "[dim]Never refreshed[/dim]"
        
        return f"{status_icon} {refresh_display}"
    
    def render_shortcuts(self) -> str:
        """Render key shortcuts."""
        shortcuts = [
            "[bold]r[/bold]efresh",
            "[bold]f[/bold]ilter", 
            "[bold]d[/bold]rafts",
            "[bold]q[/bold]uit"
        ]
        return " │ ".join(shortcuts)
    
    def update_refresh_time(self, refresh_time: Optional[datetime] = None) -> None:
        """Update the last refresh time."""
        self.last_refresh = refresh_time or datetime.now()
        self.refresh_status_display()
    
    def update_connection_status(self, status: str) -> None:
        """Update the connection status."""
        if status in ("connected", "error", "unknown"):
            self.connection_status = status
            self.refresh_status_display()
    
    def refresh_status_display(self) -> None:
        """Refresh the status section display."""
        try:
            status_widget = self.query_one("#status-info", Static)
            status_widget.update(self.render_status())
        except Exception:
            # Widget not yet mounted, ignore
            pass
    
    def watch_repo_name(self, new_value: str) -> None:
        """React to repo name changes."""
        self.refresh_repo_display()
    
    def watch_owner(self, new_value: str) -> None:
        """React to owner changes."""
        self.refresh_repo_display()
    
    def watch_username(self, new_value: str) -> None:
        """React to username changes."""
        self.refresh_repo_display()
    
    def refresh_repo_display(self) -> None:
        """Refresh the repository info display."""
        try:
            repo_widget = self.query_one("#repo-info", Static)
            repo_widget.update(self.render_repo_info())
        except Exception:
            # Widget might not be mounted yet
            pass
    
    def watch_last_refresh(self, new_value) -> None:
        """React to last refresh time changes."""
        self.refresh_status_display()
    
    def watch_connection_status(self, new_value: str) -> None:
        """React to connection status changes."""
        self.refresh_status_display()


class CompactHeaderWidget(HeaderWidget):
    """
    Compact version of the header for smaller terminals.
    """
    
    def render_repo_info(self) -> str:
        """Render compact repository information."""
        if not self.repo_name or self.repo_name == "Unknown":
            return "[red]⚠[/red]"
        
        return f"[cyan]{self.repo_name}[/cyan]"
    
    def render_shortcuts(self) -> str:
        """Render compact shortcuts."""
        return "[bold]r[/bold] [bold]f[/bold] [bold]d[/bold] [bold]q[/bold]"