import argparse
import sys

from prs.config import all_config, get, set
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

    # Subcommands
    subparsers = parser.add_subparsers(dest="command")

    # 'config' subcommand
    config_parser = subparsers.add_parser("config", help="Get or set configuration")
    config_parser.add_argument("action", choices=["get", "set", "all"])
    config_parser.add_argument("key", nargs="?", help="Ex: git.username")
    config_parser.add_argument(
        "value", nargs="?", help="Value to set (used with 'set')"
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


if __name__ == "__main__":
    run_cli()
