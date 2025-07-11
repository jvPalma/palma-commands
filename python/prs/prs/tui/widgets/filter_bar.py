"""
Filter bar widget for the PRS TUI application.

Provides text-based filtering and quick filter options for pull requests.
"""

from typing import Callable, Optional
from textual.widgets import Input, Static, Button
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.message import Message


class FilterBarWidget(Static):
    """
    Filter bar widget for filtering pull requests.
    
    Features:
    - Text-based filtering by title, author, labels
    - Quick filter buttons for common filters
    - Real-time filtering as user types
    - Clear filter functionality
    """
    
    # Reactive attributes
    filter_text = reactive("")
    is_focused = reactive(False)
    show_quick_filters = reactive(True)
    
    class FilterChanged(Message):
        """Message sent when filter text changes."""
        
        def __init__(self, filter_text: str) -> None:
            self.filter_text = filter_text
            super().__init__()
    
    class QuickFilterSelected(Message):
        """Message sent when a quick filter is selected."""
        
        def __init__(self, filter_type: str, value: str) -> None:
            self.filter_type = filter_type
            self.value = value
            super().__init__()
    
    def __init__(self, placeholder: str = "Filter PRs (title, author, labels, #id)...", **kwargs):
        super().__init__(**kwargs)
        self.placeholder = placeholder
        self.filter_input: Optional[Input] = None
        
    def compose(self):
        """Compose the filter bar layout."""
        with Horizontal(id="filter-container"):
            # Main filter input
            self.filter_input = Input(
                placeholder=self.placeholder,
                id="filter-input",
                classes="filter-input"
            )
            yield self.filter_input
            
            # Clear button
            yield Button("×", id="clear-filter", classes="clear-button")
            
            # Quick filters (if enabled)
            if self.show_quick_filters:
                yield Static("│", classes="separator")
                yield Button("My PRs", id="filter-mine", classes="quick-filter")
                yield Button("Needs Review", id="filter-review", classes="quick-filter")
                yield Button("Failed CI", id="filter-failed", classes="quick-filter")
                yield Button("Approved", id="filter-approved", classes="quick-filter")
    
    def on_mount(self) -> None:
        """Set up event handlers when mounted."""
        if self.filter_input:
            self.filter_input.focus()
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle filter input changes."""
        if event.input.id == "filter-input":
            self.filter_text = event.value
            self.post_message(self.FilterChanged(event.value))
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "clear-filter":
            self.clear_filter()
        elif event.button.id == "filter-mine":
            self.apply_quick_filter("author", "me")
        elif event.button.id == "filter-review":
            self.apply_quick_filter("status", "needs_review")
        elif event.button.id == "filter-failed":
            self.apply_quick_filter("ci", "failed")
        elif event.button.id == "filter-approved":
            self.apply_quick_filter("review", "approved")
    
    def clear_filter(self) -> None:
        """Clear the current filter."""
        if self.filter_input:
            self.filter_input.value = ""
        self.filter_text = ""
        self.post_message(self.FilterChanged(""))
    
    def apply_quick_filter(self, filter_type: str, value: str) -> None:
        """Apply a quick filter."""
        self.post_message(self.QuickFilterSelected(filter_type, value))
        
        # Also update the text input to show what filter is applied
        filter_text_map = {
            ("author", "me"): "author:me",
            ("status", "needs_review"): "status:needs_review", 
            ("ci", "failed"): "ci:failed",
            ("review", "approved"): "review:approved"
        }
        
        filter_text = filter_text_map.get((filter_type, value), f"{filter_type}:{value}")
        if self.filter_input:
            self.filter_input.value = filter_text
        self.filter_text = filter_text
    
    def set_filter_text(self, text: str) -> None:
        """Programmatically set the filter text."""
        if self.filter_input:
            self.filter_input.value = text
        self.filter_text = text
    
    def focus_filter(self) -> None:
        """Focus the filter input."""
        if self.filter_input:
            self.filter_input.focus()
            self.is_focused = True
    
    def watch_filter_text(self, new_value: str) -> None:
        """React to filter text changes."""
        # Update visual state if needed
        pass
    
    def watch_is_focused(self, new_value: bool) -> None:
        """React to focus changes."""
        # Could add visual focus indicators
        pass


class CompactFilterBarWidget(FilterBarWidget):
    """
    Compact version of the filter bar for smaller terminals.
    """
    
    def __init__(self, **kwargs):
        kwargs.setdefault("placeholder", "Filter...")
        super().__init__(**kwargs)
        self.show_quick_filters = False
    
    def compose(self):
        """Compose compact filter bar layout."""
        with Horizontal(id="filter-container"):
            self.filter_input = Input(
                placeholder=self.placeholder,
                id="filter-input", 
                classes="filter-input compact"
            )
            yield self.filter_input
            yield Button("×", id="clear-filter", classes="clear-button compact")


class AdvancedFilterBarWidget(FilterBarWidget):
    """
    Advanced filter bar with additional filtering options.
    """
    
    def compose(self):
        """Compose advanced filter bar layout."""
        with Horizontal(id="filter-container"):
            # Main filter input
            self.filter_input = Input(
                placeholder="Advanced filter (author:user, label:bug, ci:failed, review:approved)...",
                id="filter-input",
                classes="filter-input advanced"
            )
            yield self.filter_input
            
            # Clear button
            yield Button("×", id="clear-filter", classes="clear-button")
            
            # More filter options
            yield Static("│", classes="separator")
            yield Button("Draft", id="filter-draft", classes="quick-filter")
            yield Button("Mergeable", id="filter-mergeable", classes="quick-filter")
            yield Button("Stale", id="filter-stale", classes="quick-filter")
            yield Button("Recent", id="filter-recent", classes="quick-filter")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle advanced filter button presses."""
        # Call parent handler first
        super().on_button_pressed(event)
        
        # Handle additional buttons
        if event.button.id == "filter-draft":
            self.apply_quick_filter("draft", "true")
        elif event.button.id == "filter-mergeable":
            self.apply_quick_filter("mergeable", "true")
        elif event.button.id == "filter-stale":
            self.apply_quick_filter("updated", "week_ago")
        elif event.button.id == "filter-recent":
            self.apply_quick_filter("updated", "today")