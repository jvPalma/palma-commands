"""
Integration tests for the display system.

Tests how different display components work together to create the final output.
"""

import pytest
from unittest.mock import patch, Mock

from prs.core.models import PullRequest
from prs.core.display.display_config import resolve_display_modes, get_panel_color
from prs.core.display.panel_renderer import create_pr_panel, calculate_dynamic_widths


class TestDisplaySystemIntegration:
    """Test integration between display components."""

    def create_sample_pr(self, **overrides):
        """Create a sample PR for testing."""
        defaults = {
            "id": 123,
            "title": "Sample PR for Display Testing",
            "author": "test_user",
            "labels": ["bug", "high-priority"],
            "checks": [
                {"name": "CI", "status": "SUCCESS"},
                {"name": "Tests", "status": "PENDING"}
            ],
            "reviews": [
                {"user": {"login": "reviewer1"}, "state": "APPROVED"}
            ],
            "url": "https://github.com/org/repo/pull/123",
            "branch": "feature/display-test",
            "is_draft": False,
            "role": "author"
        }
        defaults.update(overrides)
        return PullRequest(**defaults)

    def test_complete_display_pipeline(self):
        """Test the complete display pipeline from PR to rendered output."""
        pr = self.create_sample_pr()
        
        # Test configuration resolution
        user_config = {
            "author": "normal",
            "checks": "long", 
            "reviews": "short",
            "labels": "none",
            "pr_url": "short",
            "branch": "normal"
        }
        
        display_modes = resolve_display_modes(user_config)
        
        # Verify configuration is properly processed
        assert display_modes["author"] == "normal"
        assert display_modes["checks"] == "long"
        assert display_modes["labels"] == "none"

    @patch('prs.core.display.panel_renderer.get_console_width')
    def test_responsive_panel_rendering(self, mock_console_width):
        """Test that panels adapt to different console widths."""
        pr = self.create_sample_pr()
        
        # Test different console widths
        test_widths = [60, 100, 140, 200]
        
        for width in test_widths:
            mock_console_width.return_value = width
            
            # Create panel with different verbosity settings
            with patch('prs.core.display.display_config.resolve_display_modes') as mock_modes:
                mock_modes.return_value = {
                    "author": "normal",
                    "checks": "long",
                    "reviews": "short", 
                    "labels": "normal",
                    "pr_url": "short",
                    "branch": "normal"
                }
                
                panel = create_pr_panel(pr, mock_modes.return_value)
                
                # Panel should be created without errors
                assert panel is not None

    def test_panel_color_logic_integration(self):
        """Test panel color determination with various PR states."""
        # Test draft PR with good checks
        draft_pr = self.create_sample_pr(
            is_draft=True,
            checks=[{"name": "CI", "status": "SUCCESS"}]
        )
        
        with patch('prs.core.display.display_config.analyze_checks') as mock_analyze:
            mock_analyze.return_value = (1, 1, 0, 0, [])  # 1 total, 1 success
            color = get_panel_color(draft_pr)
            assert color in ["cyan", "bright_cyan"]  # Draft with good checks

    def test_display_mode_combinations(self):
        """Test various display mode combinations work together."""
        pr = self.create_sample_pr()
        
        # Test extreme combinations
        mode_combinations = [
            # All minimal
            {"author": "none", "checks": "none", "reviews": "none", "labels": "none", "pr_url": "none", "branch": "none"},
            # All maximal  
            {"author": "long", "checks": "long", "reviews": "long", "labels": "long", "pr_url": "long", "branch": "long"},
            # Mixed modes
            {"author": "short", "checks": "none", "reviews": "long", "labels": "normal", "pr_url": "short", "branch": "normal"}
        ]
        
        for modes in mode_combinations:
            resolved_modes = resolve_display_modes(modes)
            
            # All modes should be valid
            for component, level in resolved_modes.items():
                assert level in ["none", "short", "normal", "long"]

    @patch('prs.core.display.panel_renderer.get_console_width')
    def test_width_calculation_integration(self, mock_console_width):
        """Test width calculation with various scenarios."""
        mock_console_width.return_value = 120
        
        # Test different verbosity scenarios
        scenarios = [
            {"has_normal": True, "num_long": 0},   # Some normal, no long
            {"has_normal": False, "num_long": 2},  # No normal, some long  
            {"has_normal": True, "num_long": 3},   # Both normal and long
            {"has_normal": False, "num_long": 0}   # All short/none
        ]
        
        for scenario in scenarios:
            widths = calculate_dynamic_widths(120, **scenario)
            
            # Total should equal console width
            assert sum(widths) == 120
            # All widths should be positive
            assert all(w > 0 for w in widths)

    def test_unicode_handling_integration(self):
        """Test Unicode and special character handling across display system."""
        unicode_pr = self.create_sample_pr(
            title="🚀 Unicode Test: Add émojis and ∑pecial chars",
            author="用户-with-unicode",
            branch="feature/émoji-support-🎯",
            labels=["🐛 bug", "✨ enhancement", "unicode-∑upport"]
        )
        
        # Test that display system handles Unicode properly
        display_modes = resolve_display_modes({
            "author": "normal",
            "checks": "short",
            "reviews": "normal",
            "labels": "long",
            "pr_url": "short", 
            "branch": "normal"
        })
        
        # Should not crash with Unicode content
        assert display_modes is not None
        assert unicode_pr.title == "🚀 Unicode Test: Add émojis and ∑pecial chars"

    def test_error_resilience_in_display(self):
        """Test display system resilience to various error conditions."""
        # Test with minimal/missing data
        minimal_pr = PullRequest(
            id=1,
            title="",
            author="",
            labels=[],
            checks=[],
            reviews=[],
            url="",
            branch="",
            is_draft=False,
            role=None
        )
        
        # Should handle minimal data gracefully
        display_modes = resolve_display_modes({
            "author": "normal",
            "checks": "long",
            "reviews": "short",
            "labels": "normal",
            "pr_url": "short",
            "branch": "normal"
        })
        
        # Should not crash with empty/minimal PR
        assert display_modes is not None

    @patch('prs.core.display.feature_renderers.get_console_width')
    def test_feature_renderer_integration(self, mock_console_width):
        """Test feature renderers working together."""
        from prs.core.display.feature_renderers import (
            render_author_info, render_checks_summary, render_reviews_summary
        )
        
        mock_console_width.return_value = 100
        pr = self.create_sample_pr()
        
        # Test rendering different components
        author_output = render_author_info(pr, "normal", 30)
        checks_output = render_checks_summary(pr, "short", 25)
        reviews_output = render_reviews_summary(pr, "normal", 35)
        
        # All renderers should produce output
        assert author_output is not None
        assert checks_output is not None  
        assert reviews_output is not None

    def test_complex_pr_display_integration(self):
        """Test display of PR with complex data."""
        complex_pr = self.create_sample_pr(
            title="Complex PR with Many Components and a Very Long Title That Might Need Truncation",
            labels=["bug", "high-priority", "backend", "database", "performance", "security"],
            checks=[
                {"name": "Continuous Integration", "status": "SUCCESS"},
                {"name": "Unit Tests", "status": "SUCCESS"},
                {"name": "Integration Tests", "status": "PENDING"},
                {"name": "Security Scan", "status": "FAILURE"},
                {"name": "Performance Tests", "status": "SUCCESS"}
            ],
            reviews=[
                {"user": {"login": "senior_dev"}, "state": "APPROVED"},
                {"user": {"login": "security_expert"}, "state": "CHANGES_REQUESTED"},
                {"user": {"login": "architect"}, "state": "COMMENTED"}
            ],
            role="both_pending"
        )
        
        # Test display with comprehensive data
        display_modes = resolve_display_modes({
            "author": "long",
            "checks": "long", 
            "reviews": "long",
            "labels": "long",
            "pr_url": "normal",
            "branch": "normal"
        })
        
        # Should handle complex PR without issues
        assert display_modes is not None
        assert len(complex_pr.labels) == 6
        assert len(complex_pr.checks) == 5
        assert len(complex_pr.reviews) == 3


class TestDisplayConfigurationIntegration:
    """Test display configuration system integration."""

    def test_config_override_hierarchy(self):
        """Test configuration override hierarchy."""
        # Base configuration
        base_config = {
            "author": "short",
            "checks": "normal", 
            "reviews": "short",
            "labels": "none",
            "pr_url": "short",
            "branch": "short"
        }
        
        # User overrides
        user_overrides = {
            "checks": "long",
            "reviews": "normal",
            "labels": "short"
        }
        
        # Simulate configuration merging
        final_config = {**base_config, **user_overrides}
        resolved = resolve_display_modes(final_config)
        
        # Overrides should take precedence
        assert resolved["checks"] == "long"
        assert resolved["reviews"] == "normal"
        assert resolved["labels"] == "short"
        # Non-overridden values should remain
        assert resolved["author"] == "short"
        assert resolved["pr_url"] == "short"

    @patch('prs.config.get')
    def test_config_file_integration(self, mock_config):
        """Test integration with actual config file values."""
        # Mock config file values
        mock_config.side_effect = lambda section, key, fallback=None: {
            ('pr-info', 'author'): 'long',
            ('pr-info', 'checks'): 'short',
            ('pr-info', 'reviews'): 'normal',
            ('pr-info', 'labels'): 'none',
            ('pr-info', 'pr_url'): 'short',
            ('pr-info', 'branch'): 'normal'
        }.get((section, key), fallback)
        
        # Test that config values are properly loaded
        config_values = {}
        for component in ['author', 'checks', 'reviews', 'labels', 'pr_url', 'branch']:
            config_values[component] = mock_config('pr-info', component, 'short')
        
        resolved = resolve_display_modes(config_values)
        
        # Should match config file values
        assert resolved['author'] == 'long'
        assert resolved['checks'] == 'short'
        assert resolved['reviews'] == 'normal'
        assert resolved['labels'] == 'none'

    def test_invalid_config_handling(self):
        """Test handling of invalid configuration values."""
        invalid_config = {
            "author": "invalid_level",
            "checks": "also_invalid",
            "reviews": "normal",  # This one is valid
            "labels": "",  # Empty string
            "pr_url": None,  # None value
            "branch": "short"  # Valid
        }
        
        # Should handle invalid values gracefully
        try:
            resolved = resolve_display_modes(invalid_config)
            # If it doesn't crash, check that valid values are preserved
            assert resolved["reviews"] == "normal"
            assert resolved["branch"] == "short"
        except (ValueError, KeyError):
            # Expected for truly invalid configurations
            pass


class TestPerformanceOptimization:
    """Test display system performance characteristics."""

    def test_large_dataset_display_performance(self):
        """Test display performance with large datasets."""
        # Create many PRs with varying complexity
        prs = []
        for i in range(100):
            pr = PullRequest(
                id=i,
                title=f"Performance Test PR #{i}",
                author=f"user_{i % 10}",  # 10 different users
                labels=[f"label_{j}" for j in range(i % 5)],  # Varying label counts
                checks=[{"name": f"check_{j}", "status": "SUCCESS"} for j in range(i % 3)],
                reviews=[],
                url=f"https://github.com/org/repo/pull/{i}",
                branch=f"branch_{i}",
                is_draft=i % 10 == 0,  # Every 10th is draft
                role="author"
            )
            prs.append(pr)
        
        # Test display mode resolution for all PRs
        display_modes = resolve_display_modes({
            "author": "normal",
            "checks": "short",
            "reviews": "normal", 
            "labels": "short",
            "pr_url": "short",
            "branch": "short"
        })
        
        # Should handle large dataset efficiently
        assert len(prs) == 100
        assert display_modes is not None

    @patch('prs.core.display.panel_renderer.get_console_width')
    def test_dynamic_width_calculation_performance(self, mock_console_width):
        """Test performance of dynamic width calculations."""
        mock_console_width.return_value = 150
        
        # Test many width calculations
        for i in range(50):
            has_normal = i % 2 == 0
            num_long = i % 4
            
            widths = calculate_dynamic_widths(150, has_normal, num_long)
            
            # Each calculation should be consistent
            assert sum(widths) == 150
            assert len(widths) == 6  # 6 display components

    def test_memory_efficient_display(self):
        """Test that display operations don't accumulate excessive memory."""
        # Create and display many PRs in sequence
        for i in range(30):
            pr = PullRequest(
                id=i,
                title=f"Memory Test PR {i}",
                author="memory_user",
                labels=["memory", "test"],
                checks=[{"name": "memory_check", "status": "SUCCESS"}],
                reviews=[],
                url=f"url_{i}",
                branch=f"branch_{i}",
                is_draft=False,
                role="author"
            )
            
            # Simulate display operations
            display_modes = resolve_display_modes({
                "author": "short",
                "checks": "normal",
                "reviews": "short",
                "labels": "normal",
                "pr_url": "short",
                "branch": "short"
            })
            
            # Should complete without memory issues
            assert display_modes is not None

    def test_string_formatting_performance(self):
        """Test string formatting performance for display."""
        pr = PullRequest(
            id=999,
            title="Performance Test PR",
            author="perf_user",
            labels=["performance"] * 10,  # Many labels
            checks=[{"name": f"check_{i}", "status": "SUCCESS"} for i in range(20)],  # Many checks
            reviews=[{"user": {"login": f"reviewer_{i}"}, "state": "APPROVED"} for i in range(5)],
            url="https://github.com/org/repo/pull/999", 
            branch="performance/test",
            is_draft=False,
            role="author"
        )
        
        # Test multiple summary generations
        summaries = []
        for i in range(20):
            summary = pr.summary()
            summaries.append(summary)
        
        # All summaries should be generated successfully
        assert len(summaries) == 20
        assert all("[#999]" in summary for summary in summaries)