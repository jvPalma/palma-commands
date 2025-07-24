"""
Unit tests for the PullRequest domain model.

Tests cover:
- Basic initialization and property access
- Role types and combinations
- Compatibility properties  
- Edge cases and data validation
- Summary method functionality
"""

import pytest
from prs.core.models import PullRequest


class TestPullRequestInitialization:
    """Test basic initialization of PullRequest objects."""

    def test_basic_initialization(self):
        """Test PullRequest can be initialized with required parameters."""
        pr = PullRequest(
            id=123,
            title="Test PR Title",
            author="testuser",
            labels=["bug", "feature"],
            checks=[{"name": "CI", "status": "success"}],
            reviews=[{"user": "reviewer1", "state": "APPROVED"}],
            url="https://github.com/org/repo/pull/123",
            branch="feature-branch",
            is_draft=False
        )
        
        assert pr.id == 123
        assert pr.title == "Test PR Title"
        assert pr.author == "testuser"
        assert pr.labels == ["bug", "feature"]
        assert pr.checks == [{"name": "CI", "status": "success"}]
        assert pr.reviews == [{"user": "reviewer1", "state": "APPROVED"}]
        assert pr.url == "https://github.com/org/repo/pull/123"
        assert pr.branch == "feature-branch"
        assert pr.is_draft is False
        assert pr.role is None
        assert pr.source is None

    def test_initialization_with_optional_role(self):
        """Test PullRequest initialization with optional role parameter."""
        pr = PullRequest(
            id=456,
            title="PR with Role",
            author="author1",
            labels=[],
            checks=[],
            reviews=[],
            url="https://github.com/org/repo/pull/456",
            branch="main",
            is_draft=True,
            role="author"
        )
        
        assert pr.role == "author"
        assert pr.is_draft is True

    def test_draft_compatibility_property(self):
        """Test that isDraft property is correctly set for backward compatibility."""
        # Test with draft=True
        draft_pr = PullRequest(
            id=1, title="Draft", author="user", labels=[], checks=[], 
            reviews=[], url="url", branch="branch", is_draft=True
        )
        assert draft_pr.isDraft is True
        assert draft_pr.is_draft is True
        
        # Test with draft=False
        normal_pr = PullRequest(
            id=2, title="Normal", author="user", labels=[], checks=[], 
            reviews=[], url="url", branch="branch", is_draft=False
        )
        assert normal_pr.isDraft is False
        assert normal_pr.is_draft is False

    def test_empty_collections_initialization(self):
        """Test initialization with empty collections."""
        pr = PullRequest(
            id=789,
            title="Empty Collections",
            author="user",
            labels=[],
            checks=[],
            reviews=[],
            url="https://example.com",
            branch="empty",
            is_draft=False
        )
        
        assert pr.labels == []
        assert pr.checks == []
        assert pr.reviews == []


class TestPullRequestRoles:
    """Test role-related functionality."""

    @pytest.mark.parametrize("role", [
        "author",
        "reviewer",
        "reviewer_pending", 
        "reviewer_completed",
        "both_pending",
        "both_completed"
    ])
    def test_valid_role_assignments(self, role):
        """Test that valid role types can be assigned."""
        pr = PullRequest(
            id=1, title="Role Test", author="user", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False, role=role
        )
        assert pr.role == role

    def test_none_role_default(self):
        """Test that role defaults to None when not specified."""
        pr = PullRequest(
            id=1, title="No Role", author="user", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False
        )
        assert pr.role is None

    def test_role_can_be_changed_after_initialization(self):
        """Test that role can be modified after object creation."""
        pr = PullRequest(
            id=1, title="Changeable Role", author="user", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False, role="author"
        )
        
        pr.role = "reviewer_pending"
        assert pr.role == "reviewer_pending"
        
        pr.role = "both_completed"
        assert pr.role == "both_completed"


class TestPullRequestSource:
    """Test source property functionality."""

    def test_source_initialization_default(self):
        """Test that source is None by default."""
        pr = PullRequest(
            id=1, title="Source Test", author="user", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False
        )
        assert pr.source is None

    def test_source_can_be_set_after_initialization(self):
        """Test that source can be set after object creation."""
        pr = PullRequest(
            id=1, title="Source Test", author="user", labels=[], checks=[],
            reviews=[], url="url", branch="branch", is_draft=False
        )
        
        pr.source = "authored"
        assert pr.source == "authored"
        
        pr.source = "team"
        assert pr.source == "team"
        
        pr.source = "review_requested"
        assert pr.source == "review_requested"


class TestPullRequestSummary:
    """Test the summary method functionality."""

    def test_summary_format(self):
        """Test that summary returns correct format."""
        pr = PullRequest(
            id=12345,
            title="Fix critical bug in authentication",
            author="developer123",
            labels=["bug", "high-priority"],
            checks=[],
            reviews=[],
            url="https://github.com/org/repo/pull/12345",
            branch="fix-auth-bug",
            is_draft=False
        )
        
        expected = "[#12345] Fix critical bug in authentication by developer123"
        assert pr.summary() == expected

    def test_summary_with_special_characters(self):
        """Test summary with special characters in title and author."""
        pr = PullRequest(
            id=999,
            title="Add support for UTF-8 émojis 🚀",
            author="user-with-dashes_and_underscores",
            labels=[],
            checks=[],
            reviews=[],
            url="url",
            branch="unicode-support",
            is_draft=True
        )
        
        expected = "[#999] Add support for UTF-8 émojis 🚀 by user-with-dashes_and_underscores"
        assert pr.summary() == expected

    def test_summary_with_empty_title(self):
        """Test summary method with empty title."""
        pr = PullRequest(
            id=0,
            title="",
            author="emptyuser",
            labels=[],
            checks=[],
            reviews=[],
            url="url",
            branch="empty",
            is_draft=False
        )
        
        expected = "[#0]  by emptyuser"
        assert pr.summary() == expected


class TestPullRequestEdgeCases:
    """Test edge cases and unusual inputs."""

    def test_negative_id(self):
        """Test that negative IDs are handled (though unusual in practice)."""
        pr = PullRequest(
            id=-1,
            title="Negative ID Test",
            author="user",
            labels=[],
            checks=[],
            reviews=[],
            url="url",
            branch="branch",
            is_draft=False
        )
        assert pr.id == -1
        assert pr.summary() == "[#-1] Negative ID Test by user"

    def test_zero_id(self):
        """Test that zero ID is handled."""
        pr = PullRequest(
            id=0,
            title="Zero ID Test",
            author="user",
            labels=[],
            checks=[],
            reviews=[],
            url="url",
            branch="branch",
            is_draft=False
        )
        assert pr.id == 0

    def test_very_long_title(self):
        """Test handling of very long title."""
        long_title = "A" * 1000
        pr = PullRequest(
            id=1,
            title=long_title,
            author="user",
            labels=[],
            checks=[],
            reviews=[],
            url="url",
            branch="branch",
            is_draft=False
        )
        assert pr.title == long_title
        assert long_title in pr.summary()

    def test_empty_author(self):
        """Test handling of empty author."""
        pr = PullRequest(
            id=1,
            title="Empty Author Test",
            author="",
            labels=[],
            checks=[],
            reviews=[],
            url="url",
            branch="branch",
            is_draft=False
        )
        assert pr.author == ""
        assert pr.summary().endswith(" by ")

    def test_none_values_in_collections(self):
        """Test handling of None values within collections."""
        pr = PullRequest(
            id=1,
            title="None Values Test",
            author="user",
            labels=["valid", None, "label"],
            checks=[{"name": "test"}, None, {"status": "pending"}],
            reviews=[None, {"user": "reviewer"}],
            url="url",
            branch="branch",
            is_draft=False
        )
        
        # The model should store exactly what's passed
        assert None in pr.labels
        assert None in pr.checks
        assert None in pr.reviews

    def test_complex_nested_data_structures(self):
        """Test handling of complex nested data in checks and reviews."""
        complex_checks = [
            {
                "name": "CI",
                "status": "success",
                "details": {
                    "tests": 150,
                    "coverage": "95%",
                    "nested": {"deep": {"value": True}}
                }
            }
        ]
        
        complex_reviews = [
            {
                "user": "reviewer1",
                "state": "APPROVED",
                "comments": [
                    {"line": 10, "body": "LGTM"},
                    {"line": 25, "body": "Consider refactoring"}
                ]
            }
        ]
        
        pr = PullRequest(
            id=1,
            title="Complex Data Test",
            author="user",
            labels=["test"],
            checks=complex_checks,
            reviews=complex_reviews,
            url="url",
            branch="branch",
            is_draft=False
        )
        
        assert pr.checks == complex_checks
        assert pr.reviews == complex_reviews
        assert pr.checks[0]["details"]["nested"]["deep"]["value"] is True


class TestPullRequestStringRepresentation:
    """Test string representations and attribute access."""

    def test_attribute_access(self):
        """Test that all attributes are accessible."""
        pr = PullRequest(
            id=123,
            title="Attribute Test",
            author="testuser",
            labels=["label1"],
            checks=[{"check": "data"}],
            reviews=[{"review": "data"}],
            url="test-url",
            branch="test-branch", 
            is_draft=True,
            role="test-role"
        )
        
        # Test all attributes are accessible
        assert hasattr(pr, 'id')
        assert hasattr(pr, 'title')
        assert hasattr(pr, 'author')
        assert hasattr(pr, 'labels')
        assert hasattr(pr, 'checks')
        assert hasattr(pr, 'reviews')
        assert hasattr(pr, 'url')
        assert hasattr(pr, 'branch')
        assert hasattr(pr, 'is_draft')
        assert hasattr(pr, 'isDraft')  # Compatibility property
        assert hasattr(pr, 'role')
        assert hasattr(pr, 'source')

    def test_attributes_are_mutable(self):
        """Test that attributes can be modified after initialization."""
        pr = PullRequest(
            id=1, title="Original", author="original_author", labels=["old"],
            checks=[], reviews=[], url="old_url", branch="old_branch", is_draft=False
        )
        
        # Modify attributes
        pr.title = "Modified Title"
        pr.author = "new_author"
        pr.labels.append("new")
        pr.is_draft = True
        pr.url = "new_url"
        pr.branch = "new_branch"
        
        # Verify changes
        assert pr.title == "Modified Title"
        assert pr.author == "new_author"
        assert "new" in pr.labels
        assert pr.is_draft is True
        assert pr.isDraft is False  # Compatibility property is set once at initialization
        assert pr.url == "new_url"
        assert pr.branch == "new_branch"