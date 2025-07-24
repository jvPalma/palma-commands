import configparser
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
authors = 

[filters]
ignored = 
ignored_users = 
include_reviewer_prs = true
include_reviewed_prs = true

[user-colors]
assignments = {}

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


def get_ignored_prs() -> list[int]:
    """Get list of ignored PR numbers from config."""
    ignored_str = get("filters", "ignored", fallback="")
    if not ignored_str.strip():
        return []
    
    # Parse comma-separated PR numbers
    try:
        return [int(pr.strip()) for pr in ignored_str.split(",") if pr.strip()]
    except ValueError:
        return []


def set_ignored_prs(pr_numbers: list[int]) -> None:
    """Set the list of ignored PR numbers in config."""
    ignored_str = ",".join(str(pr) for pr in pr_numbers)
    set("filters", "ignored", ignored_str)


def get_ignored_users() -> list[str]:
    """Get list of ignored usernames from config."""
    ignored_str = get("filters", "ignored_users", fallback="")
    if not ignored_str.strip():
        return []

    # Parse comma-separated ignored usernames
    return [ignUser.strip() for ignUser in ignored_str.split(",") if ignUser.strip()]


def set_ignored_users(ignUsernames: list[str]) -> None:
    """Set the list of ignored usernames in config."""
    ignored_str = ",".join(ignUsernames)
    set("filters", "ignored_users", ignored_str)


def add_ignored_users(new_users: list[str]) -> None:
    """Add new usernames to the existing ignored users list."""
    current_users = get_ignored_users()
    # Remove duplicates while preserving order
    all_users = current_users[:]
    for user in new_users:
        if user not in all_users:
            all_users.append(user)
    set_ignored_users(all_users)
