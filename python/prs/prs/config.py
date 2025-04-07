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
