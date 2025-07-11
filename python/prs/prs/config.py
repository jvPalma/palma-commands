import configparser
import os
from pathlib import Path

CONFIG_PATH = Path.home() / ".prsconfig"

_config = configparser.ConfigParser()

# Create a default config file if it does not exist
if not CONFIG_PATH.exists():
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
comments = short
authors = 

[cache]
enabled = true
history_minimum = 50

[ci-auth]
default_platform = github_actions
storage_dir = ~/.prs/tokens
use_keyring = true
token_refresh_threshold = 10

[ci-platforms]
buildkite_base_url = https://buildkite.com
jenkins_base_url = 
gitlab_base_url = https://gitlab.com
github_base_url = https://api.github.com

[github-actions]
enabled = true
workflow_display_limit = 5
job_display_limit = 3
show_runner_info = true
show_workflow_files = true
show_artifacts = true
cache_workflow_data = true
    """
    CONFIG_PATH.write_text(default_config.strip())


_config.read(CONFIG_PATH)


def get(section: str, key: str, fallback: str = "") -> str:
    return _config.get(section, key, fallback=fallback)


def set(section: str, key: str, value: str) -> None:
    if not _config.has_section(section):
        _config.add_section(section)
    _config.set(section, key, value)
    with open(CONFIG_PATH, "w") as configfile:
        _config.write(configfile)


def all_config() -> dict:
    return {s: dict(_config.items(s)) for s in _config.sections()}


# CI Authentication helper functions
def get_ci_auth_config() -> dict:
    """Get CI authentication configuration."""
    return dict(_config.items('ci-auth')) if _config.has_section('ci-auth') else {}


def get_ci_platform_config(platform: str) -> dict:
    """Get CI platform specific configuration."""
    platforms_config = dict(_config.items('ci-platforms')) if _config.has_section('ci-platforms') else {}
    
    # Get platform-specific base URL
    base_url_key = f"{platform}_base_url"
    base_url = platforms_config.get(base_url_key, "")
    
    # Get environment variable for platform
    env_vars = {
        'buildkite': 'BUILDKITE_API_KEY',
        'github_actions': 'GITHUB_TOKEN',
        'gitlab_ci': 'GITLAB_TOKEN',
        'jenkins': 'JENKINS_API_KEY'
    }
    
    env_var = env_vars.get(platform, f"{platform.upper()}_API_KEY")
    env_token = os.getenv(env_var)
    
    return {
        'base_url': base_url,
        'env_var': env_var,
        'env_token': env_token,
        'has_env_token': bool(env_token)
    }


def get_storage_dir() -> Path:
    """Get token storage directory from config."""
    ci_auth_config = get_ci_auth_config()
    storage_dir = ci_auth_config.get('storage_dir', '~/.prs/tokens')
    return Path(storage_dir).expanduser()


def should_use_keyring() -> bool:
    """Check if keyring should be used for token storage."""
    ci_auth_config = get_ci_auth_config()
    return ci_auth_config.get('use_keyring', 'true').lower() == 'true'


def get_token_refresh_threshold() -> int:
    """Get token refresh threshold in minutes."""
    ci_auth_config = get_ci_auth_config()
    return int(ci_auth_config.get('token_refresh_threshold', '10'))


def get_default_ci_platform() -> str:
    """Get default CI platform."""
    ci_auth_config = get_ci_auth_config()
    return ci_auth_config.get('default_platform', 'buildkite')


def set_ci_platform_base_url(platform: str, base_url: str) -> None:
    """Set base URL for CI platform."""
    key = f"{platform}_base_url"
    set('ci-platforms', key, base_url)


def get_github_actions_config() -> dict:
    """Get GitHub Actions specific configuration."""
    if not _config.has_section('github-actions'):
        return {
            'enabled': True,
            'workflow_display_limit': 5,
            'job_display_limit': 3,
            'show_runner_info': True,
            'show_workflow_files': True,
            'show_artifacts': True,
            'cache_workflow_data': True
        }
    
    config_dict = dict(_config.items('github-actions'))
    
    # Convert string values to appropriate types
    return {
        'enabled': config_dict.get('enabled', 'true').lower() == 'true',
        'workflow_display_limit': int(config_dict.get('workflow_display_limit', '5')),
        'job_display_limit': int(config_dict.get('job_display_limit', '3')),
        'show_runner_info': config_dict.get('show_runner_info', 'true').lower() == 'true',
        'show_workflow_files': config_dict.get('show_workflow_files', 'true').lower() == 'true',
        'show_artifacts': config_dict.get('show_artifacts', 'true').lower() == 'true',
        'cache_workflow_data': config_dict.get('cache_workflow_data', 'true').lower() == 'true'
    }


def is_github_actions_enabled() -> bool:
    """Check if GitHub Actions integration is enabled."""
    return get_github_actions_config().get('enabled', True)


def get_workflow_display_limit() -> int:
    """Get the number of workflows to display."""
    return get_github_actions_config().get('workflow_display_limit', 5)


def get_job_display_limit() -> int:
    """Get the number of jobs to display per workflow."""
    return get_github_actions_config().get('job_display_limit', 3)


def should_show_runner_info() -> bool:
    """Check if runner information should be displayed."""
    return get_github_actions_config().get('show_runner_info', True)


def should_show_workflow_files() -> bool:
    """Check if workflow file paths should be displayed."""
    return get_github_actions_config().get('show_workflow_files', True)


def should_show_artifacts() -> bool:
    """Check if artifact information should be displayed."""
    return get_github_actions_config().get('show_artifacts', True)


def should_cache_workflow_data() -> bool:
    """Check if workflow data should be cached."""
    return get_github_actions_config().get('cache_workflow_data', True)
