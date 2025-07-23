import argparse
import os
import subprocess
import sys

from prs.config import all_config, get, set, get_ignored_prs, set_ignored_prs, CONFIG_PATH
from prs.core.printPullRequests import list_pull_requests
from prs.utils.formatting import color_text

# Version constant (should match setup.py)
__version__ = "1.0.0"

class ColoredHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Custom help formatter with colors and concise formatting."""
    
    def _format_action_invocation(self, action):
        """Format option strings with cyan color in a fixed 15-char width."""
        if not action.option_strings:
            # Positional arguments - make them green
            metavar, = self._metavar_formatter(action, action.dest)(1)
            return color_text(metavar, "green")
        else:
            # Build the option string (short + long)
            option_text = ", ".join(action.option_strings)
            
            # Create the colored version but measure the uncolored length
            colored_options = ", ".join([color_text(opt, "yellow") for opt in action.option_strings])
            
            # Pad to 15 characters (using the uncolored length for measurement)
            padding_needed = 15 - len(option_text)
            if padding_needed > 0:
                padded_options = colored_options + " " * padding_needed
            else:
                padded_options = colored_options
            
            # Add the argument specification if this action takes arguments
            if action.nargs != 0:
                args_string = self._format_args(action, self._get_default_metavar_for_optional(action))
                # Custom formatting for choices to add spaces
                if hasattr(action, 'choices') and action.choices:
                    args_string = "{ " + ", ".join(str(color_text(choice, "cyan")) for choice in action.choices) + " }"
                return f"{padded_options}{args_string}"
            else:
                return padded_options
    
    def _format_args(self, action, default_metavar):
        """Custom args formatting with better choice display."""
        get_metavar = self._metavar_formatter(action, default_metavar)
        result = get_metavar(1)[0]
        
        # Custom formatting for choices to add spaces
        if hasattr(action, 'choices') and action.choices:
            result = "{ " + ", ".join(str(color_text(choice, "cyan")) for choice in action.choices) + " }"

        return result
    
    def _format_usage(self, usage, actions, groups, prefix):
        """Format usage line with colors."""
        if prefix is None:
            prefix = "usage: "
        
        # Get the standard usage formatting
        usage_text = super()._format_usage(usage, actions, groups, prefix)
        
        # Color the program name green
        lines = usage_text.split('\n')
        if lines:
            first_line = lines[0]
            if first_line.startswith("usage: "):
                prog_part = first_line[7:].split()[0]  # Extract program name
                colored_line = first_line.replace(prog_part, color_text(prog_part, "green"), 1)
                lines[0] = colored_line
        
        return '\n'.join(lines)


def run_cli():
    parser = argparse.ArgumentParser(
        prog="nprs", 
        description=f"""
{color_text('PRS', 'green')} - Pull Request Status CLI

Display PRs with customizable verbosity.
Supports {color_text('ignoring', 'cyan')} specific PRs and {color_text('config management', 'cyan')}.
Verbosity levels: {color_text('none', 'gray-4')} (hide), {color_text('short', 'gray-4')} (badges), {color_text('normal', 'gray-4')} (summary), {color_text('long', 'gray-4')} (detailed)
""",
        formatter_class=ColoredHelpFormatter
    )
    # Version argument
    parser.add_argument(
        "-v", "--version", 
        action="version", 
        version=f"{color_text('PRS', 'green')} v{color_text(__version__, 'cyan')} - Pull Request Status CLI"
    )
    # Global arguments for the list command
    parser.add_argument(
         "-d", "--draft",action="store_true", default=False, help="Include draft PRs"
    )
    parser.add_argument(
        "--pr_url",
        type=str,
        choices=["none", "short", "normal", "long"],
        default=None,
        help="Show PR URLs",
    )
    parser.add_argument(
        "-b",
        "--branch",
        type=str,
        choices=["none", "short", "normal", "long"],
        default=None,
        help="Show branch names",
    )
    parser.add_argument(
        "-c",
        "--checks",
        type=str,
        choices=["none", "short", "normal", "long"],
        default=None,
        help="Show CI/CD checks",
    )
    parser.add_argument(
        "-r",
        "--reviews",
        type=str,
        choices=["none", "short", "normal", "long"],
        default=None,
        help="Show review status",
    )
    parser.add_argument(
        "-l",
        "--labels",
        type=str,
        choices=["none", "short", "normal", "long"],
        default=None,
        help="Show PR labels",
    )

    #! Subcommands
    subparsers = parser.add_subparsers(dest="command")

    #! 'config' subcommand  
    config_parser = subparsers.add_parser(
        "config", 
        help=f"Manage configuration: {color_text('get', 'cyan')}, {color_text('set', 'cyan')}, {color_text('all', 'cyan')}, {color_text('open', 'cyan')} {color_text('(NEW!)', 'green')}"
    )
    config_parser.add_argument("action", choices=["get", "set", "all", "open"])
    config_parser.add_argument("key", nargs="?", help="Config key (ex: git.username)")
    config_parser.add_argument(
        "value", nargs="?", help="Value to set (for 'set' action)"
    )

    #! 'ignore' subcommand
    ignore_parser = subparsers.add_parser(
        "ignore", 
        help=f"{color_text('NEW!', 'green')} Ignore specific PRs from display"
    )
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
