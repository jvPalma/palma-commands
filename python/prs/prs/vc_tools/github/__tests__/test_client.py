"""
Unit tests for GitHub client module.

Tests GitHub API integration, PR fetching, and reviewer PR functionality.
"""

import pytest
import json
import subprocess
from unittest.mock import Mock, patch, call
from prs.vc_tools.github.client import (
    get_authenticated_user,
    list_all_prs,
    list_pull_request_ids,
    get_pull_request_details
)


class TestGetAuthenticatedUser:
    """Tests for authenticated user retrieval."""

    @patch('prs.vc_tools.github.client.subprocess.check_output')
    def test_get_authenticated_user_success(self, mock_subprocess):
        """Successfully retrieve authenticated user."""
        mock_subprocess.return_value = "test-user\n"
        
        result = get_authenticated_user()
        
        assert result == "test-user"
        mock_subprocess.assert_called_once_with(
            ["gh", "api", "user", "--jq", ".login"], 
            text=True
        )

    @patch('prs.vc_tools.github.client.subprocess.check_output')
    def test_get_authenticated_user_with_whitespace(self, mock_subprocess):
        """Handle whitespace in user response."""
        mock_subprocess.return_value = "  test-user  \n"
        
        result = get_authenticated_user()
        
        assert result == "test-user"

    @patch('prs.vc_tools.github.client.subprocess.check_output')
    def test_get_authenticated_user_subprocess_error(self, mock_subprocess):
        """Handle subprocess error gracefully."""
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, 'gh')
        
        result = get_authenticated_user()
        
        assert result == ""

    @patch('prs.vc_tools.github.client.subprocess.check_output')
    def test_get_authenticated_user_empty_response(self, mock_subprocess):
        """Handle empty response."""
        mock_subprocess.return_value = "\n"
        
        result = get_authenticated_user()
        
        assert result == ""


class TestListAllPrs:
    """Tests for PR listing functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.sample_pr_data = {
            "number": 123,
            "user": {"login": "test-user"},
            "updated_at": "2023-01-01T12:00:00Z",
            "isDraft": False,
            "source": "authored"
        }

    @patch('prs.vc_tools.github.client.get_authenticated_user')
    @patch('prs.vc_tools.github.client.subprocess.check_output')
    @patch('prs.vc_tools.github.client.get')
    def test_list_all_prs_basic_functionality(self, mock_config, mock_subprocess, mock_auth_user):
        """Basic PR listing with single author."""
        mock_config.side_effect = lambda section, key, fallback=None: {
            ('git-org', 'org_name'): 'test-org',
            ('git', 'repo_name'): 'test-repo'
        }.get((section, key), fallback)
        
        mock_auth_user.return_value = "auth-user"
        mock_subprocess.return_value = json.dumps(self.sample_pr_data) + "\n"
        
        result = list_all_prs(["test-user"], "open", False, False, False, False)
        
        assert len(result) == 1
        assert result[0]["number"] == 123
        assert result[0]["source"] == "authored"

    @patch('prs.vc_tools.github.client.get_authenticated_user')
    @patch('prs.vc_tools.github.client.subprocess.check_output')
    @patch('prs.vc_tools.github.client.get')
    def test_list_all_prs_multiple_authors(self, mock_config, mock_subprocess, mock_auth_user):
        """PR listing with multiple authors."""
        mock_config.side_effect = lambda section, key, fallback=None: {
            ('git-org', 'org_name'): 'test-org',
            ('git', 'repo_name'): 'test-repo'
        }.get((section, key), fallback)
        
        mock_auth_user.return_value = "auth-user"
        
        # Return different PR for each author
        def subprocess_side_effect(args, **kwargs):
            if "author:user1" in args:
                return json.dumps({**self.sample_pr_data, "number": 1}) + "\n"
            elif "author:user2" in args:
                return json.dumps({**self.sample_pr_data, "number": 2}) + "\n"
            return ""
        
        mock_subprocess.side_effect = subprocess_side_effect
        
        result = list_all_prs(["user1", "user2"], "open", False, False, False, False)
        
        assert len(result) == 2
        numbers = [pr["number"] for pr in result]
        assert 1 in numbers and 2 in numbers

    @patch('prs.vc_tools.github.client.get_authenticated_user')
    @patch('prs.vc_tools.github.client.subprocess.check_output')
    @patch('prs.vc_tools.github.client.get')
    def test_list_all_prs_with_drafts_included(self, mock_config, mock_subprocess, mock_auth_user):
        """PR listing with drafts included."""
        mock_config.side_effect = lambda section, key, fallback=None: {
            ('git-org', 'org_name'): 'test-org',
            ('git', 'repo_name'): 'test-repo'
        }.get((section, key), fallback)
        
        mock_auth_user.return_value = "auth-user"
        mock_subprocess.return_value = json.dumps(self.sample_pr_data) + "\n"
        
        result = list_all_prs(["test-user"], "open", True, False, False, False)
        
        # Should call with both draft and non-draft queries
        assert mock_subprocess.call_count >= 2  # At least authored + drafts

    @patch('prs.vc_tools.github.client.get_authenticated_user')
    @patch('prs.vc_tools.github.client.subprocess.check_output')
    @patch('prs.vc_tools.github.client.get')
    def test_list_all_prs_reviewer_functionality(self, mock_config, mock_subprocess, mock_auth_user):
        """Test reviewer PR functionality with pending and completed reviews."""
        mock_config.side_effect = lambda section, key, fallback=None: {
            ('git-org', 'org_name'): 'test-org',
            ('git', 'repo_name'): 'test-repo',
            ('filters', 'include_reviewer_prs'): 'true',
            ('filters', 'include_reviewed_prs'): 'true'
        }.get((section, key), fallback)
        
        mock_auth_user.return_value = "auth-user"
        
        def subprocess_side_effect(args, **kwargs):
            if "review-requested:" in args:
                return json.dumps({**self.sample_pr_data, "number": 100, "source": "reviewer"}) + "\n"
            elif "reviewed-by:" in args:
                return json.dumps({**self.sample_pr_data, "number": 200, "source": "reviewed"}) + "\n"
            elif "author:" in args:
                return json.dumps({**self.sample_pr_data, "number": 300, "source": "authored"}) + "\n"
            return ""
        
        mock_subprocess.side_effect = subprocess_side_effect
        
        result = list_all_prs(["test-user"], "open", False, False, False, False)
        
        # Should have PRs from all sources: authored, reviewer, reviewed
        numbers = [pr["number"] for pr in result]
        assert 100 in numbers  # review-requested
        assert 200 in numbers  # reviewed-by
        assert 300 in numbers  # authored

    @patch('prs.vc_tools.github.client.get_authenticated_user')
    @patch('prs.vc_tools.github.client.subprocess.check_output')
    @patch('prs.vc_tools.github.client.get')
    def test_list_all_prs_deduplication_logic(self, mock_config, mock_subprocess, mock_auth_user):
        """Test deduplication when user is both author and reviewer."""
        mock_config.side_effect = lambda section, key, fallback=None: {
            ('git-org', 'org_name'): 'test-org',
            ('git', 'repo_name'): 'test-repo',
            ('filters', 'include_reviewer_prs'): 'true',
            ('filters', 'include_reviewed_prs'): 'true'
        }.get((section, key), fallback)
        
        mock_auth_user.return_value = "auth-user"
        
        # Same PR number returned from multiple queries
        same_pr = {**self.sample_pr_data, "number": 123}
        
        def subprocess_side_effect(args, **kwargs):
            if "author:" in args:
                return json.dumps({**same_pr, "source": "authored"}) + "\n"
            elif "review-requested:" in args:
                return json.dumps({**same_pr, "source": "reviewer"}) + "\n"
            elif "reviewed-by:" in args:
                return json.dumps({**same_pr, "source": "reviewed"}) + "\n"
            return ""
        
        mock_subprocess.side_effect = subprocess_side_effect
        
        result = list_all_prs(["test-user"], "open", False, False, False, False)
        
        # Should have only one PR despite multiple sources
        assert len(result) == 1
        assert result[0]["number"] == 123
        
        # Should have combined source indicating multiple roles
        # Priority: reviewer > reviewed > authored
        assert "both" in result[0]["source"] or "reviewer" in result[0]["source"]

    @patch('prs.vc_tools.github.client.get_authenticated_user')
    @patch('prs.vc_tools.github.client.subprocess.check_output')
    @patch('prs.vc_tools.github.client.get')
    def test_list_all_prs_no_reviewer_flag(self, mock_config, mock_subprocess, mock_auth_user):
        """Test --no-reviewer flag excludes reviewer PRs."""
        mock_config.side_effect = lambda section, key, fallback=None: {
            ('git-org', 'org_name'): 'test-org',
            ('git', 'repo_name'): 'test-repo'
        }.get((section, key), fallback)
        
        mock_auth_user.return_value = "auth-user"
        mock_subprocess.return_value = json.dumps(self.sample_pr_data) + "\n"
        
        result = list_all_prs(["test-user"], "open", False, True, False, False)
        
        # Should not call reviewer-related API endpoints
        called_args = [call.args for call in mock_subprocess.call_args_list]
        
        # Check that no reviewer queries were made
        reviewer_calls = [args for args in called_args if any("review-requested:" in str(arg) for arg in args)]
        reviewed_calls = [args for args in called_args if any("reviewed-by:" in str(arg) for arg in args)]
        
        assert len(reviewer_calls) == 0
        assert len(reviewed_calls) == 0

    @patch('prs.vc_tools.github.client.get_authenticated_user')
    @patch('prs.vc_tools.github.client.subprocess.check_output')
    @patch('prs.vc_tools.github.client.get')
    def test_list_all_prs_no_reviewed_flag(self, mock_config, mock_subprocess, mock_auth_user):
        """Test --no-reviewed flag excludes reviewed PRs."""
        mock_config.side_effect = lambda section, key, fallback=None: {
            ('git-org', 'org_name'): 'test-org',
            ('git', 'repo_name'): 'test-repo',
            ('filters', 'include_reviewer_prs'): 'true'
        }.get((section, key), fallback)
        
        mock_auth_user.return_value = "auth-user"
        mock_subprocess.return_value = json.dumps(self.sample_pr_data) + "\n"
        
        result = list_all_prs(["test-user"], "open", False, False, True, False)
        
        # Should call review-requested but not reviewed-by
        called_args = [call.args for call in mock_subprocess.call_args_list]
        
        reviewer_calls = [args for args in called_args if any("review-requested:" in str(arg) for arg in args)]
        reviewed_calls = [args for args in called_args if any("reviewed-by:" in str(arg) for arg in args)]
        
        assert len(reviewer_calls) > 0  # Should have reviewer calls
        assert len(reviewed_calls) == 0  # Should not have reviewed calls

    @patch('prs.vc_tools.github.client.get_authenticated_user')
    @patch('prs.vc_tools.github.client.subprocess.check_output')
    @patch('prs.vc_tools.github.client.get')
    def test_list_all_prs_subprocess_error_handling(self, mock_config, mock_subprocess, mock_auth_user):
        """Test graceful handling of subprocess errors."""
        mock_config.side_effect = lambda section, key, fallback=None: {
            ('git-org', 'org_name'): 'test-org',
            ('git', 'repo_name'): 'test-repo'
        }.get((section, key), fallback)
        
        mock_auth_user.return_value = "auth-user"
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, 'gh')
        
        # Should not raise exception, should return empty list
        result = list_all_prs(["test-user"], "open", False, False, False, False)
        
        assert result == []

    @patch('prs.vc_tools.github.client.get_authenticated_user')
    @patch('prs.vc_tools.github.client.subprocess.check_output')
    @patch('prs.vc_tools.github.client.get')
    def test_list_all_prs_malformed_json(self, mock_config, mock_subprocess, mock_auth_user):
        """Test handling of malformed JSON responses."""
        mock_config.side_effect = lambda section, key, fallback=None: {
            ('git-org', 'org_name'): 'test-org',
            ('git', 'repo_name'): 'test-repo'
        }.get((section, key), fallback)
        
        mock_auth_user.return_value = "auth-user"
        mock_subprocess.return_value = "invalid json\n"
        
        # Should handle malformed JSON gracefully
        result = list_all_prs(["test-user"], "open", False, False, False, False)
        
        assert result == []

    @patch('prs.vc_tools.github.client.get_authenticated_user')
    @patch('prs.vc_tools.github.client.subprocess.check_output')
    @patch('prs.vc_tools.github.client.get')
    def test_list_all_prs_empty_response(self, mock_config, mock_subprocess, mock_auth_user):
        """Test handling of empty API responses."""
        mock_config.side_effect = lambda section, key, fallback=None: {
            ('git-org', 'org_name'): 'test-org',
            ('git', 'repo_name'): 'test-repo'
        }.get((section, key), fallback)
        
        mock_auth_user.return_value = "auth-user"
        mock_subprocess.return_value = ""
        
        result = list_all_prs(["test-user"], "open", False, False, False, False)
        
        assert result == []


class TestListPullRequestIds:
    """Tests for PR ID listing functionality."""

    @patch('prs.vc_tools.github.client.list_all_prs')
    def test_list_pull_request_ids_basic(self, mock_list_all):
        """Basic PR ID extraction."""
        mock_list_all.return_value = [
            {"number": 123, "user": {"login": "user1"}},
            {"number": 456, "user": {"login": "user2"}}
        ]
        
        result = list_pull_request_ids(["test-user"], "open", False, False, False, False)
        
        assert result == [123, 456]

    @patch('prs.vc_tools.github.client.list_all_prs')
    def test_list_pull_request_ids_empty(self, mock_list_all):
        """Empty PR list returns empty IDs."""
        mock_list_all.return_value = []
        
        result = list_pull_request_ids(["test-user"], "open", False, False, False, False)
        
        assert result == []

    @patch('prs.vc_tools.github.client.list_all_prs')
    def test_list_pull_request_ids_missing_number(self, mock_list_all):
        """Handle PRs with missing number field."""
        mock_list_all.return_value = [
            {"number": 123, "user": {"login": "user1"}},
            {"user": {"login": "user2"}},  # Missing number
            {"number": 456, "user": {"login": "user3"}}
        ]
        
        # Should handle missing number gracefully
        result = list_pull_request_ids(["test-user"], "open", False, False, False, False)
        
        # Might include None or skip the malformed entry
        assert 123 in result
        assert 456 in result


class TestGetPullRequestDetails:
    """Tests for PR details retrieval."""

    @patch('prs.vc_tools.github.client.subprocess.check_output')
    @patch('prs.vc_tools.github.client.get')
    def test_get_pull_request_details_success(self, mock_config, mock_subprocess):
        """Successfully retrieve PR details."""
        mock_config.side_effect = lambda section, key, fallback=None: {
            ('git-org', 'org_name'): 'test-org',
            ('git', 'repo_name'): 'test-repo'
        }.get((section, key), fallback)
        
        pr_data = {
            "number": 123,
            "title": "Test PR",
            "user": {"login": "test-user"},
            "html_url": "https://github.com/test-org/test-repo/pull/123"
        }
        mock_subprocess.return_value = json.dumps(pr_data)
        
        result = get_pull_request_details(123, "authored")
        
        assert result["number"] == 123
        assert result["title"] == "Test PR"
        assert result["source"] == "authored"

    @patch('prs.vc_tools.github.client.subprocess.check_output')
    @patch('prs.vc_tools.github.client.get')
    def test_get_pull_request_details_subprocess_error(self, mock_config, mock_subprocess):
        """Handle subprocess error in PR details."""
        mock_config.side_effect = lambda section, key, fallback=None: {
            ('git-org', 'org_name'): 'test-org',
            ('git', 'repo_name'): 'test-repo'
        }.get((section, key), fallback)
        
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, 'gh')
        
        result = get_pull_request_details(123, "authored")
        
        assert result is None

    @patch('prs.vc_tools.github.client.subprocess.check_output')
    @patch('prs.vc_tools.github.client.get')
    def test_get_pull_request_details_malformed_json(self, mock_config, mock_subprocess):
        """Handle malformed JSON in PR details."""
        mock_config.side_effect = lambda section, key, fallback=None: {
            ('git-org', 'org_name'): 'test-org',
            ('git', 'repo_name'): 'test-repo'
        }.get((section, key), fallback)
        
        mock_subprocess.return_value = "invalid json"
        
        result = get_pull_request_details(123, "authored")
        
        assert result is None

    @patch('prs.vc_tools.github.client.subprocess.check_output')
    @patch('prs.vc_tools.github.client.get')
    def test_get_pull_request_details_with_source_tag(self, mock_config, mock_subprocess):
        """PR details includes source tag."""
        mock_config.side_effect = lambda section, key, fallback=None: {
            ('git-org', 'org_name'): 'test-org',
            ('git', 'repo_name'): 'test-repo'
        }.get((section, key), fallback)
        
        pr_data = {"number": 123, "title": "Test PR"}
        mock_subprocess.return_value = json.dumps(pr_data)
        
        result = get_pull_request_details(123, "reviewer_pending")
        
        assert result["source"] == "reviewer_pending"

    @patch('prs.vc_tools.github.client.subprocess.check_output')
    @patch('prs.vc_tools.github.client.get')
    def test_get_pull_request_details_complex_data(self, mock_config, mock_subprocess):
        """Handle complex PR data structure."""
        mock_config.side_effect = lambda section, key, fallback=None: {
            ('git-org', 'org_name'): 'test-org',
            ('git', 'repo_name'): 'test-repo'
        }.get((section, key), fallback)
        
        complex_pr_data = {
            "number": 123,
            "title": "Complex PR with émojis 🚀",
            "body": "Multi\nline\nbody",
            "user": {"login": "test-user", "avatar_url": "https://avatar.url"},
            "labels": [{"name": "bug"}, {"name": "priority-high"}],
            "assignees": [{"login": "assignee1"}],
            "reviews": [{"user": {"login": "reviewer1"}, "state": "APPROVED"}],
            "head": {"ref": "feature-branch"},
            "draft": False
        }
        mock_subprocess.return_value = json.dumps(complex_pr_data)
        
        result = get_pull_request_details(123, "authored")
        
        assert result["number"] == 123
        assert "🚀" in result["title"]
        assert result["source"] == "authored"
        assert "labels" in result
        assert "reviews" in result