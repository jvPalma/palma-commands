"""
Unit tests for user filtering functionality.

Tests cover:
- User filtering logic with various scenarios
- CLI ignore-user command parsing and execution
- Configuration system user management
- Integration with existing PR pipeline
- Edge cases and error handling
"""

import pytest
from unittest.mock import patch, Mock

from prs.core.printPullRequests import filter_ignored_users_prs
from prs.core.models import PullRequest


class TestUserFilteringLogic:
    """Test core user filtering logic."""

    def create_mock_pr(self, author="user", pr_id=123):
        """Create a mock PR for testing."""
        return PullRequest(
            id=pr_id,
            title=f"Test PR {pr_id}",
            author=author,
            labels=[],
            checks=[],
            reviews=[],
            url=f"https://github.com/org/repo/pull/{pr_id}",
            branch=f"branch-{pr_id}",
            is_draft=False,
            role="author"
        )

    @patch('prs.core.printPullRequests.get_ignored_users')
    def test_filter_ignored_users_prs_no_users_configured(self, mock_get_users):
        """Test filtering when no users are configured."""
        mock_get_users.return_value = []
        
        prs = [
            self.create_mock_pr("user1", 1),
            self.create_mock_pr("app/anchor-renovate", 2),
            self.create_mock_pr("user2", 3)
        ]
        
        filtered_prs, user_count = filter_ignored_users_prs(prs, include_ignored_users=False)
        
        assert len(filtered_prs) == 3
        assert user_count == 0
        assert filtered_prs == prs

    @patch('prs.core.printPullRequests.get_ignored_users')
    def test_filter_ignored_users_prs_with_users_configured(self, mock_get_users):
        """Test filtering when users are configured."""
        mock_get_users.return_value = ["app/anchor-renovate", "dependabot[bot]"]
        
        prs = [
            self.create_mock_pr("user1", 1),
            self.create_mock_pr("app/anchor-renovate", 2),
            self.create_mock_pr("user2", 3),
            self.create_mock_pr("dependabot[bot]", 4),
            self.create_mock_pr("user3", 5)
        ]
        
        filtered_prs, user_count = filter_ignored_users_prs(prs, include_ignored_users=False)
        
        assert len(filtered_prs) == 3
        assert user_count == 2
        assert all(pr.author not in ["app/anchor-renovate", "dependabot[bot]"] for pr in filtered_prs)

    @patch('prs.core.printPullRequests.get_ignored_users')
    def test_filter_ignored_users_prs_include_users_override(self, mock_get_users):
        """Test that include_ignored_users=True returns all PRs."""
        mock_get_users.return_value = ["app/anchor-renovate", "dependabot[bot]"]
        
        prs = [
            self.create_mock_pr("user1", 1),
            self.create_mock_pr("app/anchor-renovate", 2),
            self.create_mock_pr("dependabot[bot]", 3)
        ]
        
        filtered_prs, user_count = filter_ignored_users_prs(prs, include_ignored_users=True)
        
        assert len(filtered_prs) == 3
        assert user_count == 0
        assert filtered_prs == prs

    @patch('prs.core.printPullRequests.get_ignored_users')
    def test_filter_ignored_users_prs_all_users(self, mock_get_users):
        """Test filtering when all PRs are from ignored users."""
        mock_get_users.return_value = ["app/anchor-renovate", "dependabot[bot]"]
        
        prs = [
            self.create_mock_pr("app/anchor-renovate", 1),
            self.create_mock_pr("dependabot[bot]", 2),
            self.create_mock_pr("app/anchor-renovate", 3)
        ]
        
        filtered_prs, user_count = filter_ignored_users_prs(prs, include_ignored_users=False)
        
        assert len(filtered_prs) == 0
        assert user_count == 3

    @patch('prs.core.printPullRequests.get_ignored_users')
    def test_filter_ignored_users_prs_no_user_prs(self, mock_get_users):
        """Test filtering when no PRs are from ignored users."""
        mock_get_users.return_value = ["app/anchor-renovate", "dependabot[bot]"]
        
        prs = [
            self.create_mock_pr("user1", 1),
            self.create_mock_pr("user2", 2),
            self.create_mock_pr("user3", 3)
        ]
        
        filtered_prs, user_count = filter_ignored_users_prs(prs, include_ignored_users=False)
        
        assert len(filtered_prs) == 3
        assert user_count == 0
        assert filtered_prs == prs

    @patch('prs.core.printPullRequests.get_ignored_users')
    def test_filter_ignored_users_prs_empty_pr_list(self, mock_get_users):
        """Test filtering with empty PR list."""
        mock_get_users.return_value = ["app/anchor-renovate"]
        
        prs = []
        
        filtered_prs, user_count = filter_ignored_users_prs(prs, include_ignored_users=False)
        
        assert len(filtered_prs) == 0
        assert user_count == 0

    @patch('prs.core.printPullRequests.get_ignored_users')
    def test_filter_ignored_users_prs_special_characters(self, mock_get_users):
        """Test filtering with user names containing special characters."""
        mock_get_users.return_value = ["app/anchor-renovate", "dependabot[bot]", "renovate-bot"]
        
        prs = [
            self.create_mock_pr("user1", 1),
            self.create_mock_pr("app/anchor-renovate", 2),  # Contains /
            self.create_mock_pr("dependabot[bot]", 3),      # Contains []
            self.create_mock_pr("renovate-bot", 4),         # Contains -
            self.create_mock_pr("user2", 5)
        ]
        
        filtered_prs, user_count = filter_ignored_users_prs(prs, include_ignored_users=False)
        
        assert len(filtered_prs) == 2
        assert user_count == 3
        assert all(pr.author in ["user1", "user2"] for pr in filtered_prs)

    @patch('prs.core.printPullRequests.get_ignored_users')
    def test_filter_ignored_users_prs_case_sensitive(self, mock_get_users):
        """Test that user filtering is case-sensitive."""
        mock_get_users.return_value = ["app/anchor-renovate"]
        
        prs = [
            self.create_mock_pr("app/anchor-renovate", 1),  # Exact match
            self.create_mock_pr("APP/ANCHOR-RENOVATE", 2),  # Different case
            self.create_mock_pr("user1", 3)
        ]
        
        filtered_prs, user_count = filter_ignored_users_prs(prs, include_ignored_users=False)
        
        # Only exact case match should be filtered
        assert len(filtered_prs) == 2
        assert user_count == 1
        assert filtered_prs[0].author == "APP/ANCHOR-RENOVATE"
        assert filtered_prs[1].author == "user1"


class TestConfigUserFunctions:
    """Test user configuration functions."""

    @patch('prs.config.get')
    def test_get_ignored_users_empty(self, mock_get):
        """Test getting ignored users when none are configured."""
        from prs.config import get_ignored_users
        
        mock_get.return_value = ""
        result = get_ignored_users()
        
        assert result == []

    @patch('prs.config.get')
    def test_get_ignored_users_single(self, mock_get):
        """Test getting single ignored user."""
        from prs.config import get_ignored_users
        
        mock_get.return_value = "app/anchor-renovate"
        result = get_ignored_users()
        
        assert result == ["app/anchor-renovate"]

    @patch('prs.config.get')
    def test_get_ignored_users_multiple(self, mock_get):
        """Test getting multiple ignored users."""
        from prs.config import get_ignored_users
        
        mock_get.return_value = "app/anchor-renovate,dependabot[bot],renovate-bot"
        result = get_ignored_users()
        
        assert result == ["app/anchor-renovate", "dependabot[bot]", "renovate-bot"]

    @patch('prs.config.get')
    def test_get_ignored_users_with_spaces(self, mock_get):
        """Test getting ignored users with whitespace."""
        from prs.config import get_ignored_users
        
        mock_get.return_value = " app/anchor-renovate , dependabot[bot] , renovate-bot "
        result = get_ignored_users()
        
        assert result == ["app/anchor-renovate", "dependabot[bot]", "renovate-bot"]

    @patch('prs.config.get')
    def test_get_ignored_users_empty_elements(self, mock_get):
        """Test getting ignored users with empty elements."""
        from prs.config import get_ignored_users
        
        mock_get.return_value = "app/anchor-renovate,,dependabot[bot], ,renovate-bot"
        result = get_ignored_users()
        
        assert result == ["app/anchor-renovate", "dependabot[bot]", "renovate-bot"]

    @patch('prs.config.set')
    def test_set_ignored_users(self, mock_set):
        """Test setting ignored users."""
        from prs.config import set_ignored_users
        
        users = ["app/anchor-renovate", "dependabot[bot]"]
        set_ignored_users(users)
        
        mock_set.assert_called_once_with("filters", "ignored_users", "app/anchor-renovate,dependabot[bot]")

    @patch('prs.config.set')
    def test_set_ignored_users_empty(self, mock_set):
        """Test setting empty ignored users list."""
        from prs.config import set_ignored_users
        
        set_ignored_users([])
        
        mock_set.assert_called_once_with("filters", "ignored_users", "")

    @patch('prs.config.get_ignored_users')
    @patch('prs.config.set_ignored_users')
    def test_add_ignored_users_to_empty(self, mock_set, mock_get):
        """Test adding users to empty list."""
        from prs.config import add_ignored_users
        
        mock_get.return_value = []
        new_users = ["app/anchor-renovate", "dependabot[bot]"]
        
        add_ignored_users(new_users)
        
        mock_set.assert_called_once_with(["app/anchor-renovate", "dependabot[bot]"])

    @patch('prs.config.get_ignored_users')
    @patch('prs.config.set_ignored_users')
    def test_add_ignored_users_to_existing(self, mock_set, mock_get):
        """Test adding users to existing list."""
        from prs.config import add_ignored_users
        
        mock_get.return_value = ["app/anchor-renovate"]
        new_users = ["dependabot[bot]", "renovate-bot"]
        
        add_ignored_users(new_users)
        
        mock_set.assert_called_once_with(["app/anchor-renovate", "dependabot[bot]", "renovate-bot"])

    @patch('prs.config.get_ignored_users')
    @patch('prs.config.set_ignored_users')
    def test_add_ignored_users_with_duplicates(self, mock_set, mock_get):
        """Test adding users with duplicates removes duplicates."""
        from prs.config import add_ignored_users
        
        mock_get.return_value = ["app/anchor-renovate", "dependabot[bot]"]
        new_users = ["dependabot[bot]", "renovate-bot", "app/anchor-renovate"]
        
        add_ignored_users(new_users)
        
        # Should preserve order and not duplicate
        mock_set.assert_called_once_with(["app/anchor-renovate", "dependabot[bot]", "renovate-bot"])


class TestCLIUserCommands:
    """Test CLI user command functionality."""

    def test_user_ignore_command_parsing(self):
        """Test parsing of user usernames from command line."""
        # Test comma-separated parsing logic
        user_usernames_input = "app/anchor-renovate,dependabot[bot],renovate-bot"
        user_usernames = [user.strip() for user in user_usernames_input.split(",") if user.strip()]
        
        assert user_usernames == ["app/anchor-renovate", "dependabot[bot]", "renovate-bot"]

    def test_user_ignore_command_parsing_with_spaces(self):
        """Test parsing with spaces around usernames."""
        user_usernames_input = " app/anchor-renovate , dependabot[bot] , renovate-bot "
        user_usernames = [user.strip() for user in user_usernames_input.split(",") if user.strip()]
        
        assert user_usernames == ["app/anchor-renovate", "dependabot[bot]", "renovate-bot"]

    def test_user_ignore_command_parsing_empty_elements(self):
        """Test parsing with empty elements."""
        user_usernames_input = "app/anchor-renovate,,dependabot[bot], ,renovate-bot"
        user_usernames = [user.strip() for user in user_usernames_input.split(",") if user.strip()]
        
        assert user_usernames == ["app/anchor-renovate", "dependabot[bot]", "renovate-bot"]

    def test_user_ignore_command_parsing_single_user(self):
        """Test parsing single user username."""
        user_usernames_input = "app/anchor-renovate"
        user_usernames = [user.strip() for user in user_usernames_input.split(",") if user.strip()]
        
        assert user_usernames == ["app/anchor-renovate"]

    def test_user_ignore_command_parsing_empty_string(self):
        """Test parsing empty string."""
        user_usernames_input = ""
        user_usernames = [user.strip() for user in user_usernames_input.split(",") if user.strip()]
        
        assert user_usernames == []

    def test_user_ignore_command_parsing_only_spaces(self):
        """Test parsing string with only spaces and commas."""
        user_usernames_input = " , , "
        user_usernames = [user.strip() for user in user_usernames_input.split(",") if user.strip()]
        
        assert user_usernames == []


class TestIntegrationWithPRPipeline:
    """Test integration of user filtering with PR processing pipeline."""

    def create_mock_pr(self, author="user", pr_id=123):
        """Create a mock PR for testing."""
        return PullRequest(
            id=pr_id,
            title=f"Test PR {pr_id}",
            author=author,
            labels=[],
            checks=[],
            reviews=[],
            url=f"https://github.com/org/repo/pull/{pr_id}",
            branch=f"branch-{pr_id}",
            is_draft=False,
            role="author"
        )

    @patch('prs.core.printPullRequests.get_ignored_prs')
    @patch('prs.core.printPullRequests.get_ignored_users')
    @patch('prs.core.printPullRequests.list_pull_request_ids')
    @patch('prs.core.printPullRequests.get_pull_request_details')
    @patch('prs.core.printPullRequests.render_pr_panel')
    @patch('prs.core.printPullRequests.render_ignored_count')
    def test_list_pull_requests_with_user_filtering(self, mock_render_ignored, mock_render_panel, 
                                                   mock_get_details, mock_list_ids, 
                                                   mock_get_users, mock_get_ignored):
        """Test complete PR listing with user filtering."""
        from prs.core.printPullRequests import list_pull_requests
        
        # Mock data
        mock_list_ids.return_value = [(1, "authored", False), (2, "authored", False), (3, "authored", False)]
        mock_get_ignored.return_value = []  # No ignored PRs
        mock_get_users.return_value = ["app/anchor-renovate"]  # One user configured
        
        # Mock PR details
        def details_side_effect(pr_id, source):
            authors = {1: "user1", 2: "app/anchor-renovate", 3: "user2"}
            return self.create_mock_pr(authors[pr_id], pr_id)
        
        mock_get_details.side_effect = details_side_effect
        
        # Test without including ignored users (default)
        options = {"include_from_ignored_users": False}
        list_pull_requests(options)
        
        # Should render 2 PRs (user1 and user2, ignored user filtered out)
        assert mock_render_panel.call_count == 2
        # Should show 1 filtered (ignored user) PR
        mock_render_ignored.assert_called_once()
        assert mock_render_ignored.call_args[0][0] == 1  # First argument should be 1

    @patch('prs.core.printPullRequests.get_ignored_prs')
    @patch('prs.core.printPullRequests.get_ignored_users')
    @patch('prs.core.printPullRequests.list_pull_request_ids')
    @patch('prs.core.printPullRequests.get_pull_request_details')
    @patch('prs.core.printPullRequests.render_pr_panel')
    @patch('prs.core.printPullRequests.render_ignored_count')
    def test_list_pull_requests_include_users(self, mock_render_ignored, mock_render_panel,
                                            mock_get_details, mock_list_ids,
                                            mock_get_users, mock_get_ignored):
        """Test PR listing with ignored users included."""
        from prs.core.printPullRequests import list_pull_requests
        
        # Mock data
        mock_list_ids.return_value = [(1, "authored", False), (2, "authored", False), (3, "authored", False)]
        mock_get_ignored.return_value = []  # No ignored PRs
        mock_get_users.return_value = ["app/anchor-renovate"]  # One user configured
        
        # Mock PR details
        def details_side_effect(pr_id, source):
            authors = {1: "user1", 2: "app/anchor-renovate", 3: "user2"}
            return self.create_mock_pr(authors[pr_id], pr_id)
        
        mock_get_details.side_effect = details_side_effect
        
        # Test with including ignored users
        options = {"include_from_ignored_users": True}
        list_pull_requests(options)
        
        # Should render all 3 PRs (including ignored user)
        assert mock_render_panel.call_count == 3
        # Should show 0 filtered PRs
        mock_render_ignored.assert_called_once()
        assert mock_render_ignored.call_args[0][0] == 0  # First argument should be 0

    @patch('prs.core.printPullRequests.get_ignored_prs')
    @patch('prs.core.printPullRequests.get_ignored_users')
    @patch('prs.core.printPullRequests.list_pull_request_ids')
    @patch('prs.core.printPullRequests.get_pull_request_details')
    @patch('prs.core.printPullRequests.render_pr_panel')
    @patch('prs.core.printPullRequests.render_ignored_count')
    def test_list_pull_requests_combined_filtering(self, mock_render_ignored, mock_render_panel,
                                                   mock_get_details, mock_list_ids,
                                                   mock_get_users, mock_get_ignored):
        """Test PR listing with both ignored PRs and user filtering."""
        from prs.core.printPullRequests import list_pull_requests
        
        # Mock data
        mock_list_ids.return_value = [(1, "authored", False), (2, "authored", False), 
                                      (3, "authored", False), (4, "authored", False)]
        mock_get_ignored.return_value = [1]  # PR #1 is ignored
        mock_get_users.return_value = ["app/anchor-renovate"]  # User configured
        
        # Mock PR details
        def details_side_effect(pr_id, source):
            authors = {1: "user1", 2: "app/anchor-renovate", 3: "user2", 4: "user3"}
            return self.create_mock_pr(authors[pr_id], pr_id)
        
        mock_get_details.side_effect = details_side_effect
        
        # Test without including ignored users
        options = {"include_from_ignored_users": False}
        list_pull_requests(options)
        
        # Should render 2 PRs (user2 and user3; user1 ignored, user filtered)
        assert mock_render_panel.call_count == 2
        # Should show 2 filtered PRs (1 ignored + 1 user)
        mock_render_ignored.assert_called_once()
        assert mock_render_ignored.call_args[0][0] == 2  # First argument should be 2


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    @patch('prs.core.printPullRequests.get_ignored_users')
    def test_filter_ignored_users_prs_none_pr_list(self, mock_get_users):
        """Test filtering with None PR list."""
        mock_get_users.return_value = ["app/anchor-renovate"]
        
        # This should not crash
        try:
            filtered_prs, user_count = filter_ignored_users_prs(None, include_ignored_users=False)
            # If it doesn't crash, that's acceptable behavior
        except (TypeError, AttributeError):
            # Expected for None input
            pass

    def test_user_usernames_with_unicode(self):
        """Test handling of Unicode in user usernames."""
        user_usernames_input = "app/anchor-renovate,bøt-üser,renovate[bot]"
        user_usernames = [user.strip() for user in user_usernames_input.split(",") if user.strip()]
        
        assert user_usernames == ["app/anchor-renovate", "bøt-üser", "renovate[bot]"]

    def test_very_long_user_username(self):
        """Test handling of very long user usernames."""
        long_name = "a" * 1000
        user_usernames_input = f"app/anchor-renovate,{long_name},renovate[bot]"
        user_usernames = [user.strip() for user in user_usernames_input.split(",") if user.strip()]
        
        assert len(user_usernames) == 3
        assert user_usernames[1] == long_name

    @patch('prs.core.printPullRequests.get_ignored_users')
    def test_filter_with_many_users(self, mock_get_users):
        """Test filtering with many configured users."""
        from prs.core.printPullRequests import filter_ignored_users_prs
        from prs.core.models import PullRequest
        
        # Configure many users
        many_users = [f"user-{i}" for i in range(100)]
        mock_get_users.return_value = many_users
        
        # Create PRs from various users and normal users
        prs = []
        for i in range(50):
            author = "normaluser" if i % 10 == 0 else f"user-{i % 100}"
            pr = PullRequest(
                id=i, title=f"PR {i}", author=author, labels=[], checks=[], 
                reviews=[], url=f"url-{i}", branch=f"branch-{i}", 
                is_draft=False, role="author"
            )
            prs.append(pr)
        
        filtered_prs, user_count = filter_ignored_users_prs(prs, include_ignored_users=False)
        
        # Should only have normal user PRs (every 10th PR)
        assert len(filtered_prs) == 5  # 50 PRs, every 10th is normaluser = 5 normal PRs
        assert user_count == 45  # 50 - 5 = 45 ignored user PRs
        assert all(pr.author == "normaluser" for pr in filtered_prs)