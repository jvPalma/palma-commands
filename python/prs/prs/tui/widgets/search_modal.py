"""
Advanced search modal for TUI.

Provides powerful search and filtering capabilities for PRs,
including search by author, labels, CI status, and more.
"""

from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Input, Button, Label, Checkbox, Select, 
    Static, OptionList, RadioSet, RadioButton
)
from textual.widget import Widget
from textual.message import Message
from textual.screen import ModalScreen

from prs.core.models import PullRequest


class SearchType(Enum):
    """Types of search criteria."""
    TEXT = "text"
    AUTHOR = "author"
    LABELS = "labels"
    CI_STATUS = "ci_status"
    REVIEW_STATUS = "review_status"
    DATE_RANGE = "date_range"


@dataclass
class SearchCriteria:
    """Represents search criteria."""
    search_type: SearchType
    value: Any
    operator: str = "contains"  # contains, equals, starts_with, ends_with
    case_sensitive: bool = False


@dataclass
class SearchFilter:
    """Represents a complete search filter."""
    criteria: List[SearchCriteria]
    combine_mode: str = "AND"  # AND, OR
    name: Optional[str] = None


class SearchModal(ModalScreen):
    """
    Advanced search modal for filtering PRs.
    
    Features:
    - Multiple search criteria
    - Saved search filters
    - Real-time preview
    - Advanced filtering options
    """
    
    DEFAULT_CSS = """
    SearchModal {
        align: center middle;
    }
    
    #search_container {
        width: 80%;
        height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }
    
    #search_title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    
    #criteria_container {
        height: 60%;
        border: solid $secondary;
        padding: 1;
        margin-bottom: 1;
    }
    
    #preview_container {
        height: 20%;
        border: solid $secondary;
        padding: 1;
        margin-bottom: 1;
    }
    
    #button_container {
        height: auto;
        align: center middle;
    }
    
    .search_row {
        height: auto;
        margin-bottom: 1;
    }
    
    .search_input {
        width: 1fr;
        margin-right: 1;
    }
    
    .search_select {
        width: 20;
        margin-right: 1;
    }
    
    .search_button {
        width: auto;
        margin-left: 1;
    }
    """
    
    class SearchSubmitted(Message):
        """Message sent when search is submitted."""
        def __init__(self, search_filter: SearchFilter) -> None:
            super().__init__()
            self.search_filter = search_filter
    
    class SearchCancelled(Message):
        """Message sent when search is cancelled."""
        pass
    
    def __init__(self, prs: List[PullRequest], 
                 saved_filters: List[SearchFilter] = None,
                 current_filter: SearchFilter = None):
        super().__init__()
        self.prs = prs
        self.saved_filters = saved_filters or []
        self.current_filter = current_filter
        self.search_criteria: List[SearchCriteria] = []
        self.preview_results: List[PullRequest] = []
        
        # Initialize with current filter if provided
        if current_filter:
            self.search_criteria = current_filter.criteria.copy()
    
    def compose(self) -> ComposeResult:
        """Compose the search modal."""
        with Container(id="search_container"):
            yield Label("🔍 Advanced Search & Filters", id="search_title")
            
            with Vertical(id="criteria_container"):
                yield Label("Search Criteria:", classes="section_title")
                yield Container(id="criteria_list")
                
                with Horizontal(classes="search_row"):
                    yield Button("+ Add Criteria", id="add_criteria", classes="search_button")
                    yield Button("Clear All", id="clear_criteria", classes="search_button")
                
                with Horizontal(classes="search_row"):
                    yield Label("Combine with:")
                    yield RadioSet(
                        RadioButton("AND", value=True, id="combine_and"),
                        RadioButton("OR", id="combine_or"),
                        id="combine_mode"
                    )
            
            with Vertical(id="preview_container"):
                yield Label("Preview (0 results):", id="preview_label")
                yield Static("", id="preview_content")
            
            with Horizontal(id="button_container"):
                yield Button("Search", variant="primary", id="search_button")
                yield Button("Save Filter", id="save_filter")
                yield Button("Load Filter", id="load_filter") 
                yield Button("Cancel", id="cancel_button")
    
    def on_mount(self) -> None:
        """Called when the modal is mounted."""
        self._update_criteria_display()
        self._update_preview()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "add_criteria":
            self._add_criteria_row()
        elif event.button.id == "clear_criteria":
            self._clear_criteria()
        elif event.button.id == "search_button":
            self._submit_search()
        elif event.button.id == "save_filter":
            self._save_filter()
        elif event.button.id == "load_filter":
            self._load_filter()
        elif event.button.id == "cancel_button":
            self._cancel_search()
        elif event.button.id and event.button.id.startswith("remove_criteria_"):
            criteria_index = int(event.button.id.split("_")[-1])
            self._remove_criteria(criteria_index)
    
    def _add_criteria_row(self) -> None:
        """Add a new search criteria row."""
        criteria_container = self.query_one("#criteria_list")
        criteria_index = len(self.search_criteria)
        
        with criteria_container:
            with Horizontal(classes="search_row", id=f"criteria_row_{criteria_index}"):
                # Search type selector
                type_select = Select([
                    ("Text Search", SearchType.TEXT.value),
                    ("Author", SearchType.AUTHOR.value),
                    ("Labels", SearchType.LABELS.value),
                    ("CI Status", SearchType.CI_STATUS.value),
                    ("Review Status", SearchType.REVIEW_STATUS.value),
                    ("Date Range", SearchType.DATE_RANGE.value)
                ], id=f"type_{criteria_index}", classes="search_select")
                yield type_select
                
                # Operator selector
                operator_select = Select([
                    ("Contains", "contains"),
                    ("Equals", "equals"),
                    ("Starts With", "starts_with"),
                    ("Ends With", "ends_with")
                ], id=f"operator_{criteria_index}", classes="search_select")
                yield operator_select
                
                # Value input
                value_input = Input(
                    placeholder="Search value...",
                    id=f"value_{criteria_index}",
                    classes="search_input"
                )
                yield value_input
                
                # Case sensitive checkbox
                case_check = Checkbox(
                    "Case sensitive",
                    id=f"case_{criteria_index}"
                )
                yield case_check
                
                # Remove button
                remove_btn = Button(
                    "×", 
                    id=f"remove_criteria_{criteria_index}",
                    classes="search_button"
                )
                yield remove_btn
        
        # Add empty criteria to track
        self.search_criteria.append(SearchCriteria(
            search_type=SearchType.TEXT,
            value="",
            operator="contains",
            case_sensitive=False
        ))
        
        # Focus on the new input
        value_input.focus()
    
    def _remove_criteria(self, index: int) -> None:
        """Remove a search criteria row."""
        if 0 <= index < len(self.search_criteria):
            # Remove from criteria list
            self.search_criteria.pop(index)
            
            # Remove from UI
            row = self.query_one(f"#criteria_row_{index}")
            row.remove()
            
            # Re-index remaining rows
            self._update_criteria_display()
            self._update_preview()
    
    def _clear_criteria(self) -> None:
        """Clear all search criteria."""
        self.search_criteria.clear()
        criteria_container = self.query_one("#criteria_list")
        criteria_container.remove_children()
        self._update_preview()
    
    def _update_criteria_display(self) -> None:
        """Update the criteria display."""
        # This would normally re-render the criteria list
        # For now, just update the preview
        self._update_preview()
    
    def _update_preview(self) -> None:
        """Update the search preview."""
        if not self.search_criteria:
            self.preview_results = self.prs.copy()
        else:
            self.preview_results = self._apply_filters(self.prs)
        
        # Update preview label
        preview_label = self.query_one("#preview_label")
        preview_label.update(f"Preview ({len(self.preview_results)} results):")
        
        # Update preview content
        preview_content = self.query_one("#preview_content")
        if self.preview_results:
            preview_text = "\n".join([
                f"#{pr.id} - {pr.title[:50]}{'...' if len(pr.title) > 50 else ''}"
                for pr in self.preview_results[:5]
            ])
            if len(self.preview_results) > 5:
                preview_text += f"\n... and {len(self.preview_results) - 5} more"
        else:
            preview_text = "No PRs match the current criteria."
        
        preview_content.update(preview_text)
    
    def _apply_filters(self, prs: List[PullRequest]) -> List[PullRequest]:
        """Apply search filters to PR list."""
        if not self.search_criteria:
            return prs
        
        filtered_prs = []
        combine_mode = self._get_combine_mode()
        
        for pr in prs:
            if combine_mode == "AND":
                # All criteria must match
                if all(self._check_criteria(pr, criteria) for criteria in self.search_criteria):
                    filtered_prs.append(pr)
            else:  # OR
                # Any criteria must match
                if any(self._check_criteria(pr, criteria) for criteria in self.search_criteria):
                    filtered_prs.append(pr)
        
        return filtered_prs
    
    def _check_criteria(self, pr: PullRequest, criteria: SearchCriteria) -> bool:
        """Check if a PR matches the given criteria."""
        try:
            if criteria.search_type == SearchType.TEXT:
                return self._check_text_criteria(pr, criteria)
            elif criteria.search_type == SearchType.AUTHOR:
                return self._check_author_criteria(pr, criteria)
            elif criteria.search_type == SearchType.LABELS:
                return self._check_labels_criteria(pr, criteria)
            elif criteria.search_type == SearchType.CI_STATUS:
                return self._check_ci_status_criteria(pr, criteria)
            elif criteria.search_type == SearchType.REVIEW_STATUS:
                return self._check_review_status_criteria(pr, criteria)
            elif criteria.search_type == SearchType.DATE_RANGE:
                return self._check_date_range_criteria(pr, criteria)
        except Exception:
            return False
        
        return False
    
    def _check_text_criteria(self, pr: PullRequest, criteria: SearchCriteria) -> bool:
        """Check text-based criteria."""
        search_text = str(criteria.value)
        if not criteria.case_sensitive:
            search_text = search_text.lower()
        
        # Search in title and description
        title = pr.title if criteria.case_sensitive else pr.title.lower()
        
        if criteria.operator == "contains":
            return search_text in title
        elif criteria.operator == "equals":
            return search_text == title
        elif criteria.operator == "starts_with":
            return title.startswith(search_text)
        elif criteria.operator == "ends_with":
            return title.endswith(search_text)
        
        return False
    
    def _check_author_criteria(self, pr: PullRequest, criteria: SearchCriteria) -> bool:
        """Check author-based criteria."""
        author = pr.author if criteria.case_sensitive else pr.author.lower()
        search_author = str(criteria.value)
        if not criteria.case_sensitive:
            search_author = search_author.lower()
        
        if criteria.operator == "contains":
            return search_author in author
        elif criteria.operator == "equals":
            return search_author == author
        elif criteria.operator == "starts_with":
            return author.startswith(search_author)
        elif criteria.operator == "ends_with":
            return author.endswith(search_author)
        
        return False
    
    def _check_labels_criteria(self, pr: PullRequest, criteria: SearchCriteria) -> bool:
        """Check label-based criteria."""
        search_label = str(criteria.value)
        if not criteria.case_sensitive:
            search_label = search_label.lower()
        
        for label in pr.labels:
            label_name = label if criteria.case_sensitive else label.lower()
            
            if criteria.operator == "contains":
                if search_label in label_name:
                    return True
            elif criteria.operator == "equals":
                if search_label == label_name:
                    return True
            elif criteria.operator == "starts_with":
                if label_name.startswith(search_label):
                    return True
            elif criteria.operator == "ends_with":
                if label_name.endswith(search_label):
                    return True
        
        return False
    
    def _check_ci_status_criteria(self, pr: PullRequest, criteria: SearchCriteria) -> bool:
        """Check CI status criteria."""
        search_status = str(criteria.value).lower()
        
        if hasattr(pr, 'ci_data') and pr.ci_data:
            if search_status == "passing" and pr.ci_data.failed_workflows == 0 and pr.ci_data.successful_workflows > 0:
                return True
            elif search_status == "failing" and pr.ci_data.failed_workflows > 0:
                return True
            elif search_status == "pending" and pr.ci_data.pending_workflows > 0:
                return True
            elif search_status == "none" and pr.ci_data.total_workflows == 0:
                return True
        
        return False
    
    def _check_review_status_criteria(self, pr: PullRequest, criteria: SearchCriteria) -> bool:
        """Check review status criteria."""
        search_status = str(criteria.value).lower()
        
        approved_count = sum(1 for review in pr.reviews if review.get('state') == 'APPROVED')
        requested_count = sum(1 for review in pr.reviews if review.get('state') == 'REVIEW_REQUESTED')
        changes_requested = sum(1 for review in pr.reviews if review.get('state') == 'CHANGES_REQUESTED')
        
        if search_status == "approved" and approved_count > 0:
            return True
        elif search_status == "pending" and requested_count > 0:
            return True
        elif search_status == "changes_requested" and changes_requested > 0:
            return True
        elif search_status == "none" and len(pr.reviews) == 0:
            return True
        
        return False
    
    def _check_date_range_criteria(self, pr: PullRequest, criteria: SearchCriteria) -> bool:
        """Check date range criteria."""
        # This would need to parse date ranges from the criteria value
        # For now, return True
        return True
    
    def _get_combine_mode(self) -> str:
        """Get the current combine mode."""
        try:
            radio_set = self.query_one("#combine_mode")
            if radio_set.pressed_button and radio_set.pressed_button.id == "combine_or":
                return "OR"
        except Exception:
            pass
        return "AND"
    
    def _submit_search(self) -> None:
        """Submit the search."""
        # Collect current criteria from UI
        self._collect_criteria_from_ui()
        
        # Create search filter
        search_filter = SearchFilter(
            criteria=self.search_criteria.copy(),
            combine_mode=self._get_combine_mode()
        )
        
        # Post search submitted message
        self.post_message(self.SearchSubmitted(search_filter))
        self.dismiss()
    
    def _save_filter(self) -> None:
        """Save the current filter."""
        # This would open a dialog to name and save the filter
        # For now, just collect criteria
        self._collect_criteria_from_ui()
    
    def _load_filter(self) -> None:
        """Load a saved filter."""
        # This would open a dialog to select and load a saved filter
        pass
    
    def _cancel_search(self) -> None:
        """Cancel the search."""
        self.post_message(self.SearchCancelled())
        self.dismiss()
    
    def _collect_criteria_from_ui(self) -> None:
        """Collect search criteria from UI elements."""
        # This would extract values from all the input fields
        # and update self.search_criteria
        # For now, keep existing criteria
        pass