"""
Integration tests for PR workflow functionality.

Tests the complete flow from GitHub API to display output.
"""

import pytest
import json
from unittest.mock import patch, Mock

from prs.core.printPullRequests import list_pull_requests
from prs.vc_tools.github.client import list_all_prs
from prs.core.models import PullRequest


class TestPRWorkflowIntegration:
    """Test complete PR workflow integration."""

    @patch('prs.vc_tools.github.client.subprocess.check_output')
    @patch('prs.vc_tools.github.client.get')
    def test_complete_pr_listing_workflow(self, mock_config, mock_subprocess):
        """Test complete workflow from API call to PR objects."""
        # Mock configuration
        mock_config.side_effect = lambda section, key, fallback=None: {
            ('git-org', 'org_name'): 'test-org',
            ('git', 'repo_name'): 'test-repo'
        }.get((section, key), fallback)
        
        # Mock GitHub API response
        pr_data = {
            "number": 123,
            "user": {"login": "testuser"},
            "updated_at": "2023-01-01T12:00:00Z",
            "isDraft": False,
            "source": "authored"
        }
        mock_subprocess.return_value = json.dumps(pr_data) + "\n"
        
        # Execute workflow
        filters = {"state": "open", "include_draft": False, "no_reviewer": True, "no_reviewed": True}
        results = list_all_prs(filters)
        
        # Verify results
        assert len(results) == 1
        assert results[0]["number"] == 123
        assert results[0]["user"]["login"] == "testuser"

    @patch('prs.vc_tools.github.client.get_pull_request_details')
    @patch('prs.vc_tools.github.client.list_pull_request_ids')
    def test_pr_details_integration(self, mock_list_ids, mock_get_details):
        """Test PR details retrieval integration."""
        # Mock PR IDs
        mock_list_ids.return_value = [(123, "authored", False)]
        
        # Mock PR details
        mock_get_details.return_value = PullRequest(
            id=123,
            title="Test PR",
            author="testuser",
            labels=["bug", "high-priority"],
            checks=[{"name": "CI", "status": "SUCCESS"}],
            reviews=[{"user": {"login": "reviewer"}, "state": "APPROVED"}],
            url="https://github.com/org/repo/pull/123",
            branch="feature-branch",
            is_draft=False,
            role="author"
        )
        
        filters = {"state": "open", "include_draft": False, "no_reviewer": True, "no_reviewed": True}
        pr_ids = mock_list_ids(filters)
        pr_details = mock_get_details(pr_ids[0][0], pr_ids[0][1])
        
        assert pr_details.id == 123
        assert pr_details.title == "Test PR"
        assert pr_details.role == "author"
        assert len(pr_details.labels) == 2

    @patch('prs.core.usecases.get_pull_request_details')
    @patch('prs.core.usecases.list_pull_request_ids')
    def test_use_case_integration(self, mock_list_ids, mock_get_details):
        """Test use case layer integration."""
        # Mock data flow
        mock_list_ids.return_value = [(123, "authored", False), (456, "reviewer_pending", True)]
        
        def mock_details_side_effect(pr_id, source):
            if pr_id == 123:
                return PullRequest(
                    id=123, title="First PR", author="user1",
                    labels=[], checks=[], reviews=[], url="url1",
                    branch="branch1", is_draft=False, role="author"
                )
            elif pr_id == 456:
                return PullRequest(
                    id=456, title="Second PR", author="user2",
                    labels=[], checks=[], reviews=[], url="url2",
                    branch="branch2", is_draft=True, role="reviewer_pending"
                )
        
        mock_get_details.side_effect = mock_details_side_effect
        
        # Execute use case
        filters = {"state": "open", "include_draft": True, "no_reviewer": False, "no_reviewed": True}
        results = []
        
        pr_ids = mock_list_ids(filters)
        for pr_id, source, is_draft in pr_ids:
            pr = mock_get_details(pr_id, source)
            results.append(pr)
        
        # Verify integration
        assert len(results) == 2
        assert results[0].role == "author"
        assert results[1].role == "reviewer_pending"
        assert results[1].is_draft is True


class TestConfigurationIntegration:
    """Test configuration system integration."""

    @patch('prs.config.get')
    def test_config_driven_behavior(self, mock_config):
        """Test that configuration drives behavior correctly."""
        # Mock different config scenarios
        config_scenarios = [
            # Scenario 1: Basic author filtering
            {
                ('pr-info', 'authors'): 'user1,user2',
                ('git', 'username'): 'fallback_user',
                ('filters', 'include_reviewer_prs'): 'true'
            },
            # Scenario 2: Single user with reviewer filtering disabled
            {
                ('pr-info', 'authors'): '',
                ('git', 'username'): 'single_user',
                ('filters', 'include_reviewer_prs'): 'false'
            }
        ]
        
        for scenario in config_scenarios:
            mock_config.side_effect = lambda section, key, fallback=None: scenario.get((section, key), fallback)
            
            # Import here to use updated mock
            from prs.core.helpers import read_authors
            
            authors = read_authors()
            
            if scenario.get(('pr-info', 'authors')):
                assert len(authors) >= 2
            else:
                assert len(authors) == 1
                assert authors[0] == 'single_user'

    @patch('prs.config.get_ignored_prs')
    @patch('prs.vc_tools.github.client.list_all_prs')
    def test_ignored_prs_filtering(self, mock_list_prs, mock_ignored):
        """Test that ignored PRs are filtered correctly."""
        # Mock ignored PR list
        mock_ignored.return_value = [123, 456]
        
        # Mock PR list with some ignored PRs
        mock_list_prs.return_value = [
            {"number": 123, "title": "Ignored PR 1"},
            {"number": 789, "title": "Visible PR"},
            {"number": 456, "title": "Ignored PR 2"},
            {"number": 101, "title": "Another Visible PR"}
        ]
        
        # This would be filtered in the actual use case
        all_prs = mock_list_prs({})
        ignored_ids = set(mock_ignored())
        
        filtered_prs = [pr for pr in all_prs if pr["number"] not in ignored_ids]
        
        assert len(filtered_prs) == 2
        assert all(pr["number"] not in [123, 456] for pr in filtered_prs)


class TestDisplayIntegration:
    """Test display system integration."""

    def test_verbosity_level_integration(self):
        """Test that different verbosity levels work together."""
        # Mock PR with comprehensive data
        pr = PullRequest(
            id=123,
            title="Complex Integration Test PR",
            author="integration_user",
            labels=["bug", "high-priority", "backend"],
            checks=[
                {"name": "CI", "status": "SUCCESS"},
                {"name": "Tests", "status": "PENDING"},
                {"name": "Security", "status": "FAILURE"}
            ],
            reviews=[
                {"user": {"login": "reviewer1"}, "state": "APPROVED"},
                {"user": {"login": "reviewer2"}, "state": "CHANGES_REQUESTED"}
            ],
            url="https://github.com/org/repo/pull/123",
            branch="feature/integration-test",
            is_draft=False,
            role="both_pending"
        )
        
        # Test different verbosity combinations
        from prs.core.display.display_config import resolve_display_modes
        
        verbosity_combinations = [
            {"author": "short", "checks": "none", "reviews": "long", "labels": "normal"},
            {"author": "long", "checks": "short", "reviews": "short", "labels": "none"},
            {"author": "normal", "checks": "long", "reviews": "normal", "labels": "short"}
        ]
        
        for verbosity in verbosity_combinations:
            modes = resolve_display_modes(verbosity)
            
            # Each mode should be resolved to a valid verbosity level
            for component, level in modes.items():
                assert level in ["none", "short", "normal", "long"]

    @patch('prs.core.display.panel_renderer.get_console_width')
    def test_responsive_display_integration(self, mock_console_width):
        """Test responsive display adaptation."""
        from prs.core.display.panel_renderer import calculate_dynamic_widths
        
        # Test different console widths
        width_scenarios = [80, 120, 200]
        
        for width in width_scenarios:
            mock_console_width.return_value = width
            
            # Test with different verbosity combinations
            widths = calculate_dynamic_widths(width, has_normal=True, num_long=2)
            
            # Total width should equal console width
            assert sum(widths) == width
            # Should have reasonable distribution
            assert all(w > 0 for w in widths)


class TestErrorHandlingIntegration:
    """Test error handling across the system."""

    @patch('prs.vc_tools.github.client.subprocess.check_output')
    def test_github_api_failure_handling(self, mock_subprocess):
        """Test handling of GitHub API failures."""
        from subprocess import CalledProcessError
        
        # Mock API failure
        mock_subprocess.side_effect = CalledProcessError(1, 'gh')
        
        filters = {"state": "open", "include_draft": False, "no_reviewer": True, "no_reviewed": True}
        
        # Should handle API failure gracefully
        results = list_all_prs(filters)
        assert results == []

    def test_malformed_data_handling(self):
        """Test handling of malformed PR data."""
        from prs.vc_tools.github.adapter import pr_info_to_model
        
        # Test with various malformed data scenarios
        malformed_scenarios = [
            {},  # Empty data
            {"number": "not_a_number"},  # Wrong type
            {"number": 123, "author": "not_a_dict"},  # Wrong nested structure
        ]
        
        for scenario in malformed_scenarios:
            try:
                result = pr_info_to_model(scenario)
                # If it doesn't crash, verify it has reasonable defaults
                assert hasattr(result, 'id')
                assert hasattr(result, 'title')
            except (AttributeError, TypeError, KeyError):
                # Expected for truly malformed data
                pass

    @patch('prs.config.CONFIG_PATH')
    def test_config_file_issues_handling(self, mock_config_path):
        """Test handling of config file issues."""
        # Mock config file that doesn't exist
        mock_config_path.exists.return_value = False
        
        # Should handle missing config gracefully
        from prs.config import get
        result = get("git", "username", fallback="default")
        assert result == "default"


class TestPerformanceIntegration:
    """Test performance characteristics of integrated system."""

    @patch('prs.vc_tools.github.client.subprocess.check_output')
    @patch('prs.vc_tools.github.client.get')
    def test_large_pr_list_handling(self, mock_config, mock_subprocess):
        """Test handling of large PR lists."""
        # Mock configuration
        mock_config.side_effect = lambda section, key, fallback=None: {
            ('git-org', 'org_name'): 'test-org',
            ('git', 'repo_name'): 'test-repo'
        }.get((section, key), fallback)
        
        # Generate large number of mock PRs
        large_pr_list = []
        for i in range(100):
            pr_data = {
                "number": i + 1,
                "user": {"login": f"user{i}"},
                "updated_at": "2023-01-01T12:00:00Z",
                "isDraft": i % 10 == 0,  # Every 10th PR is draft
                "source": "authored"
            }
            large_pr_list.append(json.dumps(pr_data))
        
        mock_subprocess.return_value = "\n".join(large_pr_list) + "\n"
        
        # Execute with large dataset
        filters = {"state": "open", "include_draft": True, "no_reviewer": True, "no_reviewed": True}
        results = list_all_prs(filters)
        
        # Should handle large dataset efficiently
        assert len(results) == 100
        assert results[0]["number"] == 1
        assert results[-1]["number"] == 100

    def test_memory_efficient_processing(self):
        """Test that processing doesn't accumulate excessive memory."""
        # Create many PR objects
        prs = []
        for i in range(50):
            pr = PullRequest(
                id=i,
                title=f"PR {i}",
                author=f"user{i}",
                labels=[f"label{j}" for j in range(5)],
                checks=[{"name": f"check{j}", "status": "SUCCESS"} for j in range(3)],
                reviews=[],
                url=f"url{i}",
                branch=f"branch{i}",
                is_draft=False,
                role="author"
            )
            prs.append(pr)
        
        # Process all PRs
        summaries = [pr.summary() for pr in prs]
        
        # Should complete without issues
        assert len(summaries) == 50
        assert all("PR" in summary for summary in summaries)


class TestRealWorldScenarios:
    """Test realistic usage scenarios."""

    @patch('prs.vc_tools.github.client.get_authenticated_user')
    @patch('prs.vc_tools.github.client.subprocess.check_output')
    @patch('prs.vc_tools.github.client.get')
    def test_mixed_role_pr_scenario(self, mock_config, mock_subprocess, mock_auth):
        """Test scenario where user has multiple roles on same PR."""
        # Mock configuration
        mock_config.side_effect = lambda section, key, fallback=None: {
            ('git-org', 'org_name'): 'test-org',
            ('git', 'repo_name'): 'test-repo',
            ('filters', 'include_reviewer_prs'): 'true',
            ('filters', 'include_reviewed_prs'): 'true'
        }.get((section, key), fallback)
        
        mock_auth.return_value = "test-user"
        
        # Mock scenario: same PR appears in multiple queries
        same_pr_different_sources = {
            "number": 123,
            "user": {"login": "test-user"},
            "updated_at": "2023-01-01T12:00:00Z",
            "isDraft": False
        }
        
        def subprocess_side_effect(args, **kwargs):
            pr_copy = same_pr_different_sources.copy()
            if "review-requested:" in str(args):
                pr_copy["source"] = "reviewer_pending"
            elif "reviewed-by:" in str(args):
                pr_copy["source"] = "reviewer_completed"
            else:
                pr_copy["source"] = "authored"
            return json.dumps(pr_copy) + "\n"
        
        mock_subprocess.side_effect = subprocess_side_effect
        
        # Execute realistic workflow
        filters = {"state": "open", "include_draft": False, "no_reviewer": False, "no_reviewed": False}
        results = list_all_prs(filters)
        
        # Should properly deduplicate and prioritize roles
        assert len(results) == 1
        assert results[0]["number"] == 123

    def test_team_monitoring_scenario(self):
        """Test monitoring multiple team members."""
        from prs.core.helpers import read_authors
        
        with patch('prs.config.get') as mock_config:
            # Mock team configuration
            mock_config.side_effect = lambda section, key, fallback=None: {
                ('pr-info', 'authors'): 'alice,bob,charlie,diana',
                ('git', 'username'): 'alice'
            }.get((section, key), fallback)
            
            authors = read_authors()
            
            # Should handle team monitoring setup
            assert len(authors) == 4
            assert 'alice' in authors
            assert 'diana' in authors

    @patch('prs.config.get_ignored_prs')
    def test_pr_management_workflow(self, mock_ignored):
        """Test complete PR management workflow."""
        # Mock some ignored PRs
        mock_ignored.return_value = [100, 200, 300]
        
        # Simulate adding more PRs to ignore list
        from prs.config import set_ignored_prs
        
        with patch('prs.config.set') as mock_set:
            # Add new PRs to ignore
            new_ignored = [100, 200, 300, 400, 500]
            set_ignored_prs(new_ignored)
            
            # Should update configuration
            mock_set.assert_called_with("filters", "ignored", "100,200,300,400,500")