"""
Unit tests for GitHub adapter module.

Tests cover:
- pr_info_to_model() function with various PR data shapes
- Role mapping for all combinations (author, reviewer, reviewed, etc.)
- Error handling for malformed GitHub API responses
- Data validation and transformation
- Edge cases with missing or malformed data
"""

import pytest
from unittest.mock import Mock

from prs.vc_tools.github.adapter import pr_info_to_model
from prs.core.models import PullRequest


class TestPrInfoToModelBasic:
    """Test basic functionality of pr_info_to_model."""

    def test_minimal_pr_data(self):
        """Test transformation of minimal PR data."""
        pr_json = {
            "number": 123,
            "title": "Test PR",
            "author": {"login": "testuser"},
            "url": "https://github.com/org/repo/pull/123",
            "headRefName": "feature-branch",
            "isDraft": False,
            "statusCheckRollup": [],
            "reviews": [],
            "reviewRequests": [],
            "labels": []
        }
        
        result = pr_info_to_model(pr_json)
        
        assert isinstance(result, PullRequest)
        assert result.id == 123
        assert result.title == "Test PR"
        assert result.author == "testuser"
        assert result.url == "https://github.com/org/repo/pull/123"
        assert result.branch == "feature-branch"
        assert result.is_draft is False
        assert result.labels == []
        assert result.checks == []
        assert result.reviews == []
        assert result.role is None

    def test_complete_pr_data(self):
        """Test transformation of complete PR data with all fields."""
        pr_json = {
            "number": 456,
            "title": "Complex PR with all fields",
            "author": {"login": "complex_author"},
            "url": "https://github.com/org/repo/pull/456",
            "headRefName": "complex-feature",
            "isDraft": True,
            "statusCheckRollup": [
                {"name": "CI", "status": "SUCCESS"},
                {"name": "Tests", "status": "PENDING"}
            ],
            "reviews": [
                {"user": {"login": "reviewer1"}, "state": "APPROVED"},
                {"user": {"login": "reviewer2"}, "state": "CHANGES_REQUESTED"}
            ],
            "reviewRequests": [
                {"requestedReviewer": {"login": "pending_reviewer"}}
            ],
            "labels": [
                {"name": "bug"},
                {"name": "high-priority"},
                {"name": "backend"}
            ]
        }
        
        result = pr_info_to_model(pr_json, "authored")
        
        assert result.id == 456
        assert result.title == "Complex PR with all fields"
        assert result.author == "complex_author"
        assert result.is_draft is True
        assert result.role == "author"
        assert len(result.labels) == 3
        assert "bug" in result.labels
        assert "high-priority" in result.labels
        assert "backend" in result.labels
        assert len(result.checks) == 2
        assert len(result.reviews) == 2

    def test_pr_data_with_source_tag_none(self):
        """Test PR data transformation when source_tag is None."""
        pr_json = {
            "number": 789,
            "title": "PR without source tag",
            "author": {"login": "author"},
            "url": "url",
            "headRefName": "branch",
            "isDraft": False,
            "statusCheckRollup": [],
            "reviews": [],
            "reviewRequests": [],
            "labels": []
        }
        
        result = pr_info_to_model(pr_json, None)
        
        assert result.role is None


class TestRoleMapping:
    """Test role mapping from source_tag to role field."""

    @pytest.mark.parametrize("source_tag,expected_role", [
        ("authored", "author"),
        ("reviewer_pending", "reviewer_pending"),
        ("reviewer_completed", "reviewer_completed"),
        ("both_pending", "both_pending"),
        ("both_completed", "both_completed"),
        # Legacy compatibility
        ("reviewer", "reviewer_pending"),
        ("both", "both_pending"),
        # Edge cases
        ("unknown_source", None),
        ("", None),
        (None, None)
    ])
    def test_source_tag_to_role_mapping(self, source_tag, expected_role):
        """Test mapping of various source_tag values to role."""
        pr_json = {
            "number": 1,
            "title": "Role Test",
            "author": {"login": "user"},
            "url": "url",
            "headRefName": "branch",
            "isDraft": False,
            "statusCheckRollup": [],
            "reviews": [],
            "reviewRequests": [],
            "labels": []
        }
        
        result = pr_info_to_model(pr_json, source_tag)
        
        assert result.role == expected_role

    def test_all_reviewer_role_combinations(self):
        """Test all possible reviewer role combinations."""
        base_pr = {
            "number": 1,
            "title": "Reviewer Roles Test",
            "author": {"login": "author"},
            "url": "url",
            "headRefName": "branch",
            "isDraft": False,
            "statusCheckRollup": [],
            "reviews": [],
            "reviewRequests": [],
            "labels": []
        }
        
        test_cases = [
            ("reviewer_pending", "reviewer_pending"),
            ("reviewer_completed", "reviewer_completed"),
            ("both_pending", "both_pending"),
            ("both_completed", "both_completed")
        ]
        
        for source_tag, expected_role in test_cases:
            result = pr_info_to_model(base_pr, source_tag)
            assert result.role == expected_role, f"Failed for source_tag: {source_tag}"


class TestDataHandling:
    """Test handling of various data formats and edge cases."""

    def test_missing_optional_fields(self):
        """Test handling when optional fields are missing."""
        minimal_pr = {
            "number": 123
            # All other fields missing
        }
        
        result = pr_info_to_model(minimal_pr)
        
        # Should handle missing fields gracefully with defaults
        assert result.id == 123
        assert result.title == ""
        assert result.author == ""
        assert result.url == ""
        assert result.branch == ""
        assert result.is_draft is False
        assert result.labels == []
        assert result.checks == []
        assert result.reviews == []

    def test_nested_field_extraction(self):
        """Test extraction of nested fields like author.login."""
        pr_json = {
            "number": 123,
            "title": "Nested Field Test",
            "author": {"login": "nested_user", "id": 12345, "other_field": "ignored"},
            "url": "url",
            "headRefName": "branch",
            "isDraft": False,
            "statusCheckRollup": [],
            "reviews": [],
            "reviewRequests": [],
            "labels": []
        }
        
        result = pr_info_to_model(pr_json)
        
        assert result.author == "nested_user"

    def test_missing_nested_fields(self):
        """Test handling of missing nested fields."""
        pr_json = {
            "number": 123,
            "title": "Missing Nested Test",
            "author": {},  # Missing login field
            "url": "url",
            "headRefName": "branch",
            "isDraft": False,
            "statusCheckRollup": [],
            "reviews": [],
            "reviewRequests": [],
            "labels": []
        }
        
        result = pr_info_to_model(pr_json)
        
        assert result.author == ""

    def test_author_field_completely_missing(self):
        """Test when author field is completely missing."""
        pr_json = {
            "number": 123,
            "title": "No Author Field",
            # author field missing entirely
            "url": "url",
            "headRefName": "branch",
            "isDraft": False,
            "statusCheckRollup": [],
            "reviews": [],
            "reviewRequests": [],
            "labels": []
        }
        
        result = pr_info_to_model(pr_json)
        
        assert result.author == ""

    def test_label_extraction(self):
        """Test extraction of label names from label objects."""
        pr_json = {
            "number": 123,
            "title": "Label Test",
            "author": {"login": "user"},
            "url": "url",
            "headRefName": "branch",
            "isDraft": False,
            "statusCheckRollup": [],
            "reviews": [],
            "reviewRequests": [],
            "labels": [
                {"name": "bug", "color": "red", "id": 1},
                {"name": "feature", "color": "green", "id": 2},
                {"name": "documentation", "color": "blue", "id": 3}
            ]
        }
        
        result = pr_info_to_model(pr_json)
        
        assert result.labels == ["bug", "feature", "documentation"]

    def test_label_with_missing_name(self):
        """Test handling of labels with missing name field."""
        pr_json = {
            "number": 123,
            "title": "Label Missing Name Test",
            "author": {"login": "user"},
            "url": "url",
            "headRefName": "branch", 
            "isDraft": False,
            "statusCheckRollup": [],
            "reviews": [],
            "reviewRequests": [],
            "labels": [
                {"name": "valid_label"},
                {"color": "red"},  # Missing name
                {"name": "another_valid_label"}
            ]
        }
        
        result = pr_info_to_model(pr_json)
        
        assert result.labels == ["valid_label", "", "another_valid_label"]

    def test_empty_collections(self):
        """Test handling of empty collections."""
        pr_json = {
            "number": 123,
            "title": "Empty Collections Test",
            "author": {"login": "user"},
            "url": "url",
            "headRefName": "branch",
            "isDraft": False,
            "statusCheckRollup": [],
            "reviews": [],
            "reviewRequests": [],
            "labels": []
        }
        
        result = pr_info_to_model(pr_json)
        
        assert result.labels == []
        assert result.checks == []
        assert result.reviews == []

    def test_none_collections(self):
        """Test handling when collections are None."""
        pr_json = {
            "number": 123,
            "title": "None Collections Test",
            "author": {"login": "user"},
            "url": "url",
            "headRefName": "branch",
            "isDraft": False,
            "statusCheckRollup": None,
            "reviews": None,
            "reviewRequests": None,
            "labels": None
        }
        
        # This should raise a TypeError because labels is None and we try to iterate over it
        with pytest.raises(TypeError):
            pr_info_to_model(pr_json)


class TestComplexDataStructures:
    """Test handling of complex nested data structures."""

    def test_complex_checks_data(self):
        """Test that complex checks data is preserved."""
        complex_checks = [
            {
                "name": "Continuous Integration",
                "status": "SUCCESS",
                "conclusion": "SUCCESS", 
                "detailsUrl": "https://github.com/org/repo/runs/123",
                "context": {
                    "name": "ci/build",
                    "description": "Build and test"
                }
            },
            {
                "name": "Code Quality",
                "status": "PENDING",
                "conclusion": None,
                "detailsUrl": "https://github.com/org/repo/runs/124"
            }
        ]
        
        pr_json = {
            "number": 123,
            "title": "Complex Checks Test",
            "author": {"login": "user"},
            "url": "url",
            "headRefName": "branch",
            "isDraft": False,
            "statusCheckRollup": complex_checks,
            "reviews": [],
            "reviewRequests": [],
            "labels": []
        }
        
        result = pr_info_to_model(pr_json)
        
        assert result.checks == complex_checks
        assert len(result.checks) == 2
        assert result.checks[0]["name"] == "Continuous Integration"
        assert result.checks[0]["context"]["name"] == "ci/build"
        assert result.checks[1]["conclusion"] is None

    def test_complex_reviews_data(self):
        """Test that complex reviews data is preserved."""
        complex_reviews = [
            {
                "user": {"login": "reviewer1", "id": 123},
                "state": "APPROVED",
                "body": "Looks good to me!",
                "submittedAt": "2023-12-01T10:00:00Z",
                "comments": [
                    {"body": "Nice work", "line": 10},
                    {"body": "Consider refactoring", "line": 25}
                ]
            },
            {
                "user": {"login": "reviewer2", "id": 456},
                "state": "CHANGES_REQUESTED",
                "body": "Please address the issues",
                "submittedAt": "2023-12-01T11:00:00Z"
            }
        ]
        
        pr_json = {
            "number": 123,
            "title": "Complex Reviews Test",
            "author": {"login": "user"},
            "url": "url",
            "headRefName": "branch",
            "isDraft": False,
            "statusCheckRollup": [],
            "reviews": complex_reviews,
            "reviewRequests": [],
            "labels": []
        }
        
        result = pr_info_to_model(pr_json)
        
        assert result.reviews == complex_reviews
        assert len(result.reviews) == 2
        assert result.reviews[0]["user"]["login"] == "reviewer1"
        assert result.reviews[0]["comments"][0]["body"] == "Nice work"
        assert result.reviews[1]["state"] == "CHANGES_REQUESTED"

    def test_preserved_review_requests(self):
        """Test that reviewRequests data is preserved in checks field."""
        # Note: Based on the implementation, reviewRequests is extracted but not used
        # in the PullRequest constructor. This test documents current behavior.
        review_requests = [
            {"requestedReviewer": {"login": "pending_reviewer1"}},
            {"requestedReviewer": {"login": "pending_reviewer2"}}
        ]
        
        pr_json = {
            "number": 123,
            "title": "Review Requests Test",
            "author": {"login": "user"},
            "url": "url",
            "headRefName": "branch",
            "isDraft": False,
            "statusCheckRollup": [],
            "reviews": [],
            "reviewRequests": review_requests,
            "labels": []
        }
        
        result = pr_info_to_model(pr_json)
        
        # reviewRequests is extracted but not used in PullRequest constructor
        # This test documents the current behavior
        assert result.checks == []  # reviewRequests not stored in checks


class TestEdgeCases:
    """Test edge cases and unusual data scenarios."""

    def test_zero_pr_number(self):
        """Test handling of zero PR number."""
        pr_json = {
            "number": 0,
            "title": "Zero PR Number",
            "author": {"login": "user"},
            "url": "url",
            "headRefName": "branch",
            "isDraft": False,
            "statusCheckRollup": [],
            "reviews": [],
            "reviewRequests": [],
            "labels": []
        }
        
        result = pr_info_to_model(pr_json)
        
        assert result.id == 0

    def test_negative_pr_number(self):
        """Test handling of negative PR number (unusual but possible)."""
        pr_json = {
            "number": -1,
            "title": "Negative PR Number",
            "author": {"login": "user"},
            "url": "url",
            "headRefName": "branch",
            "isDraft": False,
            "statusCheckRollup": [],
            "reviews": [],
            "reviewRequests": [],
            "labels": []
        }
        
        result = pr_info_to_model(pr_json)
        
        assert result.id == -1

    def test_missing_pr_number(self):
        """Test handling when PR number is missing."""
        pr_json = {
            # number field missing
            "title": "Missing PR Number",
            "author": {"login": "user"},
            "url": "url",
            "headRefName": "branch",
            "isDraft": False,
            "statusCheckRollup": [],
            "reviews": [],
            "reviewRequests": [],
            "labels": []
        }
        
        result = pr_info_to_model(pr_json)
        
        assert result.id == 0  # Default fallback

    def test_very_long_title(self):
        """Test handling of very long PR title."""
        long_title = "A" * 1000
        pr_json = {
            "number": 123,
            "title": long_title,
            "author": {"login": "user"},
            "url": "url",
            "headRefName": "branch",
            "isDraft": False,
            "statusCheckRollup": [],
            "reviews": [],
            "reviewRequests": [],
            "labels": []
        }
        
        result = pr_info_to_model(pr_json)
        
        assert result.title == long_title

    def test_empty_string_fields(self):
        """Test handling of empty string fields."""
        pr_json = {
            "number": 123,
            "title": "",
            "author": {"login": ""},
            "url": "",
            "headRefName": "",
            "isDraft": False,
            "statusCheckRollup": [],
            "reviews": [],
            "reviewRequests": [],
            "labels": []
        }
        
        result = pr_info_to_model(pr_json)
        
        assert result.title == ""
        assert result.author == ""
        assert result.url == ""
        assert result.branch == ""

    def test_unicode_and_special_characters(self):
        """Test handling of Unicode and special characters."""
        pr_json = {
            "number": 123,
            "title": "Add support for émojis 🚀 and ∑pecial characters",
            "author": {"login": "用户-with-unicode_and-dashes"},
            "url": "https://github.com/org/repo/pull/123",
            "headRefName": "feature/émoji-support-🚀",
            "isDraft": False,
            "statusCheckRollup": [],
            "reviews": [],
            "reviewRequests": [],
            "labels": [
                {"name": "🐛 bug"},
                {"name": "✨ enhancement"},
                {"name": "unicode-∑upport"}
            ]
        }
        
        result = pr_info_to_model(pr_json)
        
        assert "émojis 🚀" in result.title
        assert result.author == "用户-with-unicode_and-dashes"
        assert "émoji-support-🚀" in result.branch
        assert "🐛 bug" in result.labels
        assert "✨ enhancement" in result.labels
        assert "unicode-∑upport" in result.labels

    def test_boolean_field_variations(self):
        """Test handling of different boolean field variations."""
        test_cases = [
            (True, True),
            (False, False),
            ("true", "true"),  # String instead of boolean (passed through)
            ("false", "false"),
            (1, 1),  # Integer instead of boolean (passed through)
            (0, 0),
        ]
        
        for input_value, expected_value in test_cases:
            pr_json = {
                "number": 123,
                "title": f"Boolean Test {input_value}",
                "author": {"login": "user"},
                "url": "url",
                "headRefName": "branch",
                "isDraft": input_value,
                "statusCheckRollup": [],
                "reviews": [],
                "reviewRequests": [],
                "labels": []
            }
            
            result = pr_info_to_model(pr_json)
            
            # The implementation passes through the value as-is
            assert result.is_draft == input_value

    def test_boolean_field_none_default(self):
        """Test that None isDraft defaults to False."""
        pr_json = {
            "number": 123,
            "title": "None Boolean Test",
            "author": {"login": "user"},
            "url": "url",
            "headRefName": "branch",
            # isDraft missing, should default to False
            "statusCheckRollup": [],
            "reviews": [],
            "reviewRequests": [],
            "labels": []
        }
        
        result = pr_info_to_model(pr_json)
        
        # Missing field should default to False via .get() method
        assert result.is_draft is False


class TestPullRequestIntegration:
    """Test integration with PullRequest model."""

    def test_pullrequest_model_compatibility(self):
        """Test that adapter output is compatible with PullRequest model."""
        pr_json = {
            "number": 123,
            "title": "Integration Test",
            "author": {"login": "testuser"},
            "url": "https://github.com/org/repo/pull/123",
            "headRefName": "test-branch",
            "isDraft": True,
            "statusCheckRollup": [{"name": "test", "status": "success"}],
            "reviews": [{"user": {"login": "reviewer"}, "state": "APPROVED"}],
            "reviewRequests": [],
            "labels": [{"name": "test-label"}]
        }
        
        result = pr_info_to_model(pr_json, "both_pending")
        
        # Test that result has all expected PullRequest attributes
        assert hasattr(result, 'id')
        assert hasattr(result, 'title')
        assert hasattr(result, 'author')
        assert hasattr(result, 'labels')
        assert hasattr(result, 'checks')
        assert hasattr(result, 'reviews')
        assert hasattr(result, 'url')
        assert hasattr(result, 'branch')
        assert hasattr(result, 'is_draft')
        assert hasattr(result, 'role')
        assert hasattr(result, 'source')
        assert hasattr(result, 'isDraft')  # Compatibility property
        
        # Test that methods work
        assert result.summary() == "[#123] Integration Test by testuser"

    def test_data_type_consistency(self):
        """Test that data types are consistent with PullRequest expectations."""
        pr_json = {
            "number": 456,
            "title": "Type Consistency Test",
            "author": {"login": "typeuser"},
            "url": "https://test.com",
            "headRefName": "type-branch",
            "isDraft": False,
            "statusCheckRollup": [{"check": "data"}],
            "reviews": [{"review": "data"}],
            "reviewRequests": [],
            "labels": [{"name": "type-label"}]
        }
        
        result = pr_info_to_model(pr_json, "reviewer_completed")
        
        # Check data types
        assert isinstance(result.id, int)
        assert isinstance(result.title, str)
        assert isinstance(result.author, str)
        assert isinstance(result.url, str)
        assert isinstance(result.branch, str)
        assert isinstance(result.is_draft, bool)
        assert isinstance(result.labels, list)
        assert isinstance(result.checks, list)
        assert isinstance(result.reviews, list)
        assert isinstance(result.role, str) or result.role is None


class TestErrorResilience:
    """Test resilience to various error conditions."""

    def test_completely_empty_input(self):
        """Test handling of completely empty input."""
        result = pr_info_to_model({})
        
        assert isinstance(result, PullRequest)
        assert result.id == 0
        assert result.title == ""
        assert result.author == ""

    def test_none_input(self):
        """Test handling of None values in input."""
        pr_json = {
            "number": None,
            "title": None,
            "author": None,  # This will cause AttributeError when trying .get("login")
            "url": None,
            "headRefName": None,
            "isDraft": None,
            "statusCheckRollup": None,
            "reviews": None,
            "reviewRequests": None,
            "labels": None
        }
        
        # This should raise AttributeError when trying to call .get() on None author
        with pytest.raises(AttributeError):
            pr_info_to_model(pr_json)

    def test_malformed_nested_structures(self):
        """Test handling of malformed nested data structures."""
        pr_json = {
            "number": 123,
            "title": "Malformed Test",
            "author": "not_a_dict",  # Should be dict with login field
            "url": "url",
            "headRefName": "branch",
            "isDraft": False,
            "statusCheckRollup": "not_a_list",  # Should be list
            "reviews": "not_a_list",  # Should be list
            "reviewRequests": "not_a_list",  # Should be list
            "labels": "not_a_list"  # Should be list
        }
        
        # This should raise AttributeError when trying to call .get() on string
        with pytest.raises(AttributeError):
            pr_info_to_model(pr_json)

    def test_mixed_valid_invalid_data(self):
        """Test handling when some fields are valid and others invalid."""
        pr_json = {
            "number": 123,  # Valid
            "title": "Mixed Data Test",  # Valid
            "author": {"login": "valid_user"},  # Valid
            "url": "valid_url",  # Valid
            "headRefName": "valid_branch",  # Valid
            "isDraft": False,  # Valid
            "statusCheckRollup": [],  # Valid
            "reviews": [],  # Valid
            "reviewRequests": [],  # Valid
            "labels": [
                {"name": "valid_label"},  # Valid
                {"invalid": "no_name_field"},  # Invalid - missing name
                {"name": "another_valid_label"}  # Valid
            ]
        }
        
        result = pr_info_to_model(pr_json)
        
        # Valid fields should work correctly
        assert result.id == 123
        assert result.title == "Mixed Data Test"
        assert result.author == "valid_user"
        
        # Invalid label should have empty name
        assert result.labels == ["valid_label", "", "another_valid_label"]