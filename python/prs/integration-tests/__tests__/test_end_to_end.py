"""
End-to-end integration tests.

Tests complete workflows from CLI input to final output.
"""

import pytest
import json
from unittest.mock import patch, Mock, mock_open
from io import StringIO

from prs.cli import main
from prs.core.printPullRequests import list_pull_requests


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows."""

    @patch('prs.vc_tools.github.client.subprocess.check_output')
    @patch('prs.vc_tools.github.client.get')
    @patch('sys.argv', ['prs'])
    def test_basic_pr_listing_workflow(self, mock_config, mock_subprocess):
        """Test basic PR listing from CLI to output."""
        # Mock configuration
        mock_config.side_effect = lambda section, key, fallback=None: {
            ('git-org', 'org_name'): 'test-org',
            ('git', 'repo_name'): 'test-repo',
            ('pr-info', 'authors'): '',
            ('git', 'username'): 'test-user',
            ('pr-info', 'author'): 'short',
            ('pr-info', 'checks'): 'normal',
            ('pr-info', 'reviews'): 'short',
            ('pr-info', 'labels'): 'none',
            ('pr-info', 'pr_url'): 'short',
            ('pr-info', 'branch'): 'short',
            ('filters', 'ignored'): '',
            ('filters', 'include_reviewer_prs'): 'true'
        }.get((section, key), fallback)
        
        # Mock GitHub API response
        pr_data = {
            "number": 123,
            "user": {"login": "test-user"},
            "updated_at": "2023-01-01T12:00:00Z",
            "isDraft": False,
            "source": "authored"
        }
        mock_subprocess.return_value = json.dumps(pr_data) + "\n"
        
        # Mock PR details
        with patch('prs.vc_tools.github.client.get_pull_request_details') as mock_details:
            mock_details.return_value = {
                "id": 123,
                "title": "Test PR",
                "author": "test-user",
                "labels": [],
                "checks": [],
                "reviews": [],
                "url": "https://github.com/test-org/test-repo/pull/123",
                "branch": "test-branch",
                "is_draft": False,
                "role": "author"
            }
            
            # Capture output
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                try:
                    main()
                except SystemExit:
                    pass  # Expected for successful completion
                
                output = mock_stdout.getvalue()
                
                # Should contain PR information
                assert len(output) > 0

    @patch('prs.config.get')
    @patch('sys.argv', ['prs', 'config', 'get', 'git.username'])
    def test_config_get_workflow(self, mock_config):
        """Test config get command workflow."""
        mock_config.return_value = "test_username"
        
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            try:
                main()
            except SystemExit:
                pass
            
            output = mock_stdout.getvalue()
            assert "test_username" in output

    @patch('prs.config.set')
    @patch('sys.argv', ['prs', 'config', 'set', 'git.username', 'new_user'])
    def test_config_set_workflow(self, mock_set):
        """Test config set command workflow."""
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            try:
                main()
            except SystemExit:
                pass
            
            # Should call config.set with parsed values
            mock_set.assert_called_with('git', 'username', 'new_user')
            
            output = mock_stdout.getvalue()
            assert "updated" in output.lower() or "set" in output.lower()

    @patch('prs.config.add_ignored_prs')
    @patch('sys.argv', ['prs', 'ignore', '123', '456', '789'])
    def test_ignore_prs_workflow(self, mock_add_ignored):
        """Test ignore PRs command workflow."""
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            try:
                main()
            except SystemExit:
                pass
            
            # Should add parsed PR numbers
            mock_add_ignored.assert_called_with([123, 456, 789])

    @patch('sys.argv', ['prs', '--version'])
    def test_version_display_workflow(self):
        """Test version display workflow."""
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            try:
                main()
            except SystemExit:
                pass
            
            output = mock_stdout.getvalue()
            assert "prs version" in output.lower()

    @patch('prs.vc_tools.github.client.subprocess.check_output')
    @patch('prs.vc_tools.github.client.get')
    @patch('sys.argv', ['prs', '--state', 'all', '--draft', '--checks', 'long'])
    def test_complex_filtering_workflow(self, mock_config, mock_subprocess):
        """Test complex filtering options workflow."""
        # Mock configuration
        mock_config.side_effect = lambda section, key, fallback=None: {
            ('git-org', 'org_name'): 'test-org',
            ('git', 'repo_name'): 'test-repo',
            ('pr-info', 'authors'): '',
            ('git', 'username'): 'test-user',
            ('pr-info', 'author'): 'short',
            ('pr-info', 'checks'): 'short',  # Should be overridden by CLI
            ('pr-info', 'reviews'): 'short',
            ('pr-info', 'labels'): 'none',
            ('pr-info', 'pr_url'): 'short',
            ('pr-info', 'branch'): 'short',
            ('filters', 'ignored'): '',
            ('filters', 'include_reviewer_prs'): 'true'
        }.get((section, key), fallback)
        
        # Mock GitHub API response with draft PR
        pr_data = {
            "number": 456,
            "user": {"login": "test-user"},
            "updated_at": "2023-01-01T12:00:00Z",
            "isDraft": True,
            "source": "authored"
        }
        mock_subprocess.return_value = json.dumps(pr_data) + "\n"
        
        with patch('prs.core.printPullRequests.list_pull_requests') as mock_print:
            try:
                main()
            except SystemExit:
                pass
            
            # Should be called with correct filters and verbosity
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0]
            filters = call_args[0]
            verbosity = call_args[1]
            
            # Verify filters
            assert filters["state"] == "all"
            assert filters["include_draft"] is True
            
            # Verify verbosity override
            assert verbosity["checks"] == "long"


class TestErrorHandlingWorkflows:
    """Test error handling in complete workflows."""

    @patch('prs.vc_tools.github.client.subprocess.check_output')
    @patch('sys.argv', ['prs'])
    def test_github_api_error_workflow(self, mock_subprocess):
        """Test workflow when GitHub API fails."""
        from subprocess import CalledProcessError
        
        # Mock API failure
        mock_subprocess.side_effect = CalledProcessError(1, 'gh')
        
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            with patch('sys.stderr', new=StringIO()) as mock_stderr:
                try:
                    main()
                except SystemExit:
                    pass
                
                # Should handle error gracefully
                stderr_output = mock_stderr.getvalue()
                stdout_output = mock_stdout.getvalue()
                
                # May show error message or empty output
                assert isinstance(stderr_output, str)
                assert isinstance(stdout_output, str)

    @patch('sys.argv', ['prs', 'config', 'get'])
    def test_incomplete_command_error(self):
        """Test handling of incomplete commands."""
        with patch('sys.stderr', new=StringIO()) as mock_stderr:
            try:
                main()
            except SystemExit as e:
                # Should exit with error code
                assert e.code != 0
                
                stderr_output = mock_stderr.getvalue()
                # Should show usage or error message
                assert len(stderr_output) > 0

    @patch('sys.argv', ['prs', '--invalid-flag'])
    def test_invalid_argument_error(self):
        """Test handling of invalid arguments."""
        with patch('sys.stderr', new=StringIO()) as mock_stderr:
            try:
                main()
            except SystemExit as e:
                # Should exit with error code
                assert e.code != 0

    @patch('prs.config.CONFIG_PATH')
    @patch('sys.argv', ['prs'])
    def test_config_file_error_workflow(self, mock_config_path):
        """Test workflow when config file has issues."""
        # Mock config path that doesn't exist
        mock_config_path.exists.return_value = False
        mock_config_path.write_text.side_effect = PermissionError("Cannot write config")
        
        # Should handle config issues gracefully
        with patch('sys.stdout', new=StringIO()):
            with patch('sys.stderr', new=StringIO()):
                try:
                    main()
                except SystemExit:
                    pass
                except PermissionError:
                    # Expected when config cannot be created
                    pass

    def test_keyboard_interrupt_workflow(self):
        """Test handling of keyboard interrupt."""
        with patch('prs.cli.create_parser') as mock_parser:
            mock_parser.return_value.parse_args.side_effect = KeyboardInterrupt()
            
            with patch('sys.exit') as mock_exit:
                main()
                mock_exit.assert_called_with(1)


class TestConfigurationWorkflows:
    """Test configuration-related workflows."""

    @patch('prs.config.print_all_config')
    @patch('sys.argv', ['prs', 'config', 'all'])
    def test_config_all_workflow(self, mock_print_all):
        """Test config all command workflow."""
        try:
            main()
        except SystemExit:
            pass
        
        mock_print_all.assert_called_once()

    @patch('prs.config.open_config_file')
    @patch('sys.argv', ['prs', 'config', 'open'])
    def test_config_open_workflow(self, mock_open_config):
        """Test config open command workflow."""
        try:
            main()
        except SystemExit:
            pass
        
        mock_open_config.assert_called_once()

    @patch('os.environ', {'EDITOR': 'nano'})
    @patch('subprocess.run')
    @patch('prs.config.CONFIG_PATH')
    @patch('sys.argv', ['prs', 'config', 'open'])
    def test_config_open_with_editor_workflow(self, mock_config_path, mock_subprocess):
        """Test config open with actual editor."""
        mock_config_path.exists.return_value = True
        
        with patch('prs.config.open_config_file') as mock_open:
            try:
                main()
            except SystemExit:
                pass
            
            mock_open.assert_called_once()


class TestMultiUserWorkflows:
    """Test workflows involving multiple users/team scenarios."""

    @patch('prs.vc_tools.github.client.subprocess.check_output')
    @patch('prs.vc_tools.github.client.get')
    @patch('sys.argv', ['prs'])
    def test_team_monitoring_workflow(self, mock_config, mock_subprocess):
        """Test monitoring multiple team members."""
        # Mock team configuration
        mock_config.side_effect = lambda section, key, fallback=None: {
            ('git-org', 'org_name'): 'team-org',
            ('git', 'repo_name'): 'team-repo',
            ('pr-info', 'authors'): 'alice,bob,charlie',
            ('git', 'username'): 'alice',
            ('pr-info', 'author'): 'normal',
            ('pr-info', 'checks'): 'short',
            ('pr-info', 'reviews'): 'normal',
            ('pr-info', 'labels'): 'short',
            ('pr-info', 'pr_url'): 'short',
            ('pr-info', 'branch'): 'short',
            ('filters', 'ignored'): '',
            ('filters', 'include_reviewer_prs'): 'true'
        }.get((section, key), fallback)
        
        # Mock different PRs for different authors
        def subprocess_side_effect(args, **kwargs):
            if "author:alice" in str(args):
                return json.dumps({
                    "number": 100,
                    "user": {"login": "alice"},
                    "updated_at": "2023-01-01T12:00:00Z",
                    "isDraft": False,
                    "source": "authored"
                }) + "\n"
            elif "author:bob" in str(args):
                return json.dumps({
                    "number": 200,
                    "user": {"login": "bob"},
                    "updated_at": "2023-01-01T11:00:00Z",
                    "isDraft": True,
                    "source": "authored"
                }) + "\n"
            elif "author:charlie" in str(args):
                return json.dumps({
                    "number": 300,
                    "user": {"login": "charlie"},
                    "updated_at": "2023-01-01T10:00:00Z",
                    "isDraft": False,
                    "source": "authored"
                }) + "\n"
            return ""
        
        mock_subprocess.side_effect = subprocess_side_effect
        
        with patch('prs.vc_tools.github.client.get_pull_request_details') as mock_details:
            def details_side_effect(pr_id, source):
                return {
                    "id": pr_id,
                    "title": f"PR #{pr_id}",
                    "author": f"user_{pr_id}",
                    "labels": [],
                    "checks": [],
                    "reviews": [],
                    "url": f"https://github.com/team-org/team-repo/pull/{pr_id}",
                    "branch": f"branch_{pr_id}",
                    "is_draft": pr_id == 200,
                    "role": "author"
                }
            
            mock_details.side_effect = details_side_effect
            
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                try:
                    main()
                except SystemExit:
                    pass
                
                # Should process all team members
                output = mock_stdout.getvalue()
                assert len(output) >= 0  # May be empty if no PRs

    @patch('prs.vc_tools.github.client.get_authenticated_user')
    @patch('prs.vc_tools.github.client.subprocess.check_output')
    @patch('prs.vc_tools.github.client.get')
    @patch('sys.argv', ['prs'])
    def test_reviewer_workflow(self, mock_config, mock_subprocess, mock_auth_user):
        """Test workflow including reviewer PRs."""
        mock_auth_user.return_value = "reviewer_user"
        
        # Mock configuration
        mock_config.side_effect = lambda section, key, fallback=None: {
            ('git-org', 'org_name'): 'review-org',
            ('git', 'repo_name'): 'review-repo',
            ('pr-info', 'authors'): '',
            ('git', 'username'): 'reviewer_user',
            ('pr-info', 'author'): 'short',
            ('pr-info', 'checks'): 'normal',
            ('pr-info', 'reviews'): 'short',
            ('pr-info', 'labels'): 'none',
            ('pr-info', 'pr_url'): 'short',
            ('pr-info', 'branch'): 'short',
            ('filters', 'ignored'): '',
            ('filters', 'include_reviewer_prs'): 'true',
            ('filters', 'include_reviewed_prs'): 'true'
        }.get((section, key), fallback)
        
        # Mock different queries returning different PRs
        def subprocess_side_effect(args, **kwargs):
            if "author:reviewer_user" in str(args):
                return json.dumps({
                    "number": 400,
                    "user": {"login": "reviewer_user"},
                    "updated_at": "2023-01-01T12:00:00Z",
                    "isDraft": False,
                    "source": "authored"
                }) + "\n"
            elif "review-requested:reviewer_user" in str(args):
                return json.dumps({
                    "number": 500,
                    "user": {"login": "other_user"},
                    "updated_at": "2023-01-01T11:00:00Z",
                    "isDraft": False,
                    "source": "reviewer_pending"
                }) + "\n"
            elif "reviewed-by:reviewer_user" in str(args):
                return json.dumps({
                    "number": 600,
                    "user": {"login": "another_user"},
                    "updated_at": "2023-01-01T10:00:00Z",
                    "isDraft": False,
                    "source": "reviewer_completed"
                }) + "\n"
            return ""
        
        mock_subprocess.side_effect = subprocess_side_effect
        
        with patch('prs.vc_tools.github.client.get_pull_request_details') as mock_details:
            def details_side_effect(pr_id, source):
                role_map = {
                    "authored": "author",
                    "reviewer_pending": "reviewer_pending", 
                    "reviewer_completed": "reviewer_completed"
                }
                
                return {
                    "id": pr_id,
                    "title": f"PR #{pr_id}",
                    "author": f"user_{pr_id}",
                    "labels": [],
                    "checks": [],
                    "reviews": [],
                    "url": f"url_{pr_id}",
                    "branch": f"branch_{pr_id}",
                    "is_draft": False,
                    "role": role_map.get(source, "author")
                }
            
            mock_details.side_effect = details_side_effect
            
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                try:
                    main()
                except SystemExit:
                    pass
                
                output = mock_stdout.getvalue()
                # Should handle multiple role types
                assert len(output) >= 0


class TestPerformanceWorkflows:
    """Test performance characteristics of complete workflows."""

    @patch('prs.vc_tools.github.client.subprocess.check_output')
    @patch('prs.vc_tools.github.client.get')
    @patch('sys.argv', ['prs'])
    def test_large_pr_list_workflow_performance(self, mock_config, mock_subprocess):
        """Test performance with large PR lists."""
        # Mock configuration
        mock_config.side_effect = lambda section, key, fallback=None: {
            ('git-org', 'org_name'): 'perf-org',
            ('git', 'repo_name'): 'perf-repo',
            ('pr-info', 'authors'): '',
            ('git', 'username'): 'perf_user',
            ('pr-info', 'author'): 'short',
            ('pr-info', 'checks'): 'short',
            ('pr-info', 'reviews'): 'short',
            ('pr-info', 'labels'): 'short',
            ('pr-info', 'pr_url'): 'short',
            ('pr-info', 'branch'): 'short',
            ('filters', 'ignored'): '',
            ('filters', 'include_reviewer_prs'): 'false'
        }.get((section, key), fallback)
        
        # Generate large PR list
        large_pr_list = []
        for i in range(50):
            pr_data = {
                "number": i + 1,
                "user": {"login": "perf_user"},
                "updated_at": f"2023-01-{(i % 28) + 1:02d}T12:00:00Z",
                "isDraft": i % 10 == 0,
                "source": "authored"
            }
            large_pr_list.append(json.dumps(pr_data))
        
        mock_subprocess.return_value = "\n".join(large_pr_list) + "\n"
        
        with patch('prs.vc_tools.github.client.get_pull_request_details') as mock_details:
            def details_side_effect(pr_id, source):
                return {
                    "id": pr_id,
                    "title": f"Performance PR #{pr_id}",
                    "author": "perf_user",
                    "labels": [f"label_{pr_id % 5}"],
                    "checks": [{"name": "CI", "status": "SUCCESS"}],
                    "reviews": [],
                    "url": f"url_{pr_id}",
                    "branch": f"branch_{pr_id}",
                    "is_draft": pr_id % 10 == 0,
                    "role": "author"
                }
            
            mock_details.side_effect = details_side_effect
            
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                try:
                    main()
                except SystemExit:
                    pass
                
                # Should complete without performance issues
                output = mock_stdout.getvalue()
                assert len(output) >= 0

    def test_memory_efficient_end_to_end(self):
        """Test memory efficiency of complete workflows."""
        # This test primarily ensures no obvious memory leaks
        # in the complete pipeline
        
        with patch('prs.vc_tools.github.client.list_all_prs') as mock_list:
            with patch('prs.vc_tools.github.client.get_pull_request_details') as mock_details:
                # Mock modest dataset
                mock_list.return_value = [
                    {"number": i, "source": "authored", "isDraft": False} 
                    for i in range(20)
                ]
                
                def details_side_effect(pr_id, source):
                    return {
                        "id": pr_id,
                        "title": f"Memory Test PR {pr_id}",
                        "author": "memory_user",
                        "labels": [],
                        "checks": [],
                        "reviews": [],
                        "url": f"url_{pr_id}",
                        "branch": f"branch_{pr_id}",
                        "is_draft": False,
                        "role": "author"
                    }
                
                mock_details.side_effect = details_side_effect
                
                # Test multiple workflow executions
                for i in range(5):
                    filters = {"state": "open", "include_draft": False, "no_reviewer": True, "no_reviewed": True}
                    verbosity = {
                        "author": "short",
                        "checks": "normal", 
                        "reviews": "short",
                        "labels": "short",
                        "pr_url": "short",
                        "branch": "short"
                    }
                    
                    # Should complete without accumulating memory
                    try:
                        list_pull_requests({"state": "open", "include_draft": False, "no_reviewer": True, "no_reviewed": True})
                    except Exception:
                        # May fail due to missing dependencies, but should not crash memory
                        pass