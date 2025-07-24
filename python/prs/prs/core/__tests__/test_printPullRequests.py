"""
Unit tests for the main PR listing and display functionality.

Tests cover:
- PR listing and display orchestration
- Filtering logic (ignored PRs, reviewer filtering)
- Sorting and display logic  
- Error handling and edge cases
- Integration with display system and GitHub client
"""

import pytest
from unittest.mock import patch, MagicMock, call
from rich.console import Console

from prs.core.printPullRequests import list_pull_requests
from prs.core.models import PullRequest


class TestListPullRequestsBasicFunctionality:
    """Test basic functionality of list_pull_requests function."""

    @patch('prs.core.printPullRequests.render_ignored_count')
    @patch('prs.core.printPullRequests.render_pr_panel')
    @patch('prs.core.printPullRequests.Console')
    @patch('prs.core.printPullRequests.get_ignored_prs')
    @patch('prs.core.printPullRequests.get_pull_request_details')
    @patch('prs.core.printPullRequests.list_pull_request_ids')
    @patch('prs.core.printPullRequests.resolve_display_modes')
    def test_basic_pr_listing_flow(self, mock_resolve_modes, mock_list_ids, 
                                 mock_get_details, mock_get_ignored, mock_console_class,
                                 mock_render_panel, mock_render_count):
        """Test the basic flow of listing pull requests."""
        # Setup mocks
        mock_resolve_modes.return_value = {"include_drafts": False}
        mock_list_ids.return_value = [(123, "authored", False), (456, "team", True)]
        
        # Create mock PR objects  
        pr1 = MagicMock(spec=PullRequest)
        pr1.id = 123
        pr1.isDraft = False
        pr2 = MagicMock(spec=PullRequest) 
        pr2.id = 456
        pr2.isDraft = True
        
        mock_get_details.side_effect = [pr1, pr2]
        mock_get_ignored.return_value = []
        mock_console = MagicMock(spec=Console)
        mock_console_class.return_value = mock_console
        
        # Call the function
        options = {"no_reviewer": False, "no_reviewed": False}
        list_pull_requests(options)
        
        # Verify the flow
        mock_resolve_modes.assert_called_once_with(options)
        mock_list_ids.assert_called_once_with({
            "state": "open",
            "include_draft": False,
            "no_reviewer": False,
            "no_reviewed": False,
        })
        
        # Verify PR details were fetched
        assert mock_get_details.call_count == 2
        mock_get_details.assert_any_call(123, "authored")
        mock_get_details.assert_any_call(456, "team")
        
        # Verify source and isDraft were set
        assert pr1.source == "authored"
        assert pr1.isDraft is False
        assert pr2.source == "team" 
        assert pr2.isDraft is True
        
        # Verify PRs were rendered
        assert mock_render_panel.call_count == 2
        mock_render_count.assert_called_once_with(0, mock_console)

    @patch('prs.core.printPullRequests.render_ignored_count')
    @patch('prs.core.printPullRequests.render_pr_panel')
    @patch('prs.core.printPullRequests.Console')
    @patch('prs.core.printPullRequests.get_ignored_prs')
    @patch('prs.core.printPullRequests.get_pull_request_details')
    @patch('prs.core.printPullRequests.list_pull_request_ids')
    @patch('prs.core.printPullRequests.resolve_display_modes')
    def test_empty_pr_list(self, mock_resolve_modes, mock_list_ids, 
                          mock_get_details, mock_get_ignored, mock_console_class,
                          mock_render_panel, mock_render_count):
        """Test handling of empty PR list."""
        # Setup mocks
        mock_resolve_modes.return_value = {"include_drafts": True}
        mock_list_ids.return_value = []
        mock_get_ignored.return_value = []
        mock_console = MagicMock(spec=Console)
        mock_console_class.return_value = mock_console
        
        # Call the function
        options = {}
        list_pull_requests(options)
        
        # Verify no PRs were processed
        mock_get_details.assert_not_called()
        mock_render_panel.assert_not_called()
        mock_render_count.assert_called_once_with(0, mock_console)


class TestListPullRequestsFiltering:
    """Test filtering functionality."""

    @patch('prs.core.printPullRequests.render_ignored_count')
    @patch('prs.core.printPullRequests.render_pr_panel')
    @patch('prs.core.printPullRequests.Console')
    @patch('prs.core.printPullRequests.get_ignored_prs')
    @patch('prs.core.printPullRequests.get_pull_request_details')
    @patch('prs.core.printPullRequests.list_pull_request_ids')
    @patch('prs.core.printPullRequests.resolve_display_modes')
    def test_ignored_prs_filtering(self, mock_resolve_modes, mock_list_ids,
                                 mock_get_details, mock_get_ignored, mock_console_class,
                                 mock_render_panel, mock_render_count):
        """Test that ignored PRs are filtered out."""
        # Setup mocks
        mock_resolve_modes.return_value = {"include_drafts": False}
        mock_list_ids.return_value = [(123, "authored", False), (456, "team", False), (789, "authored", False)]
        
        # Create mock PR objects
        pr1 = MagicMock(spec=PullRequest)
        pr1.id = 123
        pr2 = MagicMock(spec=PullRequest) 
        pr2.id = 456
        pr3 = MagicMock(spec=PullRequest)
        pr3.id = 789
        
        mock_get_details.side_effect = [pr1, pr2, pr3]
        mock_get_ignored.return_value = [456, 999]  # 456 should be filtered, 999 doesn't exist
        mock_console = MagicMock(spec=Console)
        mock_console_class.return_value = mock_console
        
        # Call the function
        options = {}
        list_pull_requests(options)
        
        # Verify only non-ignored PRs were rendered
        assert mock_render_panel.call_count == 2
        rendered_prs = [call.args[0] for call in mock_render_panel.call_args_list]
        rendered_ids = [pr.id for pr in rendered_prs]
        assert 123 in rendered_ids
        assert 456 not in rendered_ids  # Should be filtered
        assert 789 in rendered_ids
        
        # Verify ignored count is correct (1 PR was filtered)
        mock_render_count.assert_called_once_with(1, mock_console)

    @patch('prs.core.printPullRequests.render_ignored_count')
    @patch('prs.core.printPullRequests.render_pr_panel')
    @patch('prs.core.printPullRequests.Console')
    @patch('prs.core.printPullRequests.get_ignored_prs')
    @patch('prs.core.printPullRequests.get_pull_request_details')
    @patch('prs.core.printPullRequests.list_pull_request_ids')
    @patch('prs.core.printPullRequests.resolve_display_modes')
    def test_no_reviewer_filter_passed_through(self, mock_resolve_modes, mock_list_ids,
                                              mock_get_details, mock_get_ignored, mock_console_class,
                                              mock_render_panel, mock_render_count):
        """Test that no_reviewer filter is passed through to list_pull_request_ids."""
        # Setup mocks
        mock_resolve_modes.return_value = {"include_drafts": False}
        mock_list_ids.return_value = []
        mock_get_ignored.return_value = []
        mock_console = MagicMock(spec=Console)
        mock_console_class.return_value = mock_console
        
        # Call with no_reviewer=True
        options = {"no_reviewer": True, "no_reviewed": False}
        list_pull_requests(options)
        
        # Verify filter was passed through
        mock_list_ids.assert_called_once_with({
            "state": "open",
            "include_draft": False,
            "no_reviewer": True,
            "no_reviewed": False,
        })

    @patch('prs.core.printPullRequests.render_ignored_count')
    @patch('prs.core.printPullRequests.render_pr_panel')
    @patch('prs.core.printPullRequests.Console')
    @patch('prs.core.printPullRequests.get_ignored_prs')
    @patch('prs.core.printPullRequests.get_pull_request_details')
    @patch('prs.core.printPullRequests.list_pull_request_ids')
    @patch('prs.core.printPullRequests.resolve_display_modes')
    def test_no_reviewed_filter_passed_through(self, mock_resolve_modes, mock_list_ids,
                                             mock_get_details, mock_get_ignored, mock_console_class,
                                             mock_render_panel, mock_render_count):
        """Test that no_reviewed filter is passed through to list_pull_request_ids."""
        # Setup mocks
        mock_resolve_modes.return_value = {"include_drafts": True}
        mock_list_ids.return_value = []
        mock_get_ignored.return_value = []
        mock_console = MagicMock(spec=Console)
        mock_console_class.return_value = mock_console
        
        # Call with no_reviewed=True
        options = {"no_reviewer": False, "no_reviewed": True}
        list_pull_requests(options)
        
        # Verify filter was passed through
        mock_list_ids.assert_called_once_with({
            "state": "open",
            "include_draft": True,
            "no_reviewer": False,
            "no_reviewed": True,
        })

    @patch('prs.core.printPullRequests.render_ignored_count')
    @patch('prs.core.printPullRequests.render_pr_panel')
    @patch('prs.core.printPullRequests.Console')
    @patch('prs.core.printPullRequests.get_ignored_prs')
    @patch('prs.core.printPullRequests.get_pull_request_details')
    @patch('prs.core.printPullRequests.list_pull_request_ids')
    @patch('prs.core.printPullRequests.resolve_display_modes')
    def test_include_drafts_from_display_modes(self, mock_resolve_modes, mock_list_ids,
                                             mock_get_details, mock_get_ignored, mock_console_class,
                                             mock_render_panel, mock_render_count):
        """Test that include_drafts comes from resolved display modes."""
        # Setup mocks
        mock_resolve_modes.return_value = {"include_drafts": True}
        mock_list_ids.return_value = []
        mock_get_ignored.return_value = []
        mock_console = MagicMock(spec=Console)
        mock_console_class.return_value = mock_console
        
        # Call the function
        options = {}
        list_pull_requests(options)
        
        # Verify include_draft comes from modes, not options
        mock_list_ids.assert_called_once_with({
            "state": "open",
            "include_draft": True,  # From modes
            "no_reviewer": False,  # Default from options.get()
            "no_reviewed": False,  # Default from options.get()
        })


class TestListPullRequestsSorting:
    """Test sorting functionality."""

    @patch('prs.core.printPullRequests.render_ignored_count')
    @patch('prs.core.printPullRequests.render_pr_panel')
    @patch('prs.core.printPullRequests.Console')
    @patch('prs.core.printPullRequests.get_ignored_prs')
    @patch('prs.core.printPullRequests.get_pull_request_details')
    @patch('prs.core.printPullRequests.list_pull_request_ids')
    @patch('prs.core.printPullRequests.resolve_display_modes')
    def test_prs_sorted_by_id_ascending(self, mock_resolve_modes, mock_list_ids,
                                       mock_get_details, mock_get_ignored, mock_console_class,
                                       mock_render_panel, mock_render_count):
        """Test that PRs are sorted by ID in ascending order (oldest first)."""
        # Setup mocks
        mock_resolve_modes.return_value = {"include_drafts": False}
        # Return IDs in random order
        mock_list_ids.return_value = [(789, "authored", False), (123, "team", False), (456, "authored", False)]
        
        # Create mock PR objects with corresponding IDs
        pr1 = MagicMock(spec=PullRequest)
        pr1.id = 789
        pr2 = MagicMock(spec=PullRequest)
        pr2.id = 123
        pr3 = MagicMock(spec=PullRequest)
        pr3.id = 456
        
        mock_get_details.side_effect = [pr1, pr2, pr3]
        mock_get_ignored.return_value = []
        mock_console = MagicMock(spec=Console)
        mock_console_class.return_value = mock_console
        
        # Call the function
        options = {}
        list_pull_requests(options)
        
        # Verify PRs were rendered in ascending ID order
        assert mock_render_panel.call_count == 3
        rendered_prs = [call.args[0] for call in mock_render_panel.call_args_list]
        rendered_ids = [pr.id for pr in rendered_prs]
        assert rendered_ids == [123, 456, 789]  # Should be sorted ascending

    @patch('prs.core.printPullRequests.render_ignored_count')
    @patch('prs.core.printPullRequests.render_pr_panel')
    @patch('prs.core.printPullRequests.Console')
    @patch('prs.core.printPullRequests.get_ignored_prs')
    @patch('prs.core.printPullRequests.get_pull_request_details')
    @patch('prs.core.printPullRequests.list_pull_request_ids')
    @patch('prs.core.printPullRequests.resolve_display_modes')
    def test_sorting_with_duplicate_ids(self, mock_resolve_modes, mock_list_ids,
                                       mock_get_details, mock_get_ignored, mock_console_class,
                                       mock_render_panel, mock_render_count):
        """Test sorting behavior with duplicate PR IDs (edge case)."""
        # Setup mocks
        mock_resolve_modes.return_value = {"include_drafts": False}
        mock_list_ids.return_value = [(123, "authored", False), (123, "team", False)]
        
        # Create mock PR objects with same ID
        pr1 = MagicMock(spec=PullRequest)
        pr1.id = 123
        pr2 = MagicMock(spec=PullRequest)
        pr2.id = 123
        
        mock_get_details.side_effect = [pr1, pr2]
        mock_get_ignored.return_value = []
        mock_console = MagicMock(spec=Console)
        mock_console_class.return_value = mock_console
        
        # Call the function
        options = {}
        list_pull_requests(options)
        
        # Verify both PRs were rendered (stable sort)
        assert mock_render_panel.call_count == 2


class TestListPullRequestsDataFlow:
    """Test data flow and attribute setting."""

    @patch('prs.core.printPullRequests.render_ignored_count')
    @patch('prs.core.printPullRequests.render_pr_panel')
    @patch('prs.core.printPullRequests.Console')
    @patch('prs.core.printPullRequests.get_ignored_prs')
    @patch('prs.core.printPullRequests.get_pull_request_details')
    @patch('prs.core.printPullRequests.list_pull_request_ids')
    @patch('prs.core.printPullRequests.resolve_display_modes')
    def test_source_and_is_draft_attributes_set(self, mock_resolve_modes, mock_list_ids,
                                               mock_get_details, mock_get_ignored, mock_console_class,
                                               mock_render_panel, mock_render_count):
        """Test that source and isDraft attributes are properly set on PR objects."""
        # Setup mocks
        mock_resolve_modes.return_value = {"include_drafts": True}
        mock_list_ids.return_value = [
            (123, "authored", False), 
            (456, "review_requested", True),
            (789, "team", False)
        ]
        
        # Create mock PR objects
        pr1 = MagicMock(spec=PullRequest)
        pr1.id = 123
        pr2 = MagicMock(spec=PullRequest)
        pr2.id = 456
        pr3 = MagicMock(spec=PullRequest)
        pr3.id = 789
        
        mock_get_details.side_effect = [pr1, pr2, pr3]
        mock_get_ignored.return_value = []
        mock_console = MagicMock(spec=Console)
        mock_console_class.return_value = mock_console
        
        # Call the function
        options = {}
        list_pull_requests(options)
        
        # Verify attributes were set correctly
        assert pr1.source == "authored"
        assert pr1.isDraft is False
        
        assert pr2.source == "review_requested"
        assert pr2.isDraft is True
        
        assert pr3.source == "team"
        assert pr3.isDraft is False

    @patch('prs.core.printPullRequests.render_ignored_count')
    @patch('prs.core.printPullRequests.render_pr_panel')
    @patch('prs.core.printPullRequests.Console')
    @patch('prs.core.printPullRequests.get_ignored_prs')
    @patch('prs.core.printPullRequests.get_pull_request_details')
    @patch('prs.core.printPullRequests.list_pull_request_ids')
    @patch('prs.core.printPullRequests.resolve_display_modes')
    def test_display_modes_passed_to_render(self, mock_resolve_modes, mock_list_ids,
                                          mock_get_details, mock_get_ignored, mock_console_class,
                                          mock_render_panel, mock_render_count):
        """Test that resolved display modes are passed to render function."""
        # Setup mocks
        test_modes = {
            "include_drafts": True,
            "author": "short",
            "checks": "long",
            "reviews": "normal"
        }
        mock_resolve_modes.return_value = test_modes
        mock_list_ids.return_value = [(123, "authored", False)]
        
        pr = MagicMock(spec=PullRequest)
        pr.id = 123
        mock_get_details.return_value = pr
        mock_get_ignored.return_value = []
        mock_console = MagicMock(spec=Console)
        mock_console_class.return_value = mock_console
        
        # Call the function
        options = {"author": "short"}
        list_pull_requests(options)
        
        # Verify modes were passed to render
        mock_render_panel.assert_called_once_with(pr, test_modes, mock_console)


class TestListPullRequestsErrorHandling:
    """Test error handling scenarios."""

    @patch('prs.core.printPullRequests.render_ignored_count')
    @patch('prs.core.printPullRequests.render_pr_panel')
    @patch('prs.core.printPullRequests.Console')
    @patch('prs.core.printPullRequests.get_ignored_prs')
    @patch('prs.core.printPullRequests.get_pull_request_details')
    @patch('prs.core.printPullRequests.list_pull_request_ids')
    @patch('prs.core.printPullRequests.resolve_display_modes')
    def test_handles_get_pull_request_details_failure(self, mock_resolve_modes, mock_list_ids,
                                                     mock_get_details, mock_get_ignored, mock_console_class,
                                                     mock_render_panel, mock_render_count):
        """Test handling when get_pull_request_details fails for one PR."""
        # Setup mocks
        mock_resolve_modes.return_value = {"include_drafts": False}
        mock_list_ids.return_value = [(123, "authored", False), (456, "team", False)]
        
        # First call succeeds, second fails
        pr1 = MagicMock(spec=PullRequest)
        pr1.id = 123
        mock_get_details.side_effect = [pr1, Exception("API failure")]
        mock_get_ignored.return_value = []
        mock_console = MagicMock(spec=Console)
        mock_console_class.return_value = mock_console
        
        # Should raise the exception (current behavior - no error handling in function)
        options = {}
        with pytest.raises(Exception, match="API failure"):
            list_pull_requests(options)

    @patch('prs.core.printPullRequests.render_ignored_count')
    @patch('prs.core.printPullRequests.render_pr_panel')
    @patch('prs.core.printPullRequests.Console')
    @patch('prs.core.printPullRequests.get_ignored_prs')
    @patch('prs.core.printPullRequests.get_pull_request_details')
    @patch('prs.core.printPullRequests.list_pull_request_ids')
    @patch('prs.core.printPullRequests.resolve_display_modes')
    def test_handles_list_pull_request_ids_failure(self, mock_resolve_modes, mock_list_ids,
                                                  mock_get_details, mock_get_ignored, mock_console_class,
                                                  mock_render_panel, mock_render_count):
        """Test handling when list_pull_request_ids fails."""
        # Setup mocks
        mock_resolve_modes.return_value = {"include_drafts": False}
        mock_list_ids.side_effect = Exception("GitHub API error")
        
        # Should raise the exception (current behavior - no error handling in function)
        options = {}
        with pytest.raises(Exception, match="GitHub API error"):
            list_pull_requests(options)

    @patch('prs.core.printPullRequests.render_ignored_count')
    @patch('prs.core.printPullRequests.render_pr_panel')
    @patch('prs.core.printPullRequests.Console')
    @patch('prs.core.printPullRequests.get_ignored_prs')
    @patch('prs.core.printPullRequests.get_pull_request_details')
    @patch('prs.core.printPullRequests.list_pull_request_ids')
    @patch('prs.core.printPullRequests.resolve_display_modes')
    def test_handles_get_ignored_prs_failure(self, mock_resolve_modes, mock_list_ids,
                                           mock_get_details, mock_get_ignored, mock_console_class,
                                           mock_render_panel, mock_render_count):
        """Test handling when get_ignored_prs fails."""
        # Setup mocks
        mock_resolve_modes.return_value = {"include_drafts": False}
        mock_list_ids.return_value = [(123, "authored", False)]
        
        pr = MagicMock(spec=PullRequest)
        pr.id = 123
        mock_get_details.return_value = pr
        mock_get_ignored.side_effect = Exception("Config read error")
        
        # Should raise the exception (current behavior - no error handling in function)
        options = {}
        with pytest.raises(Exception, match="Config read error"):
            list_pull_requests(options)

    @patch('prs.core.printPullRequests.render_ignored_count')
    @patch('prs.core.printPullRequests.render_pr_panel')
    @patch('prs.core.printPullRequests.Console')
    @patch('prs.core.printPullRequests.get_ignored_prs')
    @patch('prs.core.printPullRequests.get_pull_request_details')
    @patch('prs.core.printPullRequests.list_pull_request_ids')
    @patch('prs.core.printPullRequests.resolve_display_modes')
    def test_handles_render_panel_failure(self, mock_resolve_modes, mock_list_ids,
                                        mock_get_details, mock_get_ignored, mock_console_class,
                                        mock_render_panel, mock_render_count):
        """Test handling when render_pr_panel fails."""
        # Setup mocks
        mock_resolve_modes.return_value = {"include_drafts": False}
        mock_list_ids.return_value = [(123, "authored", False)]
        
        pr = MagicMock(spec=PullRequest)
        pr.id = 123
        mock_get_details.return_value = pr
        mock_get_ignored.return_value = []
        mock_console = MagicMock(spec=Console)
        mock_console_class.return_value = mock_console
        mock_render_panel.side_effect = Exception("Render error")
        
        # Should raise the exception (current behavior - no error handling in function)
        options = {}
        with pytest.raises(Exception, match="Render error"):
            list_pull_requests(options)


class TestListPullRequestsEdgeCases:
    """Test edge cases and unusual scenarios."""

    @patch('prs.core.printPullRequests.render_ignored_count')
    @patch('prs.core.printPullRequests.render_pr_panel')
    @patch('prs.core.printPullRequests.Console')
    @patch('prs.core.printPullRequests.get_ignored_prs')
    @patch('prs.core.printPullRequests.get_pull_request_details')
    @patch('prs.core.printPullRequests.list_pull_request_ids')
    @patch('prs.core.printPullRequests.resolve_display_modes')
    def test_all_prs_ignored(self, mock_resolve_modes, mock_list_ids,
                           mock_get_details, mock_get_ignored, mock_console_class,
                           mock_render_panel, mock_render_count):
        """Test behavior when all PRs are in the ignored list."""
        # Setup mocks
        mock_resolve_modes.return_value = {"include_drafts": False}
        mock_list_ids.return_value = [(123, "authored", False), (456, "team", False)]
        
        pr1 = MagicMock(spec=PullRequest)
        pr1.id = 123
        pr2 = MagicMock(spec=PullRequest)
        pr2.id = 456
        mock_get_details.side_effect = [pr1, pr2]
        mock_get_ignored.return_value = [123, 456]  # All PRs ignored
        mock_console = MagicMock(spec=Console)
        mock_console_class.return_value = mock_console
        
        # Call the function
        options = {}
        list_pull_requests(options)
        
        # Verify no PRs were rendered but ignored count is correct
        mock_render_panel.assert_not_called()
        mock_render_count.assert_called_once_with(2, mock_console)

    @patch('prs.core.printPullRequests.render_ignored_count')
    @patch('prs.core.printPullRequests.render_pr_panel')
    @patch('prs.core.printPullRequests.Console')
    @patch('prs.core.printPullRequests.get_ignored_prs')
    @patch('prs.core.printPullRequests.get_pull_request_details')
    @patch('prs.core.printPullRequests.list_pull_request_ids')
    @patch('prs.core.printPullRequests.resolve_display_modes')
    def test_options_with_missing_keys(self, mock_resolve_modes, mock_list_ids,
                                     mock_get_details, mock_get_ignored, mock_console_class,
                                     mock_render_panel, mock_render_count):
        """Test handling of options dictionary with missing keys."""
        # Setup mocks
        mock_resolve_modes.return_value = {"include_drafts": False}
        mock_list_ids.return_value = []
        mock_get_ignored.return_value = []
        mock_console = MagicMock(spec=Console)
        mock_console_class.return_value = mock_console
        
        # Call with incomplete options dict (should use defaults)
        options = {}  # Missing no_reviewer and no_reviewed
        list_pull_requests(options)
        
        # Verify defaults were used
        mock_list_ids.assert_called_once_with({
            "state": "open",
            "include_draft": False,
            "no_reviewer": False,  # Default from options.get()
            "no_reviewed": False,  # Default from options.get()
        })

    @patch('prs.core.printPullRequests.render_ignored_count')
    @patch('prs.core.printPullRequests.render_pr_panel')
    @patch('prs.core.printPullRequests.Console')
    @patch('prs.core.printPullRequests.get_ignored_prs')
    @patch('prs.core.printPullRequests.get_pull_request_details')
    @patch('prs.core.printPullRequests.list_pull_request_ids')
    @patch('prs.core.printPullRequests.resolve_display_modes')
    def test_pr_without_source_or_is_draft_attributes(self, mock_resolve_modes, mock_list_ids,
                                                    mock_get_details, mock_get_ignored, mock_console_class,
                                                    mock_render_panel, mock_render_count):
        """Test handling of PR objects that don't have source or isDraft attributes initially."""
        # Setup mocks
        mock_resolve_modes.return_value = {"include_drafts": False}
        mock_list_ids.return_value = [(123, "authored", True)]
        
        # Create a minimal mock that doesn't have source or isDraft initially
        pr = MagicMock(spec=PullRequest)
        pr.id = 123
        # Don't pre-set source or isDraft attributes
        
        mock_get_details.return_value = pr
        mock_get_ignored.return_value = []
        mock_console = MagicMock(spec=Console)
        mock_console_class.return_value = mock_console
        
        # Call the function
        options = {}
        list_pull_requests(options)
        
        # Verify attributes were set (should work even if they didn't exist before)
        assert pr.source == "authored"
        assert pr.isDraft is True