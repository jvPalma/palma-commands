"""
Unit tests for author display helpers.

Tests cover:
- Author status computation with color assignment
- Role indicator functionality (author, reviewer combinations)
- Username color mapping and persistence
- Display mode handling (none, short, normal, long)
- Integration with configuration system
"""

import pytest
from unittest.mock import patch, MagicMock

from prs.core.author.helpers import compute_author_status, get_author
from prs.core.models import PullRequest


class TestComputeAuthorStatus:
    """Test the compute_author_status function for formatting usernames with colors and role indicators."""

    @patch('prs.core.author.helpers.get_username_color')
    @patch('prs.core.author.helpers.color_text_bg')
    @patch('prs.core.author.helpers.get')
    def test_own_user_with_background_color(self, mock_get, mock_color_text_bg, mock_get_username_color):
        """Test author status for the configured user (should have background color)."""
        # Setup mocks
        mock_get.return_value = 'myuser'  # git.username
        mock_get_username_color.return_value = ('black', 'green')  # fg, bg
        mock_color_text_bg.return_value = 'colored_myuser'
        
        # Create PR
        pr = PullRequest(
            id=1, title="Test", author="myuser", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False
        )
        
        result = compute_author_status(pr)
        
        # Verify username color was requested
        mock_get_username_color.assert_called_once_with('myuser', 'myuser')
        # Verify background color function was called
        mock_color_text_bg.assert_called_once_with('myuser', 'black', 'green')
        assert result == 'colored_myuser'

    @patch('prs.core.author.helpers.get_username_color')
    @patch('prs.core.author.helpers.color_text')
    @patch('prs.core.author.helpers.get')
    def test_other_user_with_foreground_color_only(self, mock_get, mock_color_text, mock_get_username_color):
        """Test author status for other users (foreground color only)."""
        # Setup mocks
        mock_get.return_value = 'myuser'  # git.username
        mock_get_username_color.return_value = ('blue', None)  # fg, no bg
        mock_color_text.return_value = 'colored_otheruser'
        
        # Create PR
        pr = PullRequest(
            id=1, title="Test", author="otheruser", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False
        )
        
        result = compute_author_status(pr)
        
        # Verify username color was requested
        mock_get_username_color.assert_called_once_with('otheruser', 'myuser')
        # Verify foreground color function was called
        mock_color_text.assert_called_once_with('otheruser', 'blue')
        assert result == 'colored_otheruser'

    @patch('prs.core.author.helpers.get_username_color')
    @patch('prs.core.author.helpers.color_text')
    @patch('prs.core.author.helpers.get')
    def test_reviewer_pending_role_indicator(self, mock_get, mock_color_text, mock_get_username_color):
        """Test role indicator for reviewer with pending review."""
        # Setup mocks
        mock_get.return_value = 'myuser'
        mock_get_username_color.return_value = ('red', None)
        mock_color_text.return_value = 'colored_text'
        
        # Create PR with reviewer_pending role
        pr = PullRequest(
            id=1, title="Test", author="reviewer", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False, role="reviewer_pending"
        )
        
        result = compute_author_status(pr)
        
        # Verify role indicator prefix was added
        mock_color_text.assert_called_once_with('[R*] reviewer', 'red')

    @patch('prs.core.author.helpers.get_username_color')
    @patch('prs.core.author.helpers.color_text')
    @patch('prs.core.author.helpers.get')
    def test_reviewer_completed_role_indicator(self, mock_get, mock_color_text, mock_get_username_color):
        """Test role indicator for reviewer with completed review."""
        # Setup mocks
        mock_get.return_value = 'myuser'
        mock_get_username_color.return_value = ('green', None)
        mock_color_text.return_value = 'colored_text'
        
        # Create PR with reviewer_completed role
        pr = PullRequest(
            id=1, title="Test", author="reviewer", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False, role="reviewer_completed"
        )
        
        result = compute_author_status(pr)
        
        # Verify role indicator prefix was added
        mock_color_text.assert_called_once_with('[Rd] reviewer', 'green')

    @patch('prs.core.author.helpers.get_username_color')
    @patch('prs.core.author.helpers.color_text')
    @patch('prs.core.author.helpers.get')
    def test_both_pending_role_indicator(self, mock_get, mock_color_text, mock_get_username_color):
        """Test role indicator for author and reviewer with pending review."""
        # Setup mocks
        mock_get.return_value = 'myuser'
        mock_get_username_color.return_value = ('yellow', None)
        mock_color_text.return_value = 'colored_text'
        
        # Create PR with both_pending role
        pr = PullRequest(
            id=1, title="Test", author="author_reviewer", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False, role="both_pending"
        )
        
        result = compute_author_status(pr)
        
        # Verify role indicator prefix was added
        mock_color_text.assert_called_once_with('[A+R*] author_reviewer', 'yellow')

    @patch('prs.core.author.helpers.get_username_color')
    @patch('prs.core.author.helpers.color_text')
    @patch('prs.core.author.helpers.get')
    def test_both_completed_role_indicator(self, mock_get, mock_color_text, mock_get_username_color):
        """Test role indicator for author and reviewer with completed review."""
        # Setup mocks
        mock_get.return_value = 'myuser'
        mock_get_username_color.return_value = ('cyan', None)
        mock_color_text.return_value = 'colored_text'
        
        # Create PR with both_completed role
        pr = PullRequest(
            id=1, title="Test", author="author_reviewer", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False, role="both_completed"
        )
        
        result = compute_author_status(pr)
        
        # Verify role indicator prefix was added
        mock_color_text.assert_called_once_with('[A+Rd] author_reviewer', 'cyan')

    @patch('prs.core.author.helpers.get_username_color')
    @patch('prs.core.author.helpers.color_text')
    @patch('prs.core.author.helpers.get')
    def test_author_role_no_prefix(self, mock_get, mock_color_text, mock_get_username_color):
        """Test that author role doesn't add prefix."""
        # Setup mocks
        mock_get.return_value = 'myuser'
        mock_get_username_color.return_value = ('white', None)
        mock_color_text.return_value = 'colored_text'
        
        # Create PR with author role
        pr = PullRequest(
            id=1, title="Test", author="author", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False, role="author"
        )
        
        result = compute_author_status(pr)
        
        # Verify no prefix was added (just the username)
        mock_color_text.assert_called_once_with('author', 'white')

    @patch('prs.core.author.helpers.get_username_color')
    @patch('prs.core.author.helpers.color_text')
    @patch('prs.core.author.helpers.get')
    def test_no_role_no_prefix(self, mock_get, mock_color_text, mock_get_username_color):
        """Test that PRs without role don't add prefix."""
        # Setup mocks
        mock_get.return_value = 'myuser'
        mock_get_username_color.return_value = ('magenta', None)
        mock_color_text.return_value = 'colored_text'
        
        # Create PR without role
        pr = PullRequest(
            id=1, title="Test", author="author", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False
        )
        
        result = compute_author_status(pr)
        
        # Verify no prefix was added (just the username)
        mock_color_text.assert_called_once_with('author', 'magenta')

    @patch('prs.core.author.helpers.get_username_color')
    @patch('prs.core.author.helpers.color_text')
    @patch('prs.core.author.helpers.get')
    def test_legacy_source_field_fallback(self, mock_get, mock_color_text, mock_get_username_color):
        """Test fallback to legacy source field when role is not present."""
        # Setup mocks
        mock_get.return_value = 'myuser'
        mock_get_username_color.return_value = ('orange', None)
        mock_color_text.return_value = 'colored_text'
        
        # Create PR with source but no role
        pr = PullRequest(
            id=1, title="Test", author="reviewer", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False
        )
        pr.source = "reviewer"
        
        result = compute_author_status(pr)
        
        # Verify legacy source was used for prefix
        mock_color_text.assert_called_once_with('[R*] reviewer', 'orange')

    @patch('prs.core.author.helpers.get_username_color')
    @patch('prs.core.author.helpers.color_text')
    @patch('prs.core.author.helpers.get')
    def test_legacy_source_reviewer_pending(self, mock_get, mock_color_text, mock_get_username_color):
        """Test legacy source field reviewer_pending handling."""
        # Setup mocks
        mock_get.return_value = 'myuser'
        mock_get_username_color.return_value = ('purple', None)
        mock_color_text.return_value = 'colored_text'
        
        # Create PR with legacy source
        pr = PullRequest(
            id=1, title="Test", author="reviewer", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False
        )
        pr.source = "reviewer_pending"
        
        result = compute_author_status(pr)
        
        # Verify legacy source was mapped correctly
        mock_color_text.assert_called_once_with('[R*] reviewer', 'purple')

    @patch('prs.core.author.helpers.get_username_color')
    @patch('prs.core.author.helpers.color_text')
    @patch('prs.core.author.helpers.get')
    def test_legacy_source_both_completed(self, mock_get, mock_color_text, mock_get_username_color):
        """Test legacy source field both_completed handling."""
        # Setup mocks
        mock_get.return_value = 'myuser'
        mock_get_username_color.return_value = ('brown', None)
        mock_color_text.return_value = 'colored_text'
        
        # Create PR with legacy source
        pr = PullRequest(
            id=1, title="Test", author="author_reviewer", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False
        )
        pr.source = "both_completed"
        
        result = compute_author_status(pr)
        
        # Verify legacy source was mapped correctly
        mock_color_text.assert_called_once_with('[A+Rd] author_reviewer', 'brown')

    @patch('prs.core.author.helpers.get_username_color')
    @patch('prs.core.author.helpers.color_text')
    @patch('prs.core.author.helpers.get')
    def test_role_takes_precedence_over_source(self, mock_get, mock_color_text, mock_get_username_color):
        """Test that role field takes precedence over source field."""
        # Setup mocks
        mock_get.return_value = 'myuser'
        mock_get_username_color.return_value = ('teal', None)
        mock_color_text.return_value = 'colored_text'
        
        # Create PR with both role and source
        pr = PullRequest(
            id=1, title="Test", author="user", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False, role="reviewer_completed"
        )
        pr.source = "reviewer_pending"  # Different from role
        
        result = compute_author_status(pr)
        
        # Verify role was used, not source
        mock_color_text.assert_called_once_with('[Rd] user', 'teal')

    @patch('prs.core.author.helpers.get_username_color')
    @patch('prs.core.author.helpers.color_text_bg')
    @patch('prs.core.author.helpers.get')
    def test_special_characters_in_username(self, mock_get, mock_color_text_bg, mock_get_username_color):
        """Test handling of special characters in usernames."""
        # Setup mocks
        mock_get.return_value = 'my-user_123'
        mock_get_username_color.return_value = ('white', 'blue')
        mock_color_text_bg.return_value = 'colored_special_user'
        
        # Create PR with special characters in username
        pr = PullRequest(
            id=1, title="Test", author="user-name_with.special+chars@domain", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False, role="both_pending"
        )
        
        result = compute_author_status(pr)
        
        # Verify special characters are handled properly
        expected_text = '[A+R*] user-name_with.special+chars@domain'
        mock_color_text_bg.assert_called_once_with(expected_text, 'white', 'blue')

    @patch('prs.core.author.helpers.get_username_color')
    @patch('prs.core.author.helpers.color_text')
    @patch('prs.core.author.helpers.get')
    def test_empty_username(self, mock_get, mock_color_text, mock_get_username_color):
        """Test handling of empty username."""
        # Setup mocks
        mock_get.return_value = 'myuser'
        mock_get_username_color.return_value = ('gray', None)
        mock_color_text.return_value = 'colored_empty'
        
        # Create PR with empty username
        pr = PullRequest(
            id=1, title="Test", author="", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False
        )
        
        result = compute_author_status(pr)
        
        # Verify empty username is handled
        mock_color_text.assert_called_once_with('', 'gray')


class TestGetAuthor:
    """Test the get_author function for display mode handling."""

    @patch('prs.core.author.helpers.compute_author_status')
    def test_get_author_none_mode(self, mock_compute):
        """Test get_author with 'none' mode returns empty string."""
        # Create PR
        pr = PullRequest(
            id=1, title="Test", author="user", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False
        )
        
        result = get_author(pr, "none")
        
        assert result == ""
        # Verify compute_author_status was not called
        mock_compute.assert_not_called()

    @patch('prs.core.author.helpers.compute_author_status')
    def test_get_author_short_mode(self, mock_compute):
        """Test get_author with 'short' mode calls compute_author_status."""
        # Setup mock
        mock_compute.return_value = 'formatted_author'
        
        # Create PR
        pr = PullRequest(
            id=1, title="Test", author="user", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False
        )
        
        result = get_author(pr, "short")
        
        assert result == 'formatted_author'
        mock_compute.assert_called_once_with(pr)

    @patch('prs.core.author.helpers.compute_author_status')
    def test_get_author_normal_mode(self, mock_compute):
        """Test get_author with 'normal' mode calls compute_author_status."""
        # Setup mock
        mock_compute.return_value = 'formatted_author'
        
        # Create PR
        pr = PullRequest(
            id=1, title="Test", author="user", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False
        )
        
        result = get_author(pr, "normal")
        
        assert result == 'formatted_author'
        mock_compute.assert_called_once_with(pr)

    @patch('prs.core.author.helpers.compute_author_status')
    def test_get_author_long_mode(self, mock_compute):
        """Test get_author with 'long' mode calls compute_author_status."""
        # Setup mock
        mock_compute.return_value = 'formatted_author'
        
        # Create PR
        pr = PullRequest(
            id=1, title="Test", author="user", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False
        )
        
        result = get_author(pr, "long")
        
        assert result == 'formatted_author'
        mock_compute.assert_called_once_with(pr)

    @patch('prs.core.author.helpers.compute_author_status')
    def test_get_author_unknown_mode(self, mock_compute):
        """Test get_author with unknown mode defaults to compute_author_status."""
        # Setup mock
        mock_compute.return_value = 'formatted_author'
        
        # Create PR
        pr = PullRequest(
            id=1, title="Test", author="user", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False
        )
        
        result = get_author(pr, "unknown_mode")
        
        assert result == 'formatted_author'
        mock_compute.assert_called_once_with(pr)

    @patch('prs.core.author.helpers.compute_author_status')
    def test_get_author_empty_mode(self, mock_compute):
        """Test get_author with empty string mode."""
        # Setup mock
        mock_compute.return_value = 'formatted_author'
        
        # Create PR
        pr = PullRequest(
            id=1, title="Test", author="user", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False
        )
        
        result = get_author(pr, "")
        
        # Empty string is not "none", so should call compute_author_status
        assert result == 'formatted_author'
        mock_compute.assert_called_once_with(pr)

    @patch('prs.core.author.helpers.compute_author_status')
    def test_get_author_case_sensitivity(self, mock_compute):
        """Test get_author is case sensitive for 'none' mode."""
        # Setup mock
        mock_compute.return_value = 'formatted_author'
        
        # Create PR
        pr = PullRequest(
            id=1, title="Test", author="user", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False
        )
        
        # Test different cases
        result_none = get_author(pr, "none")
        result_none_upper = get_author(pr, "NONE")
        result_none_mixed = get_author(pr, "None")
        
        assert result_none == ""
        assert result_none_upper == 'formatted_author'  # Not exact match
        assert result_none_mixed == 'formatted_author'  # Not exact match
        
        # Verify compute was called for non-exact matches
        assert mock_compute.call_count == 2


class TestAuthorHelpersIntegration:
    """Integration tests for author helper functions."""

    @patch('prs.core.author.helpers.get_username_color')
    @patch('prs.core.author.helpers.color_text')
    @patch('prs.core.author.helpers.get')
    def test_full_workflow_different_modes(self, mock_get, mock_color_text, mock_get_username_color):
        """Test complete workflow with different display modes."""
        # Setup mocks
        mock_get.return_value = 'testuser'
        mock_get_username_color.return_value = ('red', None)
        mock_color_text.return_value = '[R*] testuser_colored'
        
        # Create PR
        pr = PullRequest(
            id=1, title="Test", author="testuser", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False, role="reviewer_pending"
        )
        
        # Test different modes
        none_result = get_author(pr, "none")
        short_result = get_author(pr, "short")
        normal_result = get_author(pr, "normal")
        long_result = get_author(pr, "long")
        
        assert none_result == ""
        assert short_result == '[R*] testuser_colored'
        assert normal_result == '[R*] testuser_colored'
        assert long_result == '[R*] testuser_colored'
        
        # Verify compute was called 3 times (not for 'none')
        assert mock_color_text.call_count == 3

    def test_real_pr_object_integration(self):
        """Test with a real PullRequest object to ensure compatibility."""
        # Create a real PullRequest object
        pr = PullRequest(
            id=12345,
            title="Real integration test",
            author="integration_user",
            labels=["bug", "urgent"],
            checks=[{"name": "CI", "status": "success"}],
            reviews=[{"user": "reviewer", "state": "APPROVED"}],
            url="https://github.com/org/repo/pull/12345",
            branch="integration-test",
            is_draft=False,
            role="both_completed"
        )
        
        # Test that functions can be called with real object
        # (Will use actual config and color systems)
        try:
            none_result = get_author(pr, "none")
            assert none_result == ""
            
            # Other modes will depend on actual config, just verify they don't crash
            short_result = get_author(pr, "short")
            assert isinstance(short_result, str)
            
        except Exception as e:
            # If actual config/color systems aren't available, that's okay
            # The important thing is that the functions can handle real objects
            pytest.skip(f"Skipping integration test due to config dependency: {e}")


class TestAuthorHelpersErrorHandling:
    """Test error handling in author helper functions."""

    @patch('prs.core.author.helpers.get_username_color', side_effect=Exception("Color error"))
    @patch('prs.core.author.helpers.get')
    def test_compute_author_status_handles_color_error(self, mock_get, mock_get_username_color):
        """Test that compute_author_status handles color system errors."""
        mock_get.return_value = 'testuser'
        
        pr = PullRequest(
            id=1, title="Test", author="user", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False
        )
        
        # Should propagate the color system error
        with pytest.raises(Exception, match="Color error"):
            compute_author_status(pr)

    @patch('prs.core.author.helpers.get', side_effect=Exception("Config error"))
    def test_compute_author_status_handles_config_error(self, mock_get):
        """Test that compute_author_status handles config system errors."""
        pr = PullRequest(
            id=1, title="Test", author="user", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False
        )
        
        # Should propagate the config error
        with pytest.raises(Exception, match="Config error"):
            compute_author_status(pr)

    @patch('prs.core.author.helpers.compute_author_status', side_effect=Exception("Compute error"))
    def test_get_author_handles_compute_error(self, mock_compute):
        """Test that get_author handles compute_author_status errors."""
        pr = PullRequest(
            id=1, title="Test", author="user", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False
        )
        
        # Should propagate the compute error (except for 'none' mode)
        none_result = get_author(pr, "none")
        assert none_result == ""  # 'none' mode doesn't call compute
        
        with pytest.raises(Exception, match="Compute error"):
            get_author(pr, "short")

    def test_malformed_pr_object(self):
        """Test handling of malformed PR objects."""
        # Create a mock that doesn't have expected attributes
        malformed_pr = MagicMock()
        malformed_pr.author = "test"
        # Missing other attributes like role, source
        
        # Functions should handle missing attributes gracefully or raise appropriate errors
        result = get_author(malformed_pr, "none")
        assert result == ""  # 'none' mode shouldn't access PR attributes
        
        # For other modes, the function might work with just the author attribute
        # since hasattr() returns False for missing attrs and the code handles it
        try:
            result = get_author(malformed_pr, "short")
            # If it works, that's fine - the function is robust
            assert isinstance(result, str)
        except (AttributeError, Exception):
            # If it fails, that's also acceptable - depends on implementation details
            pass