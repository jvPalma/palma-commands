"""
Main TUI application that demonstrates the integration of all components.

This is an example showing how the PR list, detail panels, CI status widget,
and interactive features work together to create a complete TUI experience.
"""

import asyncio
from typing import Optional
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from .models.tui_models import TUIState, RefreshConfig
from .widgets.pr_list import PRListWidget
from .widgets.pr_detail import PRDetailWidget
from .widgets.ci_status import CIStatusWidget
from .events.events import EventBus, InteractionManager, KeyEvent, EventType
from .data_integration import DataIntegrationManager
from ..vc_tools.github.client import GitHubClient
from ..vc_tools.github.adapter import GitHubAdapter


class MainTUIApplication:
    """Main TUI application coordinating all components."""
    
    def __init__(self, console: Console = None):
        self.console = console or Console()
        
        # Core components
        self.tui_state = TUIState()
        self.event_bus = EventBus()
        
        # GitHub integration (placeholder - would use real client)
        self.github_client = GitHubClient()
        self.github_adapter = GitHubAdapter()
        
        # Data integration
        self.data_manager = DataIntegrationManager(
            self.github_client,
            self.github_adapter,
            self.tui_state,
            self.event_bus,
            RefreshConfig()
        )
        
        # UI Widgets
        self.pr_list_widget = PRListWidget(self.tui_state, self.console)
        self.pr_detail_widget = PRDetailWidget(self.tui_state, self.console)
        self.ci_status_widget = CIStatusWidget(self.tui_state, self.console)
        
        # Interaction management
        self.interaction_manager = InteractionManager(self.event_bus)
        
        # UI state
        self.active_panel = "list"  # "list", "detail", "ci"
        self.layout = self._create_layout()
        self.live_display: Optional[Live] = None
        
        # Setup component callbacks
        self._setup_callbacks()
        
        # Setup action handlers
        self._setup_action_handlers()
    
    def _create_layout(self) -> Layout:
        """Create the main layout for the TUI."""
        layout = Layout()
        
        # Split into main areas
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        # Split main area
        layout["main"].split_row(
            Layout(name="left_panel", ratio=2),
            Layout(name="right_panel", ratio=3)
        )
        
        # Split right panel for detail and CI status
        layout["right_panel"].split_column(
            Layout(name="detail_panel", ratio=2),
            Layout(name="ci_panel", ratio=1)
        )
        
        return layout
    
    def _setup_callbacks(self):
        """Setup callbacks between components."""
        # PR list callbacks
        self.pr_list_widget.on_selection_change = self._on_pr_selection_change
        self.pr_list_widget.on_pr_activate = self._on_pr_activate
        
        # CI status callbacks
        self.ci_status_widget.on_log_request = self._on_log_request
        self.ci_status_widget.on_artifact_request = self._on_artifact_request
        
        # Data binding
        self.data_manager.reactive_binding.add_update_callback(self._on_data_update)
    
    def _setup_action_handlers(self):
        """Setup action handlers for the event system."""
        from .events.events import ActionType
        
        # Register action handlers
        self.event_bus.register_action_handler(
            ActionType.REFRESH_DATA, self._handle_refresh_action
        )
        self.event_bus.register_action_handler(
            ActionType.TOGGLE_DETAIL_PANEL, self._handle_toggle_detail_action
        )
        self.event_bus.register_action_handler(
            ActionType.OPEN_PR, self._handle_open_pr_action
        )
        self.event_bus.register_action_handler(
            ActionType.CHECKOUT_BRANCH, self._handle_checkout_action
        )
        self.event_bus.register_action_handler(
            ActionType.SELECT_ALL, self._handle_select_all_action
        )
        self.event_bus.register_action_handler(
            ActionType.CLEAR_SELECTION, self._handle_clear_selection_action
        )
    
    async def run(self):
        """Run the main TUI application."""
        try:
            # Initialize data
            await self.data_manager.initialize()
            
            # Create live display
            self.live_display = Live(
                self.layout,
                console=self.console,
                refresh_per_second=10,
                screen=True
            )
            
            # Start live display
            with self.live_display:
                # Initial render
                self._update_display()
                
                # Main event loop
                await self._main_loop()
        
        except KeyboardInterrupt:
            pass
        finally:
            # Cleanup
            self.data_manager.shutdown()
    
    async def _main_loop(self):
        """Main event loop for handling user input."""
        import sys
        import termios
        import tty
        
        # Setup terminal for raw input
        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setraw(sys.stdin.fileno())
            
            while True:
                # Read character (non-blocking would be better)
                char = sys.stdin.read(1)
                
                # Handle special keys
                if char == '\x1b':  # Escape sequence
                    char += sys.stdin.read(2)
                    key = self._parse_escape_sequence(char)
                elif char == '\r':
                    key = "enter"
                elif char == ' ':
                    key = "space"
                elif char == '\x7f':  # Backspace
                    key = "backspace"
                elif char == '\t':
                    key = "tab"
                elif char == '\x03':  # Ctrl+C
                    break
                elif ord(char) < 32:  # Other control characters
                    key = f"ctrl+{chr(ord(char) + 64).lower()}"
                else:
                    key = char
                
                # Create key event
                key_event = KeyEvent(key=key, data={"context": self.active_panel})
                
                # Handle key
                handled = await self._handle_key_input(key_event)
                
                if not handled and key in ['q', '\x03']:  # q or Ctrl+C
                    break
                
                # Update display
                self._update_display()
        
        finally:
            # Restore terminal settings
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    
    def _parse_escape_sequence(self, seq: str) -> str:
        """Parse escape sequences into key names."""
        if seq == '\x1b[A':
            return "up"
        elif seq == '\x1b[B':
            return "down"
        elif seq == '\x1b[C':
            return "right"
        elif seq == '\x1b[D':
            return "left"
        elif seq == '\x1b[5~':
            return "page_up"
        elif seq == '\x1b[6~':
            return "page_down"
        elif seq == '\x1b[H':
            return "home"
        elif seq == '\x1b[F':
            return "end"
        else:
            return "escape"
    
    async def _handle_key_input(self, key_event: KeyEvent) -> bool:
        """Handle keyboard input across all components."""
        key = key_event.key
        
        # Global keys first
        if key == "1":
            self.active_panel = "list"
            return True
        elif key == "2":
            self.active_panel = "detail"
            return True
        elif key == "3":
            self.active_panel = "ci"
            return True
        
        # Emit key event to event system
        self.event_bus.emit(key_event)
        
        # Route to active widget
        if self.active_panel == "list":
            return self.pr_list_widget.handle_key(key)
        elif self.active_panel == "detail":
            return self.pr_detail_widget.handle_key(key)
        elif self.active_panel == "ci":
            return self.ci_status_widget.handle_key(key)
        
        return False
    
    def _update_display(self):
        """Update the live display with current widget content."""
        # Header
        header_text = Text()
        header_text.append("PRS TUI ", style="bold blue")
        header_text.append("- Pull Request Manager")
        
        active_indicators = []
        if self.active_panel == "list":
            active_indicators.append("[1] List")
        else:
            active_indicators.append("1: List")
        
        if self.active_panel == "detail":
            active_indicators.append("[2] Detail")
        else:
            active_indicators.append("2: Detail")
        
        if self.active_panel == "ci":
            active_indicators.append("[3] CI/CD")
        else:
            active_indicators.append("3: CI/CD")
        
        header_text.append(f"  |  {' | '.join(active_indicators)}")
        
        self.layout["header"].update(Panel(header_text, style="blue"))
        
        # Main panels
        self.layout["left_panel"].update(self.pr_list_widget.render())
        self.layout["detail_panel"].update(self.pr_detail_widget.render())
        self.layout["ci_panel"].update(self.ci_status_widget.render())
        
        # Footer with help
        footer_text = Text()
        footer_text.append("Keys: ", style="dim")
        footer_text.append("1-3:panels ↑↓:nav enter:select space:multi r:refresh q:quit", style="dim")
        
        # Add context-specific help
        if self.active_panel == "list":
            footer_text.append(" | o:open c:checkout v:multi-select", style="dim")
        elif self.active_panel == "detail":
            footer_text.append(" | tab:switch-tabs", style="dim")
        elif self.active_panel == "ci":
            footer_text.append(" | l:logs a:artifacts", style="dim")
        
        self.layout["footer"].update(Panel(footer_text, style="dim"))
        
        # Refresh live display
        if self.live_display:
            self.live_display.refresh()
    
    # Event handlers
    def _on_pr_selection_change(self, index: Optional[int]):
        """Handle PR selection change."""
        # Update CI widget when selection changes
        self.ci_status_widget.reset_selection()
    
    def _on_pr_activate(self, index: int):
        """Handle PR activation (enter key)."""
        # Switch to detail panel
        self.active_panel = "detail"
    
    def _on_log_request(self, url: str):
        """Handle CI log request."""
        # In a real implementation, this would open the URL in browser
        # or show logs in a popup
        pass
    
    def _on_artifact_request(self, url: str):
        """Handle artifact request."""
        # Similar to log request
        pass
    
    def _on_data_update(self):
        """Handle data updates."""
        # Refresh widgets that need updating
        self.pr_list_widget.refresh()
    
    # Action handlers
    def _handle_refresh_action(self, context: dict = None):
        """Handle refresh action."""
        asyncio.create_task(self.data_manager.manual_refresh())
    
    def _handle_toggle_detail_action(self, context: dict = None):
        """Handle toggle detail panel action."""
        self.tui_state.show_detail_panel = not self.tui_state.show_detail_panel
    
    def _handle_open_pr_action(self, context: dict = None):
        """Handle open PR in browser action."""
        pr = self.tui_state.get_selected_pr()
        if pr:
            # In real implementation, would open browser
            import webbrowser
            webbrowser.open(pr.url)
    
    def _handle_checkout_action(self, context: dict = None):
        """Handle checkout PR branch action."""
        pr = self.tui_state.get_selected_pr()
        if pr:
            # In real implementation, would run git checkout
            pass
    
    def _handle_select_all_action(self, context: dict = None):
        """Handle select all action."""
        filtered_items = self.tui_state.get_filtered_sorted_items()
        self.tui_state.selection.selected_indices = set(range(len(filtered_items)))
    
    def _handle_clear_selection_action(self, context: dict = None):
        """Handle clear selection action."""
        self.tui_state.selection.clear_selection()


# Example usage
async def main():
    """Example main function showing how to run the TUI."""
    console = Console()
    app = MainTUIApplication(console)
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())