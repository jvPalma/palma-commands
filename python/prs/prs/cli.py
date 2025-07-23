import argparse
import os
import subprocess
import sys

from prs.config import all_config, get, set, get_ignored_prs, set_ignored_prs, CONFIG_PATH
from prs.core.usecases import list_pull_requests


def run_cli():
    parser = argparse.ArgumentParser(
        prog="nprs", description="PRS - Pull Request Status CLI"
    )
    # Global arguments for the list command
    parser.add_argument(
        "--draft", "-d", action="store_true", default=False, help="Include draft PRs"
    )
    parser.add_argument(
        "--pr_url",
        type=str,
        choices=["none", "short", "normal", "long"],
        default=None,
        help="Set display verbosity for PR URL",
    )
    parser.add_argument(
        "--branch",
        "-b",
        type=str,
        choices=["none", "short", "normal", "long"],
        default=None,
        help="Set display verbosity for branch",
    )
    parser.add_argument(
        "--checks",
        "-c",
        type=str,
        choices=["none", "short", "normal", "long"],
        default=None,
        help="Set display verbosity for checks",
    )
    parser.add_argument(
        "--reviews",
        "-r",
        type=str,
        choices=["none", "short", "normal", "long"],
        default=None,
        help="Set display verbosity for reviews",
    )
    parser.add_argument(
        "--labels",
        "-l",
        type=str,
        choices=["none", "short", "normal", "long"],
        default=None,
        help="Set display verbosity for labels",
    )

    #! Subcommands
    subparsers = parser.add_subparsers(dest="command")

    #! 'config' subcommand
    config_parser = subparsers.add_parser("config", help="Get, set, view all, or open configuration")
    config_parser.add_argument("action", choices=["get", "set", "all", "open"])
    config_parser.add_argument("key", nargs="?", help="Ex: git.username")
    config_parser.add_argument(
        "value", nargs="?", help="Value to set (used with 'set')"
    )

    #! 'ignore' subcommand
    ignore_parser = subparsers.add_parser("ignore", help="Ignore PRs by number")
    ignore_parser.add_argument(
        "pr_numbers", 
        nargs="+", 
        type=int,
        help="PR numbers to ignore (ex: 1234 1235 1236)"
    )

    args = parser.parse_args()

    # If no subcommand provided, default to "list"
    if args.command is None:
        args.command = "list"

    if args.command == "list":
        options = {"include_draft": args.draft}
        if args.pr_url is not None:
            options["pr_url"] = args.pr_url
        if args.branch is not None:
            options["branch"] = args.branch
        if args.checks is not None:
            options["checks"] = args.checks
        if args.reviews is not None:
            options["reviews"] = args.reviews
        if args.labels is not None:
            options["labels"] = args.labels

        list_pull_requests(options)
    elif args.command == "config":
        if args.action == "get":
            if not args.key:
                print("You must provide a key. Example: git.username")
                sys.exit(1)
            section, key = args.key.split(".")
            print(get(section, key))
        elif args.action == "set":
            if not args.key or not args.value:
                print("Usage: nprs config set git.username yourName")
                sys.exit(1)
            section, key = args.key.split(".")
            set(section, key, args.value)
            print(f"Set {section}.{key} = {args.value}")
        elif args.action == "all":
            for section, items in all_config().items():
                print(f"[{section}]")
                for key, value in items.items():
                    print(f"{key} = {value}")
                print()
        elif args.action == "open":
            # Get the editor from environment variable
            editor = os.environ.get("EDITOR")
            if not editor:
                print("Error: $EDITOR environment variable is not set.")
                print("Please set your preferred editor: export EDITOR=nano")
                sys.exit(1)
            
            try:
                # Open the config file with the user's preferred editor
                subprocess.run([editor, str(CONFIG_PATH)], check=True)
            except subprocess.CalledProcessError:
                print(f"Error: Failed to open config file with '{editor}'")
                sys.exit(1)
            except FileNotFoundError:
                print(f"Error: Editor '{editor}' not found. Please check your $EDITOR setting.")
                sys.exit(1)
    elif args.command == "ignore":
        # Get current ignored PRs and add new ones
        current_ignored = get_ignored_prs()
        combined = current_ignored + args.pr_numbers
        new_ignored = list(dict.fromkeys(combined))  # Remove duplicates while preserving order
        new_ignored.sort()  # Keep them sorted
        
        set_ignored_prs(new_ignored)
        print(f"Ignored PRs updated: {', '.join(map(str, new_ignored))}")


if __name__ == "__main__":
    run_cli()
