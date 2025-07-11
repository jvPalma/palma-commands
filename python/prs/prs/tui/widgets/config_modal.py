"""
Configuration modal for TUI.

Provides a user-friendly interface for viewing and modifying
PRS configuration settings without editing files directly.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, Tabs, TabPane
from textual.widgets import (
    Input, Button, Label, Checkbox, Select, 
    Static, OptionList, TabbedContent, Tab
)
from textual.widget import Widget
from textual.message import Message
from textual.screen import ModalScreen

from prs.config import get, set, all_config


@dataclass
class ConfigChange:
    """Represents a configuration change."""
    section: str
    key: str
    old_value: Any
    new_value: Any


class ConfigModal(ModalScreen):
    """
    Configuration modal for managing PRS settings.
    
    Features:
    - Tabbed interface for different config sections
    - Real-time validation
    - Preview of changes before applying
    - Reset to defaults option
    """
    
    DEFAULT_CSS = """
    ConfigModal {
        align: center middle;
    }
    
    #config_container {
        width: 90%;
        height: 85%;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }
    
    #config_title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    
    #config_tabs {
        height: 80%;
        margin-bottom: 1;
    }
    
    #button_container {
        height: auto;
        align: center middle;
    }
    
    .config_section {
        padding: 1;
        height: 100%;
    }
    
    .config_row {
        height: auto;
        margin-bottom: 1;
    }
    
    .config_label {
        width: 25%;
        text-align: right;
        margin-right: 2;
    }
    
    .config_input {
        width: 50%;
        margin-right: 1;
    }
    
    .config_description {
        width: 25%;
        color: $text-muted;
    }
    
    .config_button {
        width: auto;
        margin-left: 1;
    }
    
    .section_title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    
    .validation_error {
        color: $error;
        text-style: italic;
    }
    
    .validation_success {
        color: $success;
        text-style: italic;
    }
    """
    
    class ConfigSaved(Message):
        """Message sent when configuration is saved."""
        def __init__(self, changes: List[ConfigChange]) -> None:
            super().__init__()
            self.changes = changes
    
    class ConfigCancelled(Message):
        """Message sent when configuration editing is cancelled."""
        pass
    
    def __init__(self):
        super().__init__()
        self.original_config = all_config()
        self.pending_changes: List[ConfigChange] = []
        self.validation_errors: Dict[str, str] = {}
        
        # Config schema for validation and descriptions
        self.config_schema = {
            'git': {
                'username': {
                    'type': 'string',
                    'description': 'Your Git username',
                    'required': True
                },
                'repo_name': {
                    'type': 'string', 
                    'description': 'Repository name',
                    'required': True
                },
                'org': {
                    'type': 'string',
                    'description': 'Organization name',
                    'required': False
                }
            },
            'git-org': {
                'name': {
                    'type': 'string',
                    'description': 'Organization display name',
                    'required': False
                }
            },
            'vctool': {
                'platform': {
                    'type': 'select',
                    'options': ['github', 'gitlab', 'bitbucket'],
                    'description': 'Version control platform',
                    'required': True
                }
            },
            'pr-info': {
                'ci': {
                    'type': 'select',
                    'options': ['none', 'short', 'normal', 'long'],
                    'description': 'CI/CD information verbosity',
                    'required': False
                },
                'reviews': {
                    'type': 'select',
                    'options': ['none', 'short', 'normal', 'long'],
                    'description': 'Review information verbosity',
                    'required': False
                },
                'labels': {
                    'type': 'select',
                    'options': ['none', 'short', 'normal', 'long'],
                    'description': 'Label information verbosity',
                    'required': False
                },
                'comments': {
                    'type': 'select',
                    'options': ['none', 'short', 'normal', 'long'],
                    'description': 'Comment information verbosity',
                    'required': False
                },
                'author': {
                    'type': 'select',
                    'options': ['none', 'short', 'normal', 'long'],
                    'description': 'Author information verbosity',
                    'required': False
                },
                'branch': {
                    'type': 'select',
                    'options': ['none', 'short', 'normal', 'long'],
                    'description': 'Branch information verbosity',
                    'required': False
                },
                'pr_url': {
                    'type': 'select',
                    'options': ['none', 'short', 'normal', 'long'],
                    'description': 'PR URL information verbosity',
                    'required': False
                }
            },
            'tui': {
                'theme': {
                    'type': 'select',
                    'options': ['default', 'dark', 'light', 'github'],
                    'description': 'TUI color theme',
                    'required': False
                },
                'refresh_interval': {
                    'type': 'number',
                    'description': 'Auto-refresh interval (seconds)',
                    'required': False,
                    'min': 5,
                    'max': 300
                },
                'animation': {
                    'type': 'boolean',
                    'description': 'Enable UI animations',
                    'required': False
                }
            }
        }
    
    def compose(self) -> ComposeResult:
        """Compose the configuration modal."""
        with Container(id="config_container"):
            yield Label("⚙️ Configuration Settings", id="config_title")
            
            with TabbedContent(id="config_tabs"):
                # Git Configuration Tab
                with TabPane("Git", id="git_tab"):
                    yield self._create_section_content("git")
                
                # Git Organization Tab  
                with TabPane("Organization", id="git_org_tab"):
                    yield self._create_section_content("git-org")
                
                # Version Control Tab
                with TabPane("VC Tool", id="vctool_tab"):
                    yield self._create_section_content("vctool")
                
                # PR Info Tab
                with TabPane("PR Display", id="pr_info_tab"):
                    yield self._create_section_content("pr-info")
                
                # TUI Settings Tab
                with TabPane("TUI", id="tui_tab"):
                    yield self._create_section_content("tui")
            
            with Horizontal(id="button_container"):
                yield Button("Save Changes", variant="primary", id="save_button")
                yield Button("Reset to Defaults", id="reset_button")
                yield Button("Preview Changes", id="preview_button")
                yield Button("Cancel", id="cancel_button")
    
    def _create_section_content(self, section: str) -> Container:
        """Create content for a configuration section."""
        container = Container(classes="config_section")
        
        with container:
            yield Label(f"{section.title().replace('-', ' ')} Settings", classes="section_title")
            
            schema = self.config_schema.get(section, {})
            current_values = self.original_config.get(section, {})
            
            for key, config in schema.items():
                with Horizontal(classes="config_row"):
                    # Label
                    yield Label(f"{key.replace('_', ' ').title()}:", classes="config_label")
                    
                    # Input widget based on type
                    widget_id = f"{section}_{key}"
                    current_value = current_values.get(key, "")
                    
                    if config['type'] == 'select':
                        options = [(opt.title(), opt) for opt in config['options']]
                        widget = Select(
                            options,
                            value=current_value,
                            id=widget_id,
                            classes="config_input"
                        )
                    elif config['type'] == 'boolean':
                        widget = Checkbox(
                            "",
                            value=current_value.lower() == 'true' if isinstance(current_value, str) else bool(current_value),
                            id=widget_id,
                            classes="config_input"
                        )
                    elif config['type'] == 'number':
                        widget = Input(
                            value=str(current_value),
                            placeholder=f"Min: {config.get('min', 'N/A')}, Max: {config.get('max', 'N/A')}",
                            id=widget_id,
                            classes="config_input"
                        )
                    else:  # string
                        widget = Input(
                            value=str(current_value),
                            placeholder=config.get('placeholder', ''),
                            id=widget_id,
                            classes="config_input"
                        )
                    
                    yield widget
                    
                    # Description
                    description = config.get('description', '')
                    if config.get('required'):
                        description += " (Required)"
                    
                    yield Label(description, classes="config_description")
                
                # Validation message area
                yield Static("", id=f"validation_{widget_id}", classes="validation_error")
        
        return container
    
    def on_mount(self) -> None:
        """Called when the modal is mounted."""
        self._validate_all_inputs()
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        self._validate_input(event.input.id, event.value)
        self._update_pending_changes()
    
    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select changes."""
        self._validate_input(event.select.id, event.value)
        self._update_pending_changes()
    
    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox changes."""
        self._validate_input(event.checkbox.id, event.value)
        self._update_pending_changes()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save_button":
            self._save_configuration()
        elif event.button.id == "reset_button":
            self._reset_to_defaults()
        elif event.button.id == "preview_button":
            self._preview_changes()
        elif event.button.id == "cancel_button":
            self._cancel_configuration()
    
    def _validate_input(self, widget_id: str, value: Any) -> bool:
        """Validate a single input."""
        # Parse widget ID to get section and key
        parts = widget_id.split('_', 1)
        if len(parts) != 2:
            return True
        
        section, key = parts
        schema = self.config_schema.get(section, {}).get(key, {})
        
        validation_widget = self.query_one(f"#validation_{widget_id}")
        
        # Required field validation
        if schema.get('required') and not value:
            error_msg = "This field is required"
            validation_widget.update(error_msg)
            validation_widget.add_class("validation_error")
            validation_widget.remove_class("validation_success")
            self.validation_errors[widget_id] = error_msg
            return False
        
        # Type-specific validation
        if schema.get('type') == 'number':
            try:
                num_value = int(value) if value else 0
                min_val = schema.get('min')
                max_val = schema.get('max')
                
                if min_val is not None and num_value < min_val:
                    error_msg = f"Value must be at least {min_val}"
                    validation_widget.update(error_msg)
                    validation_widget.add_class("validation_error")
                    validation_widget.remove_class("validation_success")
                    self.validation_errors[widget_id] = error_msg
                    return False
                
                if max_val is not None and num_value > max_val:
                    error_msg = f"Value must be at most {max_val}"
                    validation_widget.update(error_msg)
                    validation_widget.add_class("validation_error")
                    validation_widget.remove_class("validation_success")
                    self.validation_errors[widget_id] = error_msg
                    return False
                    
            except ValueError:
                error_msg = "Must be a valid number"
                validation_widget.update(error_msg)
                validation_widget.add_class("validation_error")
                validation_widget.remove_class("validation_success")
                self.validation_errors[widget_id] = error_msg
                return False
        
        # Clear validation error
        validation_widget.update("✓ Valid")
        validation_widget.add_class("validation_success")
        validation_widget.remove_class("validation_error")
        self.validation_errors.pop(widget_id, None)
        return True
    
    def _validate_all_inputs(self) -> bool:
        """Validate all inputs."""
        all_valid = True
        
        for section, schema in self.config_schema.items():
            for key in schema.keys():
                widget_id = f"{section}_{key}"
                try:
                    widget = self.query_one(f"#{widget_id}")
                    if hasattr(widget, 'value'):
                        if not self._validate_input(widget_id, widget.value):
                            all_valid = False
                except Exception:
                    pass
        
        return all_valid
    
    def _update_pending_changes(self) -> None:
        """Update the list of pending changes."""
        self.pending_changes.clear()
        
        for section, schema in self.config_schema.items():
            for key in schema.keys():
                widget_id = f"{section}_{key}"
                try:
                    widget = self.query_one(f"#{widget_id}")
                    if hasattr(widget, 'value'):
                        new_value = widget.value
                        old_value = self.original_config.get(section, {}).get(key, "")
                        
                        # Convert values for comparison
                        if isinstance(widget, Checkbox):
                            new_value = str(new_value).lower()
                            old_value = str(old_value).lower()
                        else:
                            new_value = str(new_value)
                            old_value = str(old_value)
                        
                        if new_value != old_value:
                            self.pending_changes.append(ConfigChange(
                                section=section,
                                key=key,
                                old_value=old_value,
                                new_value=new_value
                            ))
                except Exception:
                    pass
    
    def _save_configuration(self) -> None:
        """Save the configuration changes."""
        if not self._validate_all_inputs():
            return
        
        self._update_pending_changes()
        
        # Apply changes
        for change in self.pending_changes:
            set(change.section, change.key, change.new_value)
        
        # Post save message
        self.post_message(self.ConfigSaved(self.pending_changes))
        self.dismiss()
    
    def _reset_to_defaults(self) -> None:
        """Reset all values to defaults."""
        # This would reset to default values
        # For now, just clear all inputs
        for section, schema in self.config_schema.items():
            for key in schema.keys():
                widget_id = f"{section}_{key}"
                try:
                    widget = self.query_one(f"#{widget_id}")
                    if isinstance(widget, Input):
                        widget.value = ""
                    elif isinstance(widget, Select):
                        if schema[key].get('options'):
                            widget.value = schema[key]['options'][0]
                    elif isinstance(widget, Checkbox):
                        widget.value = False
                except Exception:
                    pass
        
        self._validate_all_inputs()
        self._update_pending_changes()
    
    def _preview_changes(self) -> None:
        """Preview the pending changes."""
        self._update_pending_changes()
        
        if not self.pending_changes:
            # Show "no changes" message
            return
        
        # This would open a preview dialog
        # For now, just validate
        self._validate_all_inputs()
    
    def _cancel_configuration(self) -> None:
        """Cancel configuration editing."""
        self.post_message(self.ConfigCancelled())
        self.dismiss()