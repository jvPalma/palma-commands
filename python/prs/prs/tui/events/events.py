"""
Event system for TUI application.

Provides event handling, context menus, action shortcuts, and interactive features
for the PR management TUI.
"""

from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass
from enum import Enum


class EventType(Enum):
    """Types of events in the TUI."""
    KEY_PRESS = "key_press"
    MOUSE_CLICK = "mouse_click"
    SELECTION_CHANGE = "selection_change"
    PR_ACTIVATE = "pr_activate"
    CONTEXT_MENU = "context_menu"
    ACTION_TRIGGERED = "action_triggered"
    DATA_REFRESH = "data_refresh"
    FILTER_CHANGE = "filter_change"
    SORT_CHANGE = "sort_change"


class ActionType(Enum):
    """Available actions in the application."""
    # PR Actions
    OPEN_PR = "open_pr"
    VIEW_DETAILS = "view_details"
    CHECKOUT_BRANCH = "checkout_branch"
    MERGE_PR = "merge_pr"
    CLOSE_PR = "close_pr"
    APPROVE_PR = "approve_pr"
    REQUEST_CHANGES = "request_changes"
    
    # Navigation Actions
    REFRESH_DATA = "refresh_data"
    TOGGLE_DETAIL_PANEL = "toggle_detail_panel"
    TOGGLE_FILTER_PANEL = "toggle_filter_panel"
    FOCUS_SEARCH = "focus_search"
    CLEAR_FILTERS = "clear_filters"
    
    # Selection Actions
    SELECT_ALL = "select_all"
    CLEAR_SELECTION = "clear_selection"
    TOGGLE_MULTI_SELECT = "toggle_multi_select"
    
    # View Actions
    SORT_BY_STATUS = "sort_by_status"
    SORT_BY_DATE = "sort_by_date"
    SORT_BY_AUTHOR = "sort_by_author"
    TOGGLE_COMPACT_MODE = "toggle_compact_mode"
    
    # CI Actions
    VIEW_LOGS = "view_logs"
    VIEW_ARTIFACTS = "view_artifacts"
    RETRY_CHECKS = "retry_checks"


@dataclass
class Event:
    """Base event class."""
    type: EventType
    data: Dict[str, Any]
    source: str = "unknown"
    timestamp: float = 0.0


@dataclass 
class KeyEvent(Event):
    """Keyboard event."""
    key: str
    modifiers: List[str] = None
    
    def __post_init__(self):
        self.type = EventType.KEY_PRESS
        if self.modifiers is None:
            self.modifiers = []


@dataclass
class Action:
    """Represents an action that can be triggered."""
    type: ActionType
    name: str
    description: str
    shortcut: Optional[str] = None
    enabled: bool = True
    context: List[str] = None  # Contexts where action is available
    
    def __post_init__(self):
        if self.context is None:
            self.context = ["global"]


class EventBus:
    """Central event bus for the application."""
    
    def __init__(self):
        self._listeners: Dict[EventType, List[Callable]] = {}
        self._action_handlers: Dict[ActionType, Callable] = {}
    
    def subscribe(self, event_type: EventType, handler: Callable):
        """Subscribe to an event type."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(handler)
    
    def unsubscribe(self, event_type: EventType, handler: Callable):
        """Unsubscribe from an event type."""
        if event_type in self._listeners:
            try:
                self._listeners[event_type].remove(handler)
            except ValueError:
                pass
    
    def emit(self, event: Event):
        """Emit an event to all listeners."""
        if event.type in self._listeners:
            for handler in self._listeners[event.type]:
                try:
                    handler(event)
                except Exception as e:
                    # Log error but don't stop other handlers
                    pass
    
    def register_action_handler(self, action_type: ActionType, handler: Callable):
        """Register a handler for an action."""
        self._action_handlers[action_type] = handler
    
    def trigger_action(self, action_type: ActionType, context: Dict[str, Any] = None):
        """Trigger an action."""
        if action_type in self._action_handlers:
            try:
                handler = self._action_handlers[action_type]
                if context:
                    handler(context)
                else:
                    handler()
            except Exception as e:
                # Handle action error
                error_event = Event(
                    type=EventType.ACTION_TRIGGERED,
                    data={"action": action_type, "error": str(e)},
                    source="action_handler"
                )
                self.emit(error_event)


class ContextMenu:
    """Context menu for PR items."""
    
    def __init__(self):
        self.items: List[Action] = []
        self.visible = False
        self.position = (0, 0)
        self.selected_index = 0
    
    def show(self, x: int, y: int, context: str, pr_ids: List[int] = None):
        """Show context menu at position."""
        self.position = (x, y)
        self.visible = True
        self.selected_index = 0
        self.items = self._get_context_actions(context, pr_ids)
    
    def hide(self):
        """Hide context menu."""
        self.visible = False
        self.items = []
    
    def select_next(self):
        """Select next menu item."""
        if self.items:
            self.selected_index = (self.selected_index + 1) % len(self.items)
    
    def select_previous(self):
        """Select previous menu item."""
        if self.items:
            self.selected_index = (self.selected_index - 1) % len(self.items)
    
    def get_selected_action(self) -> Optional[Action]:
        """Get currently selected action."""
        if 0 <= self.selected_index < len(self.items):
            return self.items[self.selected_index]
        return None
    
    def _get_context_actions(self, context: str, pr_ids: List[int] = None) -> List[Action]:
        """Get actions available for the given context."""
        actions = []
        
        if context == "pr_list":
            actions.extend([
                Action(ActionType.VIEW_DETAILS, "View Details", "View PR details", "Enter"),
                Action(ActionType.OPEN_PR, "Open in Browser", "Open PR in web browser", "O"),
                Action(ActionType.CHECKOUT_BRANCH, "Checkout Branch", "Checkout PR branch", "C"),
                Action(ActionType.REFRESH_DATA, "Refresh", "Refresh PR data", "R"),
            ])
            
            if pr_ids and len(pr_ids) == 1:
                actions.extend([
                    Action(ActionType.APPROVE_PR, "Approve", "Approve this PR"),
                    Action(ActionType.REQUEST_CHANGES, "Request Changes", "Request changes"),
                    Action(ActionType.MERGE_PR, "Merge", "Merge this PR"),
                    Action(ActionType.CLOSE_PR, "Close", "Close this PR"),
                ])
            elif pr_ids and len(pr_ids) > 1:
                actions.extend([
                    Action(ActionType.MERGE_PR, f"Merge {len(pr_ids)} PRs", "Merge selected PRs"),
                    Action(ActionType.CLOSE_PR, f"Close {len(pr_ids)} PRs", "Close selected PRs"),
                ])
        
        elif context == "ci_status":
            actions.extend([
                Action(ActionType.VIEW_LOGS, "View Logs", "View CI logs", "L"),
                Action(ActionType.VIEW_ARTIFACTS, "View Artifacts", "View artifacts", "A"),
                Action(ActionType.RETRY_CHECKS, "Retry Checks", "Retry failed checks"),
            ])
        
        return actions


class KeyboardShortcuts:
    """Manages keyboard shortcuts and key bindings."""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.shortcuts: Dict[str, ActionType] = {}
        self.context_shortcuts: Dict[str, Dict[str, ActionType]] = {}
        self._setup_default_shortcuts()
    
    def _setup_default_shortcuts(self):
        """Setup default keyboard shortcuts."""
        # Global shortcuts
        self.shortcuts.update({
            "r": ActionType.REFRESH_DATA,
            "ctrl+r": ActionType.REFRESH_DATA,
            "f": ActionType.FOCUS_SEARCH,
            "ctrl+f": ActionType.FOCUS_SEARCH,
            "escape": ActionType.CLEAR_FILTERS,
            "ctrl+a": ActionType.SELECT_ALL,
            "ctrl+d": ActionType.CLEAR_SELECTION,
            "v": ActionType.TOGGLE_MULTI_SELECT,
            "d": ActionType.TOGGLE_DETAIL_PANEL,
            "t": ActionType.TOGGLE_COMPACT_MODE,
            "?": "show_help",  # Special case
        })
        
        # Context-specific shortcuts
        self.context_shortcuts["pr_list"] = {
            "enter": ActionType.VIEW_DETAILS,
            "o": ActionType.OPEN_PR,
            "c": ActionType.CHECKOUT_BRANCH,
            "s": ActionType.SORT_BY_STATUS,
            "u": ActionType.SORT_BY_DATE,
            "a": ActionType.SORT_BY_AUTHOR,
        }
        
        self.context_shortcuts["ci_status"] = {
            "l": ActionType.VIEW_LOGS,
            "a": ActionType.VIEW_ARTIFACTS,
            "r": ActionType.RETRY_CHECKS,
        }
    
    def handle_key(self, key: str, context: str = "global") -> bool:
        """
        Handle keyboard input and trigger appropriate actions.
        Returns True if key was handled.
        """
        # Check context-specific shortcuts first
        if context in self.context_shortcuts:
            if key in self.context_shortcuts[context]:
                action_type = self.context_shortcuts[context][key]
                self.event_bus.trigger_action(action_type)
                return True
        
        # Check global shortcuts
        if key in self.shortcuts:
            action_value = self.shortcuts[key]
            if isinstance(action_value, ActionType):
                self.event_bus.trigger_action(action_value)
                return True
            elif action_value == "show_help":
                # Special case for help
                self._show_help()
                return True
        
        return False
    
    def _show_help(self):
        """Show help dialog with available shortcuts."""
        help_event = Event(
            type=EventType.ACTION_TRIGGERED,
            data={"action": "show_help", "shortcuts": self._get_help_content()},
            source="keyboard_shortcuts"
        )
        self.event_bus.emit(help_event)
    
    def _get_help_content(self) -> Dict[str, List[str]]:
        """Get help content for shortcuts."""
        return {
            "Navigation": [
                "↑/k: Move up",
                "↓/j: Move down", 
                "Page Up/Down: Fast scroll",
                "Home/g: Go to top",
                "End/G: Go to bottom",
            ],
            "Actions": [
                "Enter: View details",
                "Space: Toggle selection",
                "o: Open in browser",
                "c: Checkout branch",
                "r: Refresh data",
            ],
            "View": [
                "d: Toggle detail panel",
                "t: Toggle compact mode",
                "f: Focus search",
                "v: Toggle multi-select",
                "Tab: Switch tabs",
            ],
            "Sorting": [
                "s: Sort by status",
                "u: Sort by date",
                "a: Sort by author",
            ]
        }


class InteractionManager:
    """Manages interactive features and user interactions."""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.context_menu = ContextMenu()
        self.shortcuts = KeyboardShortcuts(event_bus)
        self.loading_states: Dict[str, bool] = {}
        self.error_states: Dict[str, str] = {}
        
        # Setup event handlers
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Setup event handlers."""
        self.event_bus.subscribe(EventType.KEY_PRESS, self._handle_key_event)
        self.event_bus.subscribe(EventType.MOUSE_CLICK, self._handle_mouse_event)
    
    def _handle_key_event(self, event: Event):
        """Handle keyboard events."""
        if not isinstance(event, KeyEvent):
            return
        
        key = event.key
        
        # Handle context menu navigation
        if self.context_menu.visible:
            if key == "up":
                self.context_menu.select_previous()
                return
            elif key == "down":
                self.context_menu.select_next()
                return
            elif key == "enter":
                action = self.context_menu.get_selected_action()
                if action:
                    self.event_bus.trigger_action(action.type)
                self.context_menu.hide()
                return
            elif key == "escape":
                self.context_menu.hide()
                return
        
        # Handle regular shortcuts
        context = event.data.get("context", "global")
        self.shortcuts.handle_key(key, context)
    
    def _handle_mouse_event(self, event: Event):
        """Handle mouse events."""
        if event.data.get("button") == "right":
            # Right click - show context menu
            x, y = event.data.get("position", (0, 0))
            context = event.data.get("context", "pr_list")
            pr_ids = event.data.get("pr_ids", [])
            self.show_context_menu(x, y, context, pr_ids)
    
    def show_context_menu(self, x: int, y: int, context: str, pr_ids: List[int] = None):
        """Show context menu."""
        self.context_menu.show(x, y, context, pr_ids)
    
    def hide_context_menu(self):
        """Hide context menu."""
        self.context_menu.hide()
    
    def set_loading_state(self, component: str, loading: bool):
        """Set loading state for a component."""
        self.loading_states[component] = loading
        
        loading_event = Event(
            type=EventType.DATA_REFRESH,
            data={"component": component, "loading": loading},
            source="interaction_manager"
        )
        self.event_bus.emit(loading_event)
    
    def set_error_state(self, component: str, error: str = None):
        """Set error state for a component."""
        if error:
            self.error_states[component] = error
        else:
            self.error_states.pop(component, None)
        
        error_event = Event(
            type=EventType.ACTION_TRIGGERED,
            data={"component": component, "error": error},
            source="interaction_manager"
        )
        self.event_bus.emit(error_event)
    
    def is_loading(self, component: str) -> bool:
        """Check if component is in loading state."""
        return self.loading_states.get(component, False)
    
    def get_error(self, component: str) -> Optional[str]:
        """Get error message for component."""
        return self.error_states.get(component)