"""
Settings screen for configuring PRS TUI application.

Provides interface for modifying configuration options, preferences,
and application behavior.
"""

from typing import Dict, Any
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, Input, Switch, Select, Button, Tabs, TabbedContent, TabPane
from textual.reactive import reactive
from textual.binding import Binding

from ..widgets.header import HeaderWidget
from ..widgets.footer import FooterWidget
from ...config import get, all_config


class SettingsScreen(Screen):
    """
    Settings configuration screen.
    
    Layout:
    ┌─────────────────────────────────────────────────┐
    │ Header (Settings title)                         │
    ├─────────────────────────────────────────────────┤
    │ [General] [Display] [Filters] [Advanced]       │
    ├─────────────────────────────────────────────────┤
    │                                                 │
    │              Settings Content                   │
    │                                                 │
    │                                                 │
    │         [Save] [Cancel] [Reset]                 │
    ├─────────────────────────────────────────────────┤
    │ Footer (navigation)                             │
    └─────────────────────────────────────────────────┘
    """
    
    CSS = """
    SettingsScreen {
        layout: grid;
        grid-size: 1 4;
        grid-rows: auto auto 1fr auto;
    }
    
    #header {
        height: 3;
    }
    
    #settings-content {
        border: solid $primary;
        padding: 1;
    }
    
    #footer {
        height: 2;
    }
    
    .setting-group {
        margin: 1;
        padding: 1;
        border: solid $secondary;
    }
    
    .setting-row {
        layout: horizontal;
        height: 3;
        margin: 1;
    }
    
    .setting-label {
        width: 30%;
        content-align: middle left;
        padding-right: 2;
    }
    
    .setting-input {
        width: 70%;
    }
    
    .button-row {
        layout: horizontal;
        align: center middle;
        height: 4;
        margin: 1;
    }
    
    .button-row Button {
        margin: 0 1;
    }
    """
    
    BINDINGS = [
        Binding("escape,q", "cancel", "Cancel", show=True),
        Binding("ctrl+s", "save", "Save", show=True),
        Binding("ctrl+r", "reset", "Reset", show=True),
    ]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config_data: Dict[str, Any] = {}
        self.modified = False
    
    def compose(self):
        """Compose the settings screen layout."""
        yield HeaderWidget(id="header")
        
        with TabbedContent(id="settings-content"):
            with TabPane("General", id="general"):
                yield self.create_general_settings()
            
            with TabPane("Display", id="display"):
                yield self.create_display_settings()
            
            with TabPane("Filters", id="filters"):
                yield self.create_filter_settings()
            
            with TabPane("Advanced", id="advanced"):
                yield self.create_advanced_settings()
        
        yield FooterWidget(id="footer")
    
    def on_mount(self) -> None:
        """Initialize settings screen."""
        # Update header
        header = self.query_one("#header", HeaderWidget)
        header.repo_name = "Settings"
        header.owner = "Configuration"
        
        # Load current configuration
        self.load_config()
    
    def load_config(self) -> None:
        """Load current configuration values."""
        try:
            self.config_data = all_config()
        except Exception:
            self.config_data = {}
    
    def create_general_settings(self) -> Container:
        """Create general settings tab."""
        container = Container()
        
        with container:
            with Container(classes="setting-group"):
                yield Static("[bold]Repository Settings[/bold]")
                
                with Container(classes="setting-row"):
                    yield Static("Repository Name:", classes="setting-label")
                    yield Input(
                        value=get("git", "repo_name", fallback=""),
                        placeholder="repository-name",
                        id="repo-name",
                        classes="setting-input"
                    )
                
                with Container(classes="setting-row"):
                    yield Static("Username:", classes="setting-label")
                    yield Input(
                        value=get("git", "username", fallback=""),
                        placeholder="github-username",
                        id="username",
                        classes="setting-input"
                    )
                
                with Container(classes="setting-row"):
                    yield Static("Organization:", classes="setting-label")
                    yield Input(
                        value=get("git-org", "org_name", fallback=""),
                        placeholder="organization-name",
                        id="org-name",
                        classes="setting-input"
                    )
            
            with Container(classes="setting-group"):
                yield Static("[bold]Refresh Settings[/bold]")
                
                with Container(classes="setting-row"):
                    yield Static("Auto-refresh:", classes="setting-label")
                    yield Switch(
                        value=True,  # Default enabled
                        id="auto-refresh",
                        classes="setting-input"
                    )
                
                with Container(classes="setting-row"):
                    yield Static("Refresh Interval (seconds):", classes="setting-label")
                    yield Input(
                        value="30",
                        placeholder="30",
                        id="refresh-interval",
                        classes="setting-input"
                    )
        
        return container
    
    def create_display_settings(self) -> Container:
        """Create display settings tab."""
        container = Container()
        
        with container:
            with Container(classes="setting-group"):
                yield Static("[bold]Layout Settings[/bold]")
                
                with Container(classes="setting-row"):
                    yield Static("Show Detail Panel:", classes="setting-label")
                    yield Switch(
                        value=True,
                        id="show-detail-panel",
                        classes="setting-input"
                    )
                
                with Container(classes="setting-row"):
                    yield Static("Compact Mode:", classes="setting-label")
                    yield Switch(
                        value=False,
                        id="compact-mode",
                        classes="setting-input"
                    )
            
            with Container(classes="setting-group"):
                yield Static("[bold]Information Display[/bold]")
                
                with Container(classes="setting-row"):
                    yield Static("Author Mode:", classes="setting-label")
                    yield Select(
                        options=[
                            ("none", "None"),
                            ("short", "Short"),
                            ("normal", "Normal"),
                            ("long", "Long")
                        ],
                        value="short",
                        id="author-mode",
                        classes="setting-input"
                    )
                
                with Container(classes="setting-row"):
                    yield Static("Checks Mode:", classes="setting-label")
                    yield Select(
                        options=[
                            ("none", "None"),
                            ("short", "Short"),
                            ("normal", "Normal"),
                            ("long", "Long")
                        ],
                        value="short",
                        id="checks-mode",
                        classes="setting-input"
                    )
                
                with Container(classes="setting-row"):
                    yield Static("Reviews Mode:", classes="setting-label")
                    yield Select(
                        options=[
                            ("none", "None"),
                            ("short", "Short"),
                            ("normal", "Normal"),
                            ("long", "Long")
                        ],
                        value="short",
                        id="reviews-mode",
                        classes="setting-input"
                    )
                
                with Container(classes="setting-row"):
                    yield Static("Labels Mode:", classes="setting-label")
                    yield Select(
                        options=[
                            ("none", "None"),
                            ("short", "Short"),
                            ("normal", "Normal"),
                            ("long", "Long")
                        ],
                        value="short",
                        id="labels-mode",
                        classes="setting-input"
                    )
        
        return container
    
    def create_filter_settings(self) -> Container:
        """Create filter settings tab."""
        container = Container()
        
        with container:
            with Container(classes="setting-group"):
                yield Static("[bold]Default Filters[/bold]")
                
                with Container(classes="setting-row"):
                    yield Static("Include Drafts:", classes="setting-label")
                    yield Switch(
                        value=False,
                        id="include-drafts",
                        classes="setting-input"
                    )
                
                with Container(classes="setting-row"):
                    yield Static("Include Merged:", classes="setting-label")
                    yield Switch(
                        value=False,
                        id="include-merged",
                        classes="setting-input"
                    )
                
                with Container(classes="setting-row"):
                    yield Static("Default Author Filter:", classes="setting-label")
                    yield Input(
                        placeholder="Leave empty for all authors",
                        id="default-author",
                        classes="setting-input"
                    )
            
            with Container(classes="setting-group"):
                yield Static("[bold]Quick Filters[/bold]")
                
                with Container(classes="setting-row"):
                    yield Static("Show Quick Filters:", classes="setting-label")
                    yield Switch(
                        value=True,
                        id="show-quick-filters",
                        classes="setting-input"
                    )
        
        return container
    
    def create_advanced_settings(self) -> Container:
        """Create advanced settings tab."""
        container = Container()
        
        with container:
            with Container(classes="setting-group"):
                yield Static("[bold]Cache Settings[/bold]")
                
                with Container(classes="setting-row"):
                    yield Static("Enable Cache:", classes="setting-label")
                    yield Switch(
                        value=True,
                        id="enable-cache",
                        classes="setting-input"
                    )
                
                with Container(classes="setting-row"):
                    yield Static("Cache TTL (minutes):", classes="setting-label")
                    yield Input(
                        value="5",
                        placeholder="5",
                        id="cache-ttl",
                        classes="setting-input"
                    )
            
            with Container(classes="setting-group"):
                yield Static("[bold]Performance[/bold]")
                
                with Container(classes="setting-row"):
                    yield Static("Max PRs to Load:", classes="setting-label")
                    yield Input(
                        value="100",
                        placeholder="100",
                        id="max-prs",
                        classes="setting-input"
                    )
                
                with Container(classes="setting-row"):
                    yield Static("Render Throttle (ms):", classes="setting-label")
                    yield Input(
                        value="100",
                        placeholder="100",
                        id="render-throttle",
                        classes="setting-input"
                    )
            
            # Action buttons
            with Container(classes="button-row"):
                yield Button("Save", variant="success", id="save-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")
                yield Button("Reset to Defaults", variant="error", id="reset-btn")
        
        return container
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-btn":
            self.action_save()
        elif event.button.id == "cancel-btn":
            self.action_cancel()
        elif event.button.id == "reset-btn":
            self.action_reset()
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        self.modified = True
    
    def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handle switch changes."""
        self.modified = True
    
    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select changes."""
        self.modified = True
    
    def collect_settings(self) -> Dict[str, Any]:
        """Collect all settings from the form."""
        settings = {}
        
        try:
            # General settings
            settings["git"] = {
                "repo_name": self.query_one("#repo-name", Input).value,
                "username": self.query_one("#username", Input).value,
            }
            settings["git-org"] = {
                "org_name": self.query_one("#org-name", Input).value,
            }
            
            # Display settings
            settings["tui"] = {
                "auto_refresh": self.query_one("#auto-refresh", Switch).value,
                "refresh_interval": int(self.query_one("#refresh-interval", Input).value or "30"),
                "show_detail_panel": self.query_one("#show-detail-panel", Switch).value,
                "compact_mode": self.query_one("#compact-mode", Switch).value,
            }
            
            # Information display settings
            settings["pr-info"] = {
                "author": self.query_one("#author-mode", Select).value,
                "checks": self.query_one("#checks-mode", Select).value,
                "reviews": self.query_one("#reviews-mode", Select).value,
                "labels": self.query_one("#labels-mode", Select).value,
                "include_drafts": str(self.query_one("#include-drafts", Switch).value).lower(),
                "include_merged": str(self.query_one("#include-merged", Switch).value).lower(),
            }
            
            # Advanced settings
            settings["advanced"] = {
                "enable_cache": self.query_one("#enable-cache", Switch).value,
                "cache_ttl": int(self.query_one("#cache-ttl", Input).value or "5"),
                "max_prs": int(self.query_one("#max-prs", Input).value or "100"),
                "render_throttle": int(self.query_one("#render-throttle", Input).value or "100"),
            }
            
        except Exception:
            pass  # Handle validation errors
        
        return settings
    
    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """Save settings to configuration file."""
        try:
            # TODO: Implement actual config file writing
            # For now, just return success
            return True
        except Exception:
            return False
    
    # Action handlers
    def action_save(self) -> None:
        """Save settings and close."""
        settings = self.collect_settings()
        if self.save_settings(settings):
            self.app.pop_screen()
        else:
            # TODO: Show error message
            pass
    
    def action_cancel(self) -> None:
        """Cancel settings changes."""
        self.app.pop_screen()
    
    def action_reset(self) -> None:
        """Reset all settings to defaults."""
        # TODO: Implement reset to defaults
        self.modified = True