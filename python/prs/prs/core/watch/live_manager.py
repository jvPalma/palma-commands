"""
Live Display Manager

Manages Rich.Live integration for smooth, flicker-free updates.
"""

from typing import List, Dict, Set, Optional
from rich.live import Live
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from datetime import datetime
import logging

from .watch_types import ChangeSet, WatchState, WatchConfig
from .spinner_manager import SpinnerManager
from .runtime_modes import RuntimeModeManager
# Import will be done dynamically to avoid circular imports


class LiveDisplayManager:
    """
    Manages Rich.Live display for smooth PR updates.
    
    Integrates with existing panel rendering system while providing
    real-time updates without terminal flickering. Enhanced with
    spinner countdown timer and keyboard shortcuts display.
    """
    
    def __init__(self, console: Console, config: WatchConfig, 
                 spinner_manager: Optional[SpinnerManager] = None,
                 runtime_modes: Optional[RuntimeModeManager] = None):
        self.console = console
        self.config = config
        self.live: Optional[Live] = None
        self.watch_state = WatchState()
        self.logger = logging.getLogger(__name__)
        self.changed_prs: Set[str] = set()
        self.spinner_manager = spinner_manager
        self.runtime_modes = runtime_modes
        self._current_modes: Dict[str, str] = {}
    
    def start_live_display(self) -> None:
        """Initialize and start the Rich.Live display."""
        if self.live is not None:
            self.logger.warning("Live display already started")
            return
        
        initial_content = self._create_loading_display()
        
        try:
            self.live = Live(
                initial_content,
                console=self.console,
                refresh_per_second=2,  # Reduced to minimize flickering
                screen=False,  # Don't take over entire screen
                auto_refresh=True,
                transient=False
            )
            self.live.start()
            self.watch_state.is_running = True
            self.logger.debug("Live display started")
        except Exception as e:
            self.logger.error(f"Failed to start live display: {e}")
            raise
    
    def stop_live_display(self) -> None:
        """Stop the Rich.Live display."""
        if self.live is not None:
            try:
                self.live.stop()
                self.live = None
                self.watch_state.is_running = False
                self.logger.debug("Live display stopped")
            except Exception as e:
                self.logger.error(f"Error stopping live display: {e}")
    
    def update_display(self, prs: List, modes: Dict, changeset: Optional[ChangeSet] = None, 
                      remaining_seconds: Optional[int] = None) -> None:
        """
        Update the live display with new PR data.
        
        Args:
            prs: List of PullRequest objects
            modes: Display mode configuration
            changeset: Optional changeset for highlighting changes
            remaining_seconds: Optional countdown seconds for enhanced display
        """
        if not self.live:
            self.logger.error("Live display not started")
            return
        
        try:
            # Update current modes tracking
            self._current_modes = modes.copy()
            
            # Update changed PR tracking
            if changeset:
                self.changed_prs = changeset.get_changed_pr_ids()
            
            # Create display content with countdown
            display_content = self._create_display_content(prs, modes, changeset, remaining_seconds)
            
            # Update the live display
            self.live.update(display_content)
            
            # Update watch state
            # Only increment update count on actual PR data updates, not visual refreshes
            if changeset is not None:
                self.watch_state.update_count += 1
            self.watch_state.last_update = datetime.now().strftime("%H:%M:%S")
            self.watch_state.connection_status = "connected"
            
        except Exception as e:
            self.logger.error(f"Error updating display: {e}")
            self.watch_state.last_error = str(e)
            self.watch_state.connection_status = "error"
    
    def update_display_modes(self, new_modes: Dict[str, str]) -> None:
        """
        Update display modes (internal state only, no immediate display update).
        
        Args:
            new_modes: New display mode configuration
        """
        self._current_modes = new_modes.copy()
        # Note: Display update is handled centrally by the controller to prevent race conditions
    
    
    def update_status(self, status: str, error: Optional[str] = None) -> None:
        """Update connection status and error information (internal state only)."""
        self.watch_state.connection_status = status
        if error:
            self.watch_state.last_error = error
        
        # Note: Display updates are handled centrally by the controller to prevent
        # concurrent Rich.Live updates that cause duplicate panels
    
    def _create_display_content(self, prs: List, modes: Dict, changeset: Optional[ChangeSet] = None,
                               remaining_seconds: Optional[int] = None):
        """Create the complete display content including header and PR panels."""
        content_parts = []
        
        # Add PR panels first
        for pr in prs:
            # Check if this PR has changes for highlighting
            highlight_changes = pr.id in self.changed_prs if hasattr(pr, 'id') else False
            
            try:
                # Use existing panel rendering system
                panel = self._create_pr_panel_for_watch(pr, modes, highlight_changes)
                if panel:
                    content_parts.append(panel)
            except Exception as e:
                self.logger.error(f"Error creating panel for PR {getattr(pr, 'id', 'unknown')}: {e}")
                # Add fallback panel
                fallback_panel = self._create_basic_panel(pr, highlight_changes)
                content_parts.append(fallback_panel)
                continue
        
        # Add enhanced header panel at the bottom with top margin
        if content_parts:  # Only add spacing if there are PRs
            from rich.padding import Padding
            header_panel = self._create_enhanced_header_panel(changeset, remaining_seconds)
            content_parts.append(Padding(header_panel, (1, 0, 0, 0)))  # 1 line top padding
        else:
            # No PRs, just add the header
            header_panel = self._create_enhanced_header_panel(changeset, remaining_seconds)
            content_parts.append(header_panel)
        
        # Store for status updates
        self._last_prs = prs
        self._last_modes = modes
        
        return Group(*content_parts)
    
    def _create_enhanced_header_panel(self, changeset: Optional[ChangeSet] = None, 
                                     remaining_seconds: Optional[int] = None) -> Panel:
        """Create enhanced header panel with keyboard shortcuts, modes, and countdown."""
        content_parts = []
        
        # First line: Keyboard shortcuts and current modes
        first_line = Text()
        
        # Add keyboard shortcuts if spinner manager is available
        if self.spinner_manager and self.runtime_modes:
            current_modes = self.runtime_modes.get_current_modes()
            enhanced_display = self.spinner_manager.get_enhanced_countdown_display(
                remaining_seconds or 0, current_modes, show_shortcuts=True
            )
            first_line = enhanced_display
        else:
            # Fallback display without enhanced features
            first_line.append("🔧 PRS Watch Mode", style="bold blue")
            if self._current_modes:
                first_line.append(" | ", style="dim")
                mode_parts = []
                for feature in ["checks", "reviews", "labels"]:
                    if feature in self._current_modes:
                        mode_parts.append(f"{feature.capitalize()}: {self._current_modes[feature]}")
                if mode_parts:
                    first_line.append(" | ".join(mode_parts), style="white")
        
        content_parts.append(first_line)
        
        # Second line: Status information
        status_line = Text()
        
        # Update count and time
        status_line.append(f"Updates: {self.watch_state.update_count}", style="dim")
        if self.watch_state.last_update:
            status_line.append(f" | Last: {self.watch_state.last_update}", style="dim")
        
        # Connection status
        status_styles = {
            "connected": "green",
            "connecting": "yellow", 
            "disconnected": "red",
            "error": "red"
        }
        status_style = status_styles.get(self.watch_state.connection_status, "dim")
        status_line.append(f" | Status: {self.watch_state.connection_status}", style=status_style)
        
        # Change summary if available
        if changeset and changeset.has_changes():
            if changeset.new_prs:
                status_line.append(f" | New: {len(changeset.new_prs)}", style="green")
            if changeset.changes:
                status_line.append(f" | Changed: {len(changeset.changes)}", style="yellow")
        
        # Controls
        status_line.append(" | Press Ctrl+C to stop", style="dim")
        
        content_parts.append(status_line)
        
        # Error information if present
        if self.watch_state.last_error:
            error_line = Text(f"⚠ Last error: {self.watch_state.last_error}", style="red")
            content_parts.append(error_line)
        
        return Panel(
            Group(*content_parts),
            border_style="blue",
            padding=(0, 1)
        )
    
    def _create_header_panel(self, changeset: Optional[ChangeSet] = None) -> Panel:
        """Create basic header panel with watch status information (fallback)."""
        return self._create_enhanced_header_panel(changeset, None)
    
    def _create_pr_panel_for_watch(self, pr, modes: Dict, highlight_changes: bool = False):
        """
        Create a PR panel for watch mode using the existing panel rendering system.
        """
        try:
            # Import here to avoid circular imports
            from ..display.panel_renderer import create_panel_title, assemble_panel_content, get_panel_color
            
            # Create panel title
            panel_title = create_panel_title(pr)
            
            # Create panel content
            panel_content = assemble_panel_content(pr, modes, self.console)
            
            # Determine panel color (with change highlighting)
            panel_color = get_panel_color(pr)
            if highlight_changes:
                panel_color = "on red"  # Highlight changed PRs
            
            # Create panel subtitle (URL)
            panel_subtitle = None
            if modes.get("pr_url", "none") != "none":
                panel_subtitle = Text(pr.url, style="cyan")
            
            return Panel(
                panel_content,
                title=panel_title,
                subtitle=panel_subtitle,
                border_style=panel_color,
                title_align="left",
                subtitle_align="left",
                padding=(0, 1),
                expand=True
            )
            
        except Exception as e:
            self.logger.error(f"Error creating panel with existing renderer: {e}")
            # Fallback to basic panel
            return self._create_basic_panel(pr, highlight_changes)
    
    def _create_basic_panel(self, pr, highlight_changes: bool = False):
        """Fallback basic panel creation."""
        title_text = Text()
        title_text.append(f"#{getattr(pr, 'id', 'unknown'):06}", style="green")
        title_text.append(" ")
        title_text.append(getattr(pr, 'title', 'Unknown Title'), style="white")
        
        content_text = Text()
        if highlight_changes:
            content_text.append("● CHANGED ", style="on red")
        
        content_text.append("Status: ", style="dim")
        content_text.append(getattr(pr, 'status', 'unknown'), style="green")
        
        border_style = "on red" if highlight_changes else "green"
        
        return Panel(
            content_text,
            title=title_text,
            title_align="left",
            border_style=border_style,
            padding=(0, 1),
            expand=True
        )
    
    def _create_loading_display(self):
        """Create initial loading display."""
        loading_text = Text("🔄 Starting PRS Watch Mode...", style="yellow")
        return Panel(
            loading_text,
            title="PRS Watch",
            title_align="left",
            border_style="blue",
            padding=(0, 1)
        )
    
    def _create_status_only_display(self):
        """Create status-only display when no PR data is available."""
        header_panel = self._create_header_panel()
        return header_panel
    
    def is_running(self) -> bool:
        """Check if live display is currently running."""
        return self.watch_state.is_running and self.live is not None
    
    def get_watch_state(self) -> WatchState:
        """Get current watch state."""
        return self.watch_state