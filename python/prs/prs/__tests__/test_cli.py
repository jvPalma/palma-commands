"""
Unit tests for CLI module.

Tests cover:
- Argument parsing with various combinations
- ColoredHelpFormatter functionality
- CLI flag handling and validation
- Config integration with CLI arguments
- Error handling for invalid arguments
"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

from prs.cli import run_cli, ColoredHelpFormatter


class TestCreateParser:
    """Test argument parser creation and functionality."""

    def test_create_parser_basic(self):
        """Test basic parser creation."""
        parser = create_parser()
        
        assert parser is not None
        assert parser.prog == "prs"

    def test_parser_with_no_arguments(self):
        """Test parser with no arguments uses defaults."""
        parser = create_parser()
        args = parser.parse_args([])
        
        # Check default values
        assert args.state == "open"
        assert args.include_draft is False
        assert args.no_reviewer is False
        assert args.no_reviewed is False
        assert args.version is False

    def test_parser_with_state_argument(self):
        """Test parser handles state argument correctly."""
        parser = create_parser()
        
        # Test valid states
        for state in ["open", "closed", "all"]:
            args = parser.parse_args(["--state", state])
            assert args.state == state

    def test_parser_with_draft_flag(self):
        """Test parser handles --draft flag."""
        parser = create_parser()
        args = parser.parse_args(["--draft"])
        
        assert args.include_draft is True

    def test_parser_with_no_reviewer_flag(self):
        """Test parser handles --no-reviewer flag."""
        parser = create_parser()
        args = parser.parse_args(["--no-reviewer"])
        
        assert args.no_reviewer is True

    def test_parser_with_no_reviewed_flag(self):
        """Test parser handles --no-reviewed flag."""
        parser = create_parser()
        args = parser.parse_args(["--no-reviewed"])
        
        assert args.no_reviewed is True

    def test_parser_with_version_flag(self):
        """Test parser handles --version flag."""
        parser = create_parser()
        
        # Test short version
        args = parser.parse_args(["-v"])
        assert args.version is True
        
        # Test long version
        args = parser.parse_args(["--version"])
        assert args.version is True

    def test_parser_verbosity_arguments(self):
        """Test parser handles verbosity arguments."""
        parser = create_parser()
        
        verbosity_args = [
            ("--author", "author"),
            ("--checks", "checks"),
            ("--reviews", "reviews"),
            ("--labels", "labels"),
            ("--pr-url", "pr_url"),
            ("--branch", "branch")
        ]
        
        for arg_name, attr_name in verbosity_args:
            for level in ["none", "short", "normal", "long"]:
                args = parser.parse_args([arg_name, level])
                assert getattr(args, attr_name) == level

    def test_parser_config_commands(self):
        """Test parser handles config commands."""
        parser = create_parser()
        
        # Test config get
        args = parser.parse_args(["config", "get", "section.key"])
        assert args.command == "config"
        assert args.config_action == "get"
        assert args.config_key == "section.key"
        
        # Test config set
        args = parser.parse_args(["config", "set", "section.key", "value"])
        assert args.command == "config"
        assert args.config_action == "set"
        assert args.config_key == "section.key"
        assert args.config_value == "value"
        
        # Test config all
        args = parser.parse_args(["config", "all"])
        assert args.command == "config"
        assert args.config_action == "all"
        
        # Test config open
        args = parser.parse_args(["config", "open"])
        assert args.command == "config"
        assert args.config_action == "open"

    def test_parser_ignore_command(self):
        """Test parser handles ignore command."""
        parser = create_parser()
        
        # Single PR number
        args = parser.parse_args(["ignore", "123"])
        assert args.command == "ignore"
        assert args.pr_numbers == ["123"]
        
        # Multiple PR numbers
        args = parser.parse_args(["ignore", "123", "456", "789"])
        assert args.command == "ignore"
        assert args.pr_numbers == ["123", "456", "789"]

    def test_parser_combined_arguments(self):
        """Test parser with multiple arguments combined."""
        parser = create_parser()
        args = parser.parse_args([
            "--state", "all",
            "--draft",
            "--no-reviewer",
            "--checks", "long",
            "--reviews", "short"
        ])
        
        assert args.state == "all"
        assert args.include_draft is True
        assert args.no_reviewer is True
        assert args.checks == "long"
        assert args.reviews == "short"

    def test_parser_invalid_state(self):
        """Test parser rejects invalid state values."""
        parser = create_parser()
        
        with pytest.raises(SystemExit):
            parser.parse_args(["--state", "invalid"])

    def test_parser_invalid_verbosity(self):
        """Test parser rejects invalid verbosity levels."""
        parser = create_parser()
        
        with pytest.raises(SystemExit):
            parser.parse_args(["--checks", "invalid"])


class TestColoredHelpFormatter:
    """Test ColoredHelpFormatter functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = create_parser()
        self.formatter = ColoredHelpFormatter("test_prog")

    def test_formatter_initialization(self):
        """Test ColoredHelpFormatter initializes correctly."""
        formatter = ColoredHelpFormatter("test_prog")
        assert formatter is not None

    def test_format_help_contains_colors(self):
        """Test that formatted help contains color codes."""
        help_text = self.parser.format_help()
        
        # Should contain ANSI color codes
        assert "\033[" in help_text

    def test_format_help_structure(self):
        """Test help output has expected structure."""
        help_text = self.parser.format_help()
        
        # Should contain main sections
        assert "usage:" in help_text
        assert "positional arguments:" in help_text
        assert "options:" in help_text

    def test_format_usage(self):
        """Test usage formatting."""
        usage = self.formatter.format_usage("usage", [], [], "")
        assert "usage" in usage

    def test_format_actions_usage(self):
        """Test action usage formatting."""
        # Create a mock action
        action = Mock()
        action.option_strings = ["--test"]
        action.dest = "test"
        action.metavar = None
        action.nargs = None
        
        result = self.formatter._format_actions_usage([action], [])
        assert isinstance(result, str)

    @patch('sys.stdout', new_callable=StringIO)
    def test_help_output_readable(self, mock_stdout):
        """Test that help output is readable (no broken formatting)."""
        try:
            self.parser.parse_args(["--help"])
        except SystemExit:
            pass  # argparse calls sys.exit after printing help
        
        help_output = mock_stdout.getvalue()
        
        # Basic readability checks
        assert len(help_output) > 0
        assert "prs" in help_output
        assert "Pull Request Status" in help_output


class TestMainFunction:
    """Test main function behavior."""

    @patch('prs.cli.handle_version')
    @patch('prs.cli.create_parser')
    def test_main_with_version_flag(self, mock_create_parser, mock_handle_version):
        """Test main function with version flag."""
        mock_parser = Mock()
        mock_args = Mock()
        mock_args.version = True
        mock_parser.parse_args.return_value = mock_args
        mock_create_parser.return_value = mock_parser
        
        with patch('sys.argv', ['prs', '--version']):
            main()
        
        mock_handle_version.assert_called_once()

    @patch('prs.cli.handle_config_command')
    @patch('prs.cli.create_parser')
    def test_main_with_config_command(self, mock_create_parser, mock_handle_config):
        """Test main function with config command."""
        mock_parser = Mock()
        mock_args = Mock()
        mock_args.version = False
        mock_args.command = "config"
        mock_parser.parse_args.return_value = mock_args
        mock_create_parser.return_value = mock_parser
        
        with patch('sys.argv', ['prs', 'config', 'all']):
            main()
        
        mock_handle_config.assert_called_once_with(mock_args)

    @patch('prs.cli.handle_ignore_command')
    @patch('prs.cli.create_parser')
    def test_main_with_ignore_command(self, mock_create_parser, mock_handle_ignore):
        """Test main function with ignore command."""
        mock_parser = Mock()
        mock_args = Mock()
        mock_args.version = False
        mock_args.command = "ignore"
        mock_parser.parse_args.return_value = mock_args
        mock_create_parser.return_value = mock_parser
        
        with patch('sys.argv', ['prs', 'ignore', '123']):
            main()
        
        mock_handle_ignore.assert_called_once_with(mock_args)

    @patch('prs.cli.print_pull_requests')
    @patch('prs.cli.create_parser')
    def test_main_with_no_command(self, mock_create_parser, mock_print_prs):
        """Test main function with no command (default behavior)."""
        mock_parser = Mock()
        mock_args = Mock()
        mock_args.version = False
        mock_args.command = None
        mock_parser.parse_args.return_value = mock_args
        mock_create_parser.return_value = mock_parser
        
        with patch('sys.argv', ['prs']):
            main()
        
        mock_print_prs.assert_called_once_with(mock_args)

    @patch('prs.cli.create_parser')
    def test_main_handles_keyboard_interrupt(self, mock_create_parser):
        """Test main function handles KeyboardInterrupt gracefully."""
        mock_parser = Mock()
        mock_parser.parse_args.side_effect = KeyboardInterrupt()
        mock_create_parser.return_value = mock_parser
        
        with patch('sys.argv', ['prs']):
            with patch('sys.exit') as mock_exit:
                main()
                mock_exit.assert_called_once_with(1)

    @patch('prs.cli.create_parser')
    def test_main_handles_general_exception(self, mock_create_parser):
        """Test main function handles general exceptions."""
        mock_parser = Mock()
        mock_parser.parse_args.side_effect = Exception("Test error")
        mock_create_parser.return_value = mock_parser
        
        with patch('sys.argv', ['prs']):
            with patch('sys.exit') as mock_exit:
                with patch('builtins.print') as mock_print:
                    main()
                    
                    mock_print.assert_called()
                    mock_exit.assert_called_once_with(1)


class TestCommandHandlers:
    """Test command handler functions."""

    @patch('prs.cli.print')
    def test_handle_version(self, mock_print):
        """Test version handler."""
        from prs.cli import handle_version
        
        handle_version()
        
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "prs version" in call_args

    @patch('prs.config.get')
    @patch('prs.cli.print')
    def test_handle_config_get(self, mock_print, mock_config_get):
        """Test config get handler."""
        from prs.cli import handle_config_command
        
        mock_config_get.return_value = "test_value"
        args = Mock()
        args.config_action = "get"
        args.config_key = "section.key"
        
        handle_config_command(args)
        
        mock_print.assert_called_with("test_value")

    @patch('prs.config.set')
    @patch('prs.cli.print')
    def test_handle_config_set(self, mock_print, mock_config_set):
        """Test config set handler."""
        from prs.cli import handle_config_command
        
        args = Mock()
        args.config_action = "set"
        args.config_key = "section.key"
        args.config_value = "new_value"
        
        handle_config_command(args)
        
        section, key = args.config_key.split(".", 1)
        mock_config_set.assert_called_with(section, key, "new_value")
        mock_print.assert_called_with("Configuration updated")

    @patch('prs.config.print_all_config')
    def test_handle_config_all(self, mock_print_all):
        """Test config all handler."""
        from prs.cli import handle_config_command
        
        args = Mock()
        args.config_action = "all"
        
        handle_config_command(args)
        
        mock_print_all.assert_called_once()

    @patch('prs.config.open_config_file')
    def test_handle_config_open(self, mock_open_config):
        """Test config open handler."""
        from prs.cli import handle_config_command
        
        args = Mock()
        args.config_action = "open"
        
        handle_config_command(args)
        
        mock_open_config.assert_called_once()

    @patch('prs.config.add_ignored_prs')
    @patch('prs.cli.print')
    def test_handle_ignore_command(self, mock_print, mock_add_ignored):
        """Test ignore command handler."""
        from prs.cli import handle_ignore_command
        
        args = Mock()
        args.pr_numbers = ["123", "456", "789"]
        
        handle_ignore_command(args)
        
        mock_add_ignored.assert_called_with([123, 456, 789])
        mock_print.assert_called()

    @patch('prs.config.add_ignored_prs')
    @patch('prs.cli.print')
    def test_handle_ignore_invalid_numbers(self, mock_print, mock_add_ignored):
        """Test ignore command with invalid PR numbers."""
        from prs.cli import handle_ignore_command
        
        args = Mock()
        args.pr_numbers = ["123", "invalid", "456"]
        
        handle_ignore_command(args)
        
        # Should only add valid numbers
        mock_add_ignored.assert_called_with([123, 456])


class TestArgumentValidation:
    """Test argument validation and error handling."""

    def test_config_get_requires_key(self):
        """Test config get command requires a key."""
        parser = create_parser()
        
        with pytest.raises(SystemExit):
            parser.parse_args(["config", "get"])

    def test_config_set_requires_key_and_value(self):
        """Test config set command requires key and value."""
        parser = create_parser()
        
        # Missing value
        with pytest.raises(SystemExit):
            parser.parse_args(["config", "set", "section.key"])

    def test_ignore_requires_pr_numbers(self):
        """Test ignore command requires PR numbers."""
        parser = create_parser()
        
        with pytest.raises(SystemExit):
            parser.parse_args(["ignore"])

    def test_verbosity_choices_validation(self):
        """Test verbosity level validation."""
        parser = create_parser()
        
        valid_levels = ["none", "short", "normal", "long"]
        
        for arg in ["--author", "--checks", "--reviews", "--labels", "--pr-url", "--branch"]:
            # Test valid levels
            for level in valid_levels:
                args = parser.parse_args([arg, level])
                assert getattr(args, arg.replace("--", "").replace("-", "_")) == level
            
            # Test invalid level
            with pytest.raises(SystemExit):
                parser.parse_args([arg, "invalid"])

    def test_state_choices_validation(self):
        """Test state argument validation."""
        parser = create_parser()
        
        valid_states = ["open", "closed", "all"]
        
        # Test valid states
        for state in valid_states:
            args = parser.parse_args(["--state", state])
            assert args.state == state
        
        # Test invalid state
        with pytest.raises(SystemExit):
            parser.parse_args(["--state", "invalid"])


class TestFilterGeneration:
    """Test filter dictionary generation from arguments."""

    def test_build_filters_from_args_basic(self):
        """Test basic filter generation."""
        from prs.cli import build_filters_from_args
        
        args = Mock()
        args.state = "open"
        args.include_draft = False
        args.no_reviewer = False
        args.no_reviewed = False
        
        filters = build_filters_from_args(args)
        
        assert filters["state"] == "open"
        assert filters["include_draft"] is False
        assert filters["no_reviewer"] is False
        assert filters["no_reviewed"] is False

    def test_build_filters_from_args_all_flags(self):
        """Test filter generation with all flags set."""
        from prs.cli import build_filters_from_args
        
        args = Mock()
        args.state = "all"
        args.include_draft = True
        args.no_reviewer = True
        args.no_reviewed = True
        
        filters = build_filters_from_args(args)
        
        assert filters["state"] == "all"
        assert filters["include_draft"] is True
        assert filters["no_reviewer"] is True
        assert filters["no_reviewed"] is True

    def test_build_filters_maintains_type(self):
        """Test that filter values maintain correct types."""
        from prs.cli import build_filters_from_args
        
        args = Mock()
        args.state = "closed"
        args.include_draft = True
        args.no_reviewer = False
        args.no_reviewed = True
        
        filters = build_filters_from_args(args)
        
        assert isinstance(filters["state"], str)
        assert isinstance(filters["include_draft"], bool)
        assert isinstance(filters["no_reviewer"], bool)
        assert isinstance(filters["no_reviewed"], bool)


class TestCLIIntegration:
    """Test CLI integration with other modules."""

    @patch('prs.core.printPullRequests.print_pull_requests')
    def test_cli_calls_print_pull_requests(self, mock_print_prs):
        """Test CLI calls print_pull_requests with correct arguments."""
        from prs.cli import print_pull_requests
        
        args = Mock()
        args.state = "open"
        args.include_draft = False
        args.no_reviewer = False
        args.no_reviewed = False
        args.author = "normal"
        args.checks = "short"
        args.reviews = "long"
        args.labels = "none"
        args.pr_url = "normal"
        args.branch = "short"
        
        print_pull_requests(args)
        
        mock_print_prs.assert_called_once()

    @patch('sys.argv', ['prs', '--help'])
    def test_help_formatting_does_not_crash(self):
        """Test that help formatting doesn't crash."""
        parser = create_parser()
        
        try:
            parser.parse_args()
        except SystemExit as e:
            # Help should exit with code 0
            assert e.code == 0


class TestErrorHandling:
    """Test error handling in CLI module."""

    def test_parser_handles_empty_args(self):
        """Test parser handles empty argument list."""
        parser = create_parser()
        args = parser.parse_args([])
        
        # Should not crash and should have defaults
        assert args.state == "open"
        assert args.include_draft is False

    @patch('prs.cli.create_parser')
    def test_main_catches_parser_errors(self, mock_create_parser):
        """Test main function catches parser errors."""
        mock_parser = Mock()
        mock_parser.parse_args.side_effect = SystemExit(2)
        mock_create_parser.return_value = mock_parser
        
        with patch('sys.argv', ['prs', '--invalid']):
            with patch('sys.exit') as mock_exit:
                main()
                # SystemExit from argparse should be re-raised
                mock_exit.assert_called()

    def test_invalid_config_key_format(self):
        """Test handling of invalid config key format."""
        from prs.cli import handle_config_command
        
        args = Mock()
        args.config_action = "get"
        args.config_key = "invalid_key_format"  # Missing dot separator
        
        with patch('prs.cli.print') as mock_print:
            handle_config_command(args)
            # Should handle gracefully, possibly with error message
            mock_print.assert_called()


class TestHelpText:
    """Test help text content and formatting."""

    def test_help_contains_all_commands(self):
        """Test help text contains all available commands."""
        parser = create_parser()
        help_text = parser.format_help()
        
        # Should mention main commands
        assert "config" in help_text
        assert "ignore" in help_text

    def test_help_contains_verbosity_info(self):
        """Test help text explains verbosity levels."""
        parser = create_parser()
        help_text = parser.format_help()
        
        # Should explain verbosity levels
        assert "none" in help_text
        assert "short" in help_text
        assert "normal" in help_text
        assert "long" in help_text

    def test_help_formatting_preserves_structure(self):
        """Test help formatting preserves logical structure."""
        parser = create_parser()
        help_text = parser.format_help()
        
        # Should have proper sections in order
        usage_pos = help_text.find("usage:")
        positional_pos = help_text.find("positional arguments:")
        options_pos = help_text.find("options:")
        
        assert usage_pos < positional_pos < options_pos

    def test_color_codes_in_help(self):
        """Test that color codes are present in help text."""
        parser = create_parser()
        help_text = parser.format_help()
        
        # Should contain ANSI escape sequences
        assert "\033[" in help_text
        
        # Should contain reset codes
        assert "\033[0m" in help_text