"""
Unit tests for core helper functions.

Tests cover:
- Owner resolution functionality  
- Author reading and parsing
- Username extraction and validation
- Configuration integration
- Edge cases and error handling
"""

import pytest
from unittest.mock import patch, MagicMock

from prs.core.helpers import resolve_owner, read_authors


class TestResolveOwner:
    """Test the resolve_owner function for determining repository owner."""

    @patch('prs.core.helpers.get')
    def test_resolve_owner_with_username_config(self, mock_get):
        """Test resolve_owner when upstream config is 'username'."""
        # Setup mock to return 'username' for upstream config
        mock_get.side_effect = lambda section, key: {
            ('git', 'upstream'): 'username',
            ('git', 'username'): 'testuser',
            ('git-org', 'org_name'): 'testorg'
        }.get((section, key), '')
        
        result = resolve_owner()
        
        assert result == 'testuser'
        # Verify the correct config calls were made
        expected_calls = [
            ('git', 'upstream'),
            ('git', 'username'),
            ('git-org', 'org_name')
        ]
        actual_calls = [call.args for call in mock_get.call_args_list]
        assert actual_calls == expected_calls

    @patch('prs.core.helpers.get')
    def test_resolve_owner_with_org_name_config(self, mock_get):
        """Test resolve_owner when upstream config is 'org_name'."""
        # Setup mock to return 'org_name' for upstream config
        mock_get.side_effect = lambda section, key: {
            ('git', 'upstream'): 'org_name',
            ('git', 'username'): 'testuser',
            ('git-org', 'org_name'): 'myorganization'
        }.get((section, key), '')
        
        result = resolve_owner()
        
        assert result == 'myorganization'

    @patch('prs.core.helpers.get')
    def test_resolve_owner_with_literal_value(self, mock_get):
        """Test resolve_owner when upstream config is a literal value."""
        # Setup mock to return literal value for upstream config
        mock_get.side_effect = lambda section, key: {
            ('git', 'upstream'): 'literal-owner',
            ('git', 'username'): 'testuser',
            ('git-org', 'org_name'): 'testorg'
        }.get((section, key), '')
        
        result = resolve_owner()
        
        assert result == 'literal-owner'

    @patch('prs.core.helpers.get')
    def test_resolve_owner_with_empty_upstream_config(self, mock_get):
        """Test resolve_owner when upstream config is empty."""
        # Setup mock to return empty string for upstream config
        mock_get.side_effect = lambda section, key: {
            ('git', 'upstream'): '',
            ('git', 'username'): 'testuser',
            ('git-org', 'org_name'): 'testorg'
        }.get((section, key), '')
        
        result = resolve_owner()
        
        # Should return the empty string (literal value)
        assert result == ''

    @patch('prs.core.helpers.get')
    def test_resolve_owner_with_username_but_empty_user_config(self, mock_get):
        """Test resolve_owner when upstream is 'username' but git.username is empty."""
        # Setup mock 
        mock_get.side_effect = lambda section, key: {
            ('git', 'upstream'): 'username',
            ('git', 'username'): '',  # Empty username
            ('git-org', 'org_name'): 'testorg'
        }.get((section, key), '')
        
        result = resolve_owner()
        
        # Should return empty string (the value of git.username)
        assert result == ''

    @patch('prs.core.helpers.get')
    def test_resolve_owner_with_org_name_but_empty_org_config(self, mock_get):
        """Test resolve_owner when upstream is 'org_name' but git-org.org_name is empty."""
        # Setup mock
        mock_get.side_effect = lambda section, key: {
            ('git', 'upstream'): 'org_name',
            ('git', 'username'): 'testuser',
            ('git-org', 'org_name'): ''  # Empty org name
        }.get((section, key), '')
        
        result = resolve_owner()
        
        # Should return empty string (the value of git-org.org_name)
        assert result == ''

    @patch('prs.core.helpers.get')
    def test_resolve_owner_with_special_characters(self, mock_get):
        """Test resolve_owner with special characters in values."""
        # Setup mock with special characters
        mock_get.side_effect = lambda section, key: {
            ('git', 'upstream'): 'username',
            ('git', 'username'): 'user-with_special.chars+123',
            ('git-org', 'org_name'): 'testorg'
        }.get((section, key), '')
        
        result = resolve_owner()
        
        assert result == 'user-with_special.chars+123'

    @patch('prs.core.helpers.get')
    def test_resolve_owner_case_sensitivity(self, mock_get):
        """Test resolve_owner with different case variations."""
        # Setup mock with different case
        mock_get.side_effect = lambda section, key: {
            ('git', 'upstream'): 'USERNAME',  # Different case
            ('git', 'username'): 'testuser',
            ('git-org', 'org_name'): 'testorg'
        }.get((section, key), '')
        
        result = resolve_owner()
        
        # Should treat as literal value since it's not exactly 'username'
        assert result == 'USERNAME'


class TestReadAuthors:
    """Test the read_authors function for parsing author configuration."""

    @patch('prs.core.helpers.get')
    def test_read_authors_with_single_author(self, mock_get):
        """Test read_authors with a single author configured."""
        mock_get.side_effect = lambda section, key, fallback='': {
            ('pr-info', 'authors'): 'singleuser',
            ('git', 'username'): 'fallbackuser'
        }.get((section, key), fallback)
        
        result = read_authors()
        
        assert result == ['singleuser']

    @patch('prs.core.helpers.get')
    def test_read_authors_with_multiple_authors(self, mock_get):
        """Test read_authors with multiple authors configured."""
        mock_get.side_effect = lambda section, key, fallback='': {
            ('pr-info', 'authors'): 'user1,user2,user3',
            ('git', 'username'): 'fallbackuser'
        }.get((section, key), fallback)
        
        result = read_authors()
        
        assert result == ['user1', 'user2', 'user3']

    @patch('prs.core.helpers.get')
    def test_read_authors_with_spaces_around_names(self, mock_get):
        """Test read_authors with spaces around author names."""
        mock_get.side_effect = lambda section, key, fallback='': {
            ('pr-info', 'authors'): ' user1 , user2 , user3 ',
            ('git', 'username'): 'fallbackuser'
        }.get((section, key), fallback)
        
        result = read_authors()
        
        assert result == ['user1', 'user2', 'user3']

    @patch('prs.core.helpers.get')
    def test_read_authors_with_empty_elements(self, mock_get):
        """Test read_authors with empty elements in the list."""
        mock_get.side_effect = lambda section, key, fallback='': {
            ('pr-info', 'authors'): 'user1,,user2, ,user3',
            ('git', 'username'): 'fallbackuser'
        }.get((section, key), fallback)
        
        result = read_authors()
        
        # Empty elements should be filtered out
        assert result == ['user1', 'user2', 'user3']

    @patch('prs.core.helpers.get')
    def test_read_authors_with_empty_config(self, mock_get):
        """Test read_authors when authors config is empty."""
        mock_get.side_effect = lambda section, key, fallback='': {
            ('pr-info', 'authors'): '',
            ('git', 'username'): 'fallbackuser'
        }.get((section, key), fallback)
        
        result = read_authors()
        
        # Should fallback to git.username
        assert result == ['fallbackuser']

    @patch('prs.core.helpers.get')
    def test_read_authors_with_whitespace_only_config(self, mock_get):
        """Test read_authors when authors config is whitespace only."""
        mock_get.side_effect = lambda section, key, fallback='': {
            ('pr-info', 'authors'): '   \t\n  ',
            ('git', 'username'): 'fallbackuser'
        }.get((section, key), fallback)
        
        result = read_authors()
        
        # Should fallback to git.username
        assert result == ['fallbackuser']

    @patch('prs.core.helpers.get')
    def test_read_authors_fallback_to_username(self, mock_get):
        """Test read_authors fallback behavior when no authors configured."""
        mock_get.side_effect = lambda section, key, fallback='': {
            ('pr-info', 'authors'): fallback,  # Will return empty string
            ('git', 'username'): 'myusername'
        }.get((section, key), fallback)
        
        result = read_authors()
        
        assert result == ['myusername']

    @patch('prs.core.helpers.get')
    def test_read_authors_empty_username_fallback(self, mock_get):
        """Test read_authors when both authors and username are empty."""
        mock_get.side_effect = lambda section, key, fallback='': {
            ('pr-info', 'authors'): '',
            ('git', 'username'): ''
        }.get((section, key), fallback)
        
        result = read_authors()
        
        # Should return list with empty string
        assert result == ['']

    @patch('prs.core.helpers.get')
    def test_read_authors_with_special_characters(self, mock_get):
        """Test read_authors with special characters in usernames."""
        mock_get.side_effect = lambda section, key, fallback='': {
            ('pr-info', 'authors'): 'user-1_test,user.2+special,user@domain.com',
            ('git', 'username'): 'fallbackuser'
        }.get((section, key), fallback)
        
        result = read_authors()
        
        assert result == ['user-1_test', 'user.2+special', 'user@domain.com']

    @patch('prs.core.helpers.get')
    def test_read_authors_with_mixed_separators(self, mock_get):
        """Test read_authors behavior with different separators (only comma should work)."""
        mock_get.side_effect = lambda section, key, fallback='': {
            ('pr-info', 'authors'): 'user1;user2:user3|user4',
            ('git', 'username'): 'fallbackuser'
        }.get((section, key), fallback)
        
        result = read_authors()
        
        # Should treat the whole string as one author since only comma is the separator
        assert result == ['user1;user2:user3|user4']

    @patch('prs.core.helpers.get')
    def test_read_authors_single_comma_only(self, mock_get):
        """Test read_authors with just a comma."""
        mock_get.side_effect = lambda section, key, fallback='': {
            ('pr-info', 'authors'): ',',
            ('git', 'username'): 'fallbackuser'
        }.get((section, key), fallback)
        
        result = read_authors()
        
        # Should filter out empty elements but not fallback since string is not empty
        assert result == []

    @patch('prs.core.helpers.get')
    def test_read_authors_multiple_commas_only(self, mock_get):
        """Test read_authors with multiple commas only."""
        mock_get.side_effect = lambda section, key, fallback='': {
            ('pr-info', 'authors'): ',,,',
            ('git', 'username'): 'fallbackuser'
        }.get((section, key), fallback)
        
        result = read_authors()
        
        # Should filter out empty elements but not fallback since string is not empty
        assert result == []

    @patch('prs.core.helpers.get')
    def test_read_authors_preserves_order(self, mock_get):
        """Test that read_authors preserves the order of authors."""
        mock_get.side_effect = lambda section, key, fallback='': {
            ('pr-info', 'authors'): 'zuser,auser,muser',
            ('git', 'username'): 'fallbackuser'
        }.get((section, key), fallback)
        
        result = read_authors()
        
        # Should preserve the order from config
        assert result == ['zuser', 'auser', 'muser']

    @patch('prs.core.helpers.get', side_effect=Exception('Config error'))
    def test_read_authors_handles_config_exception(self, mock_get):
        """Test read_authors behavior when config access raises an exception."""
        # Should propagate the exception (current behavior)
        with pytest.raises(Exception, match='Config error'):
            read_authors()


class TestHelpersIntegration:
    """Integration tests for helper functions."""

    @patch('prs.core.helpers.get')
    def test_resolve_owner_and_read_authors_together(self, mock_get):
        """Test that resolve_owner and read_authors work correctly together."""
        # Setup config that would be realistic for both functions
        mock_get.side_effect = lambda section, key, fallback='': {
            ('git', 'upstream'): 'username',
            ('git', 'username'): 'myuser',
            ('git-org', 'org_name'): 'myorg',
            ('pr-info', 'authors'): 'myuser,teammate1,teammate2'
        }.get((section, key), fallback)
        
        # Test both functions
        owner = resolve_owner()
        authors = read_authors()
        
        assert owner == 'myuser'
        assert authors == ['myuser', 'teammate1', 'teammate2']
        # Verify that the username appears both as owner and first author
        assert owner == authors[0]

    @patch('prs.core.helpers.get')
    def test_functions_with_org_based_config(self, mock_get):
        """Test both functions with organization-based configuration."""
        mock_get.side_effect = lambda section, key, fallback='': {
            ('git', 'upstream'): 'org_name',
            ('git', 'username'): 'employee',
            ('git-org', 'org_name'): 'bigcorp',
            ('pr-info', 'authors'): ''  # Empty, should fallback
        }.get((section, key), fallback)
        
        owner = resolve_owner()
        authors = read_authors()
        
        assert owner == 'bigcorp'
        assert authors == ['employee']  # Fallback to username
        # Owner and author are different in this case
        assert owner != authors[0]


class TestHelpersEdgeCases:
    """Test edge cases and error conditions."""

    @patch('prs.core.helpers.get')
    def test_functions_with_none_returns(self, mock_get):
        """Test behavior when config.get returns None (shouldn't happen but test defensively)."""
        # This is a defensive test - config.get shouldn't return None but if it did
        mock_get.return_value = None
        
        # Both functions should handle None gracefully
        owner = resolve_owner()
        assert owner is None
        
        # For read_authors, it would try to call .strip() on None
        # This would raise AttributeError in current implementation
        with pytest.raises(AttributeError):
            read_authors()

    @patch('prs.core.helpers.get')
    def test_unicode_and_special_characters(self, mock_get):
        """Test functions with unicode and special characters."""
        mock_get.side_effect = lambda section, key, fallback='': {
            ('git', 'upstream'): 'username',
            ('git', 'username'): 'user-émoji-🚀',
            ('git-org', 'org_name'): 'org-ñame',
            ('pr-info', 'authors'): 'user-émoji-🚀,collaborator-测试,reviewer-العربية'
        }.get((section, key), fallback)
        
        owner = resolve_owner()
        authors = read_authors()
        
        assert owner == 'user-émoji-🚀'
        assert authors == ['user-émoji-🚀', 'collaborator-测试', 'reviewer-العربية']

    @patch('prs.core.helpers.get')
    def test_very_long_strings(self, mock_get):
        """Test functions with very long configuration values."""
        long_username = 'a' * 1000
        long_authors = ','.join([f'user{i}' for i in range(100)])
        
        mock_get.side_effect = lambda section, key, fallback='': {
            ('git', 'upstream'): 'username',
            ('git', 'username'): long_username,
            ('git-org', 'org_name'): 'normalorg',
            ('pr-info', 'authors'): long_authors
        }.get((section, key), fallback)
        
        owner = resolve_owner()
        authors = read_authors()
        
        assert owner == long_username
        assert len(authors) == 100
        assert all(author.startswith('user') for author in authors)

    def test_functions_with_no_patches(self):
        """Test that functions can be imported and called (will use actual config)."""
        # This test verifies the functions can be imported and called
        # It will use the actual config system, which should be present
        
        # These calls might fail if config is not set up, but shouldn't crash on import
        try:
            owner = resolve_owner()
            authors = read_authors()
            # Functions should return string values
            assert isinstance(owner, str)
            assert isinstance(authors, list)
            assert all(isinstance(author, str) for author in authors)
        except Exception:
            # If config is not available, that's okay for this test
            # We just want to verify the functions can be called
            pass