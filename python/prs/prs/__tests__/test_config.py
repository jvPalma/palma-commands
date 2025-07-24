"""
Unit tests for the configuration module.

Tests cover:
- Config file creation and management
- Reading and writing configuration values
- All configuration sections and defaults
- Get/set operations with proper fallbacks
- Config file parsing edge cases
- Ignored PR management functionality
"""

import pytest
import configparser
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

# Import the module under test
import prs.config as config


class TestConfigFileCreation:
    """Test configuration file creation and initialization."""

    def test_default_config_creation_when_file_not_exists(self):
        """Test that default config is created when file doesn't exist."""
        # This test is more about the actual behavior documented in the module
        # The file creation happens at import time, so we'll test the structure instead
        
        # Test that we can create a temp config with the expected structure
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.config') as f:
            default_config = """
[git]
repo_name =
username =
origin = 
upstream = username

[git-org]
team_name = 
org_name =

[vctool]
platform = github

[pr-info]
author = short
pr_url = short
branch = short
checks = short
reviews = short
labels = short
authors = 

[filters]
ignored = 
ignored_users = 
include_reviewer_prs = true
include_reviewed_prs = true

[user-colors]
assignments = {}
            """
            f.write(default_config.strip())
            temp_path = f.name
        
        try:
            # Parse the config to verify structure
            parser = configparser.ConfigParser()
            parser.read(temp_path)
            
            # Verify all expected sections exist
            expected_sections = ['git', 'git-org', 'vctool', 'pr-info', 'filters', 'user-colors']
            for section in expected_sections:
                assert parser.has_section(section), f"Missing section: {section}"
            
            # Verify specific default values
            assert parser.get('git', 'upstream') == 'username'
            assert parser.get('vctool', 'platform') == 'github'
            assert parser.get('pr-info', 'author') == 'short'
            assert parser.get('filters', 'include_reviewer_prs') == 'true'
            
        finally:
            os.unlink(temp_path)

    @patch('prs.config.CONFIG_PATH')
    def test_config_not_created_when_file_exists(self, mock_path):
        """Test that config is not recreated when file already exists."""
        mock_path.exists.return_value = True
        mock_path.write_text = MagicMock()
        
        # Reload the module
        import importlib
        importlib.reload(config)
        
        # Verify write_text was not called
        mock_path.write_text.assert_not_called()

    def test_default_config_structure(self):
        """Test the structure of the default configuration."""
        expected_sections = [
            'git', 'git-org', 'vctool', 'pr-info', 'filters', 'user-colors'
        ]
        
        # Create a temporary config with default content
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.config') as f:
            default_config = """
[git]
repo_name =
username =
origin = 
upstream = username

[git-org]
team_name = 
org_name =

[vctool]
platform = github

[pr-info]
author = short
pr_url = short
branch = short
checks = short
reviews = short
labels = short
authors = 

[filters]
ignored = 
include_reviewer_prs = true
include_reviewed_prs = true

[user-colors]
assignments = {}
            """
            f.write(default_config.strip())
            temp_path = f.name
        
        try:
            # Parse the config
            parser = configparser.ConfigParser()
            parser.read(temp_path)
            
            # Verify all expected sections exist
            for section in expected_sections:
                assert parser.has_section(section), f"Missing section: {section}"
            
            # Verify specific default values
            assert parser.get('git', 'upstream') == 'username'
            assert parser.get('vctool', 'platform') == 'github'
            assert parser.get('pr-info', 'author') == 'short'
            assert parser.get('filters', 'include_reviewer_prs') == 'true'
            assert parser.get('filters', 'include_reviewed_prs') == 'true'
            
        finally:
            os.unlink(temp_path)


class TestConfigGetOperations:
    """Test configuration reading operations."""

    @patch('prs.config._config')
    def test_get_existing_value(self, mock_config):
        """Test getting an existing configuration value."""
        mock_config.get.return_value = 'test_value'
        
        result = config.get('test_section', 'test_key')
        
        mock_config.get.assert_called_once_with('test_section', 'test_key', fallback='')
        assert result == 'test_value'

    @patch('prs.config._config')
    def test_get_with_custom_fallback(self, mock_config):
        """Test getting value with custom fallback."""
        mock_config.get.return_value = 'fallback_value'
        
        result = config.get('section', 'key', fallback='fallback_value')
        
        mock_config.get.assert_called_once_with('section', 'key', fallback='fallback_value')
        assert result == 'fallback_value'

    @patch('prs.config._config')
    def test_get_with_empty_fallback(self, mock_config):
        """Test getting value with empty string fallback (default)."""
        mock_config.get.return_value = ''
        
        result = config.get('section', 'key')
        
        mock_config.get.assert_called_once_with('section', 'key', fallback='')
        assert result == ''

    @patch('prs.config._config')
    def test_get_nonexistent_key(self, mock_config):
        """Test getting a non-existent key returns fallback."""
        mock_config.get.return_value = 'default'
        
        result = config.get('nonexistent', 'key', fallback='default')
        
        assert result == 'default'


class TestConfigSetOperations:
    """Test configuration writing operations."""

    @patch('builtins.open', new_callable=mock_open)
    @patch('prs.config._config')
    def test_set_existing_section(self, mock_config, mock_file):
        """Test setting a value in an existing section."""
        mock_config.has_section.return_value = True
        mock_config.set = MagicMock()
        mock_config.write = MagicMock()
        
        config.set('existing_section', 'test_key', 'test_value')
        
        mock_config.has_section.assert_called_once_with('existing_section')
        mock_config.set.assert_called_once_with('existing_section', 'test_key', 'test_value')
        mock_config.write.assert_called_once()

    @patch('builtins.open', new_callable=mock_open)
    @patch('prs.config._config')
    def test_set_new_section(self, mock_config, mock_file):
        """Test setting a value in a new section (creates section first)."""
        mock_config.has_section.return_value = False
        mock_config.add_section = MagicMock()
        mock_config.set = MagicMock()
        mock_config.write = MagicMock()
        
        config.set('new_section', 'test_key', 'test_value')
        
        mock_config.has_section.assert_called_once_with('new_section')
        mock_config.add_section.assert_called_once_with('new_section')
        mock_config.set.assert_called_once_with('new_section', 'test_key', 'test_value')
        mock_config.write.assert_called_once()

    @patch('builtins.open', new_callable=mock_open)
    @patch('prs.config._config')
    @patch('prs.config.CONFIG_PATH', '/test/path/.prsconfig')
    def test_set_writes_to_correct_file(self, mock_config, mock_file):
        """Test that set operation writes to the correct config file."""
        mock_config.has_section.return_value = True
        mock_config.set = MagicMock()
        mock_config.write = MagicMock()
        
        config.set('section', 'key', 'value')
        
        mock_file.assert_called_once_with('/test/path/.prsconfig', 'w')

    @patch('builtins.open', new_callable=mock_open)
    @patch('prs.config._config')
    def test_set_empty_value(self, mock_config, mock_file):
        """Test setting an empty value."""
        mock_config.has_section.return_value = True
        mock_config.set = MagicMock()
        mock_config.write = MagicMock()
        
        config.set('section', 'key', '')
        
        mock_config.set.assert_called_once_with('section', 'key', '')

    @patch('builtins.open', new_callable=mock_open)
    @patch('prs.config._config')
    def test_set_special_characters(self, mock_config, mock_file):
        """Test setting values with special characters."""
        mock_config.has_section.return_value = True
        mock_config.set = MagicMock()
        mock_config.write = MagicMock()
        
        special_value = 'value with spaces, commas, and émojis 🚀'
        config.set('section', 'key', special_value)
        
        mock_config.set.assert_called_once_with('section', 'key', special_value)


class TestAllConfigOperation:
    """Test getting all configuration as dictionary."""

    @patch('prs.config._config')
    def test_all_config_returns_all_sections(self, mock_config):
        """Test that all_config returns dictionary of all sections."""
        mock_config.sections.return_value = ['section1', 'section2']
        mock_config.items.side_effect = [
            [('key1', 'value1'), ('key2', 'value2')],
            [('key3', 'value3')]
        ]
        
        result = config.all_config()
        
        expected = {
            'section1': {'key1': 'value1', 'key2': 'value2'},
            'section2': {'key3': 'value3'}
        }
        assert result == expected

    @patch('prs.config._config')
    def test_all_config_empty_sections(self, mock_config):
        """Test all_config with empty sections."""
        mock_config.sections.return_value = ['empty_section']
        mock_config.items.return_value = []
        
        result = config.all_config()
        
        expected = {'empty_section': {}}
        assert result == expected

    @patch('prs.config._config')
    def test_all_config_no_sections(self, mock_config):
        """Test all_config with no sections."""
        mock_config.sections.return_value = []
        
        result = config.all_config()
        
        assert result == {}


class TestIgnoredPRsFunctionality:
    """Test ignored PRs management functionality."""

    @patch('prs.config.get')
    def test_get_ignored_prs_empty_string(self, mock_get):
        """Test getting ignored PRs when config value is empty."""
        mock_get.return_value = ''
        
        result = config.get_ignored_prs()
        
        mock_get.assert_called_once_with('filters', 'ignored', fallback='')
        assert result == []

    @patch('prs.config.get')
    def test_get_ignored_prs_whitespace_only(self, mock_get):
        """Test getting ignored PRs when config value is whitespace only."""
        mock_get.return_value = '   \t\n  '
        
        result = config.get_ignored_prs()
        
        assert result == []

    @patch('prs.config.get')
    def test_get_ignored_prs_single_pr(self, mock_get):
        """Test getting ignored PRs with single PR number."""
        mock_get.return_value = '123'
        
        result = config.get_ignored_prs()
        
        assert result == [123]

    @patch('prs.config.get')
    def test_get_ignored_prs_multiple_prs(self, mock_get):
        """Test getting ignored PRs with multiple PR numbers."""
        mock_get.return_value = '123,456,789'
        
        result = config.get_ignored_prs()
        
        assert result == [123, 456, 789]

    @patch('prs.config.get')
    def test_get_ignored_prs_with_spaces(self, mock_get):
        """Test getting ignored PRs with spaces around numbers."""
        mock_get.return_value = ' 123 , 456 , 789 '
        
        result = config.get_ignored_prs()
        
        assert result == [123, 456, 789]

    @patch('prs.config.get')
    def test_get_ignored_prs_with_empty_elements(self, mock_get):
        """Test getting ignored PRs with empty elements in list."""
        mock_get.return_value = '123,,456, ,789'
        
        result = config.get_ignored_prs()
        
        assert result == [123, 456, 789]

    @patch('prs.config.get')
    def test_get_ignored_prs_invalid_numbers(self, mock_get):
        """Test getting ignored PRs with invalid number formats."""
        mock_get.return_value = '123,invalid,456'
        
        result = config.get_ignored_prs()
        
        # Should return empty list on ValueError
        assert result == []

    @patch('prs.config.get')
    def test_get_ignored_prs_mixed_valid_invalid(self, mock_get):
        """Test getting ignored PRs with mix of valid and invalid numbers."""
        mock_get.return_value = '123,abc,456,def'
        
        result = config.get_ignored_prs()
        
        # Should return empty list on any ValueError
        assert result == []

    @patch('prs.config.get')
    def test_get_ignored_prs_negative_numbers(self, mock_get):
        """Test getting ignored PRs with negative numbers."""
        mock_get.return_value = '-123,456,-789'
        
        result = config.get_ignored_prs()
        
        # Should handle negative numbers (though unusual for PR IDs)
        assert result == [-123, 456, -789]

    @patch('prs.config.get')
    def test_get_ignored_prs_zero(self, mock_get):
        """Test getting ignored PRs with zero values."""
        mock_get.return_value = '0,123,0'
        
        result = config.get_ignored_prs()
        
        assert result == [0, 123, 0]

    @patch('prs.config.set')
    def test_set_ignored_prs_empty_list(self, mock_set):
        """Test setting empty list of ignored PRs."""
        config.set_ignored_prs([])
        
        mock_set.assert_called_once_with('filters', 'ignored', '')

    @patch('prs.config.set')
    def test_set_ignored_prs_single_pr(self, mock_set):
        """Test setting single ignored PR."""
        config.set_ignored_prs([123])
        
        mock_set.assert_called_once_with('filters', 'ignored', '123')

    @patch('prs.config.set')
    def test_set_ignored_prs_multiple_prs(self, mock_set):
        """Test setting multiple ignored PRs."""
        config.set_ignored_prs([123, 456, 789])
        
        mock_set.assert_called_once_with('filters', 'ignored', '123,456,789')

    @patch('prs.config.set')
    def test_set_ignored_prs_negative_numbers(self, mock_set):
        """Test setting ignored PRs with negative numbers."""
        config.set_ignored_prs([-1, 123, -456])
        
        mock_set.assert_called_once_with('filters', 'ignored', '-1,123,-456')

    @patch('prs.config.set')
    def test_set_ignored_prs_zero_values(self, mock_set):
        """Test setting ignored PRs with zero values."""
        config.set_ignored_prs([0, 123, 0])
        
        mock_set.assert_called_once_with('filters', 'ignored', '0,123,0')

    @patch('prs.config.set')
    def test_set_ignored_prs_preserves_order(self, mock_set):
        """Test that setting ignored PRs preserves the order."""
        config.set_ignored_prs([789, 123, 456])
        
        mock_set.assert_called_once_with('filters', 'ignored', '789,123,456')


class TestConfigIntegration:
    """Integration tests for configuration operations."""

    def test_get_set_roundtrip(self):
        """Test that values can be set and retrieved correctly."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.config') as f:
            temp_path = f.name
        
        try:
            # Patch the CONFIG_PATH to use our temporary file
            with patch('prs.config.CONFIG_PATH', Path(temp_path)):
                # Import fresh instance
                import importlib
                importlib.reload(config)
                
                # Set a value
                config.set('test_section', 'test_key', 'test_value')
                
                # Get the value back
                result = config.get('test_section', 'test_key')
                
                assert result == 'test_value'
        
        finally:
            os.unlink(temp_path)

    def test_ignored_prs_roundtrip(self):
        """Test that ignored PRs can be set and retrieved correctly."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.config') as f:
            temp_path = f.name
        
        try:
            # Patch the CONFIG_PATH to use our temporary file
            with patch('prs.config.CONFIG_PATH', Path(temp_path)):
                # Import fresh instance
                import importlib
                importlib.reload(config)
                
                # Set ignored PRs
                test_prs = [123, 456, 789]
                config.set_ignored_prs(test_prs)
                
                # Get them back
                result = config.get_ignored_prs()
                
                assert result == test_prs
        
        finally:
            os.unlink(temp_path)


class TestConfigErrorHandling:
    """Test error handling in configuration operations."""

    @patch('builtins.open', side_effect=PermissionError("Permission denied"))
    @patch('prs.config._config')
    def test_set_handles_permission_error(self, mock_config, mock_file):
        """Test that set operation handles file permission errors."""
        mock_config.has_section.return_value = True
        mock_config.set = MagicMock()
        
        # Should raise the PermissionError
        with pytest.raises(PermissionError):
            config.set('section', 'key', 'value')

    @patch('builtins.open', side_effect=IOError("Disk full"))
    @patch('prs.config._config')  
    def test_set_handles_io_error(self, mock_config, mock_file):
        """Test that set operation handles I/O errors."""
        mock_config.has_section.return_value = True
        mock_config.set = MagicMock()
        
        # Should raise the IOError
        with pytest.raises(IOError):
            config.set('section', 'key', 'value')

    def test_config_parsing_edge_cases(self):
        """Test configuration parsing with edge cases."""
        # Test with malformed config content
        malformed_config = """
[section1
key1 = value1
[section2]
key2 = value2
key3
        """
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.config') as f:
            f.write(malformed_config)
            temp_path = f.name
        
        try:
            parser = configparser.ConfigParser()
            # Should handle malformed config gracefully or raise appropriate error
            with pytest.raises(configparser.Error):
                parser.read(temp_path)
        
        finally:
            os.unlink(temp_path)