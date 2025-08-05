import argparse
import os
import subprocess
import sys

from prs.config import all_config, get, set, get_ignored_prs, set_ignored_prs, get_ignored_users, add_ignored_users, CONFIG_PATH
from prs.core.printPullRequests import list_pull_requests
from prs.utils.formatting import color_text
from prs.utils.username_colors import (
    get_all_color_assignments, 
    reset_color_assignments, 
    preassign_username_color,
    get_color_stats,
    AVAILABLE_COLORS
)

# Version constant (should match setup.py)
__version__ = "1.2.0"

class ColoredHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Custom help formatter with colors and reorganized options."""
    
    def __init__(self, prog):
        super().__init__(prog)
        self._actions_store = []
    
    def add_action(self, action):
        """Store actions for later reorganization."""
        self._actions_store.append(action)
        return action
    
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
    
    def _format_action(self, action):
        """Format a single action with single-line layout and colors."""
        # Handle subparsers specially
        if action.nargs == argparse.PARSER:
            # Get the help info stored when adding subparsers
            subparsers_help = {}
            if hasattr(action, '_choices_actions'):
                for subaction in action._choices_actions:
                    if hasattr(subaction, 'dest') and hasattr(subaction, 'help'):
                        subparsers_help[subaction.dest] = subaction.help
            
            # Get parser choices
            parsers = action.choices
            if parsers:
                # Calculate the width for alignment
                max_len = max(len(name) for name in parsers.keys())
                
                # Build help strings for each subcommand
                help_lines = []
                for name in sorted(parsers.keys()):
                    # Get help text from stored info
                    help_text = subparsers_help.get(name, "")
                    
                    # Format the line with color
                    name_colored = color_text(name.ljust(max_len + 4), "green")
                    help_lines.append(f"    {name_colored}{help_text}")
                
                # Build the complete output
                output = ["positional arguments:", f"  {color_text(action.metavar, 'green')}"]
                output.extend(help_lines)
                output.append("")
                return '\n'.join(output)
        
        # For regular options, format in single-line style
        if not action.option_strings:
            return super()._format_action(action)
        
        # Build the option string
        option_text = ", ".join(action.option_strings)
        colored_options = ", ".join([color_text(opt, "yellow") for opt in action.option_strings])
        
        # Use fixed width of 18 characters for options
        option_width = 18
        padding_needed = option_width - len(option_text)
        if padding_needed > 0:
            formatted_option = colored_options + " " * padding_needed
        else:
            formatted_option = colored_options + " "
        
        # Get help text
        help_text = action.help or ""
        
        # Format choices if they exist
        if hasattr(action, 'choices') and action.choices:
            if action.dest == 'pr_url':
                # Special case for pr_url - only show none and normal
                choices_text = "{ " + ", ".join([color_text("none", "cyan"), color_text("normal", "cyan")]) + " }"
            else:
                choices_text = "{ " + ", ".join([color_text(str(choice), "cyan") for choice in action.choices]) + " }"
            
            # Format with choices on second line
            result = f"  {formatted_option}{help_text}\n"
            result += f"                        {choices_text}\n"
        else:
            # Single line format
            result = f"  {formatted_option}{help_text}\n"
        
        return result
    
    def format_help(self):
        """Override format_help to reorganize options by category."""
        # Get the standard help text
        help_text = super().format_help()
        lines = help_text.split('\n')
        
        # Find the options section
        options_start = -1
        options_end = len(lines)
        
        for i, line in enumerate(lines):
            if line.strip() == "options:":
                options_start = i
                break
                
        if options_start == -1:
            return help_text
            
        # Find where options end
        for i in range(options_start + 1, len(lines)):
            if lines[i] and not lines[i].startswith(' ') and not lines[i].startswith('\t'):
                options_end = i
                break
        
        # Extract and categorize options
        option_lines = []
        i = options_start + 1
        while i < options_end:
            line = lines[i]
            if line.strip() and line.startswith('  '):
                option_lines.append(line)
                # Check if next line is a continuation (choices)
                if i + 1 < options_end and lines[i + 1].startswith('                        '):
                    i += 1
                    option_lines.append(lines[i])
            i += 1
        
        # Define categories and their order
        categories = {
            'basic': ['-h', '--help', '-v', '--version'],
            'display': ['-d', '--draft', '-b', '--branch', '-c', '--checks', '-r', '--reviews', '-l', '--labels'],
            'advanced': ['--lines', '--pr_url'],
            'filtering': ['--no-reviewer-prs', '--no-reviewed-prs', '--include-ignored']
        }
        
        # Categorize the option lines
        categorized_options = {cat: [] for cat in categories.keys()}
        uncategorized = []
        
        i = 0
        while i < len(option_lines):
            line = option_lines[i]
            categorized = False
            
            # Find which category this option belongs to
            for category, opts in categories.items():
                for opt in opts:
                    if opt in line:
                        categorized_options[category].append(line)
                        # Check if there's a continuation line
                        if i + 1 < len(option_lines) and option_lines[i + 1].startswith('                        '):
                            i += 1
                            categorized_options[category].append(option_lines[i])
                        categorized = True
                        break
                if categorized:
                    break
            
            if not categorized:
                uncategorized.append(line)
            
            i += 1
        
        # Build new options section
        new_options = ["options:"]
        
        # Add basic options
        if categorized_options['basic']:
            new_options.extend(categorized_options['basic'])
            new_options.append("")  # Spacing
        
        # Add display options
        if categorized_options['display']:
            new_options.extend(categorized_options['display'])
            new_options.append("")  # Spacing
        
        # Add advanced options
        if categorized_options['advanced']:
            new_options.extend(categorized_options['advanced'])
            new_options.append("")  # Spacing
        
        # Add filtering options
        if categorized_options['filtering']:
            new_options.extend(categorized_options['filtering'])
        
        # Add any uncategorized options
        if uncategorized:
            new_options.append("")  # Spacing if there were other categories
            new_options.extend(uncategorized)
        
        # Reconstruct the help text
        result_lines = lines[:options_start] + new_options + lines[options_end:]
        return '\n'.join(result_lines)



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
        "--no-reviewer-prs",
        action="store_true",
        default=False,
        help="Exclude PRs where you are a reviewer",
    )
    parser.add_argument(
        "--no-reviewed-prs",
        action="store_true",
        default=False,
        help="Exclude PRs where you have already given a review",
    )
    parser.add_argument(
        "--include-ignored",
        action="store_true",
        default=False,
        help="Include PRs from ignored users (normally filtered out)",
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
    parser.add_argument(
        "--lines",
        type=int,
        default=5,
        help="Number of lines to show in long mode (default: 5)",
    )
    parser.add_argument(
        "-w", "--watch",
        type=int,
        nargs="?",
        const=30,
        default=None,
        help=f"{color_text('NEW!', 'green')} Watch mode: continuously update PR status (interval in seconds, default: 30, minimum: 10)",
    )
    parser.add_argument(
        "-exp", "--export",
        type=str,
        nargs="?",
        const="default",
        default=None,
        help=f"{color_text('NEW!', 'green')} Export PRs to JSON file (optional filename, default: prs_export_YYYYMMDD_HHMMSS.json)",
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

    #! 'ignore-user' subcommand
    user_ignore_parser = subparsers.add_parser(
        "ignore-user", 
        help=f"{color_text('NEW!', 'green')} Ignore PRs from specific users"
    )
    user_ignore_parser.add_argument(
        "usernames", 
        help="Comma-separated usernames to ignore (ex: user1,user2)"
    )

    #! 'colors' subcommand
    colors_parser = subparsers.add_parser(
        "colors", 
        help=f"{color_text('NEW!', 'green')} Manage username color assignments"
    )
    colors_parser.add_argument(
        "action", 
        choices=["list", "stats", "reset", "assign", "palette"],
        help="Action: list assignments, show stats, reset all, assign color, show palette"
    )
    colors_parser.add_argument(
        "username", 
        nargs="?", 
        help="Username for assign action"
    )
    colors_parser.add_argument(
        "color", 
        nargs="?", 
        help="Color name for assign action"
    )

    args = parser.parse_args()

    # If no subcommand provided, default to "list"
    if args.command is None:
        args.command = "list"

    if args.command == "list":
        # Watch mode validation
        if args.watch is not None:
            if args.watch < 10:
                print(f"Error: Watch interval must be at least 10 seconds (got {args.watch})")
                sys.exit(1)
        
        options = {"include_draft": args.draft, "lines": args.lines, "no_reviewer": args.no_reviewer_prs, "no_reviewed": args.no_reviewed_prs, "include_from_ignored_users": args.include_ignored}
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
        
        # Add watch interval to options if specified
        if args.watch is not None:
            options["watch_interval"] = args.watch
        
        # Add export option if specified
        if args.export is not None:
            options["export"] = args.export

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
    elif args.command == "ignore-user":
        # Parse comma-separated ignored usernames
        ignored_usernames = [ignUser.strip() for ignUser in args.usernames.split(",") if ignUser.strip()]

        if not ignored_usernames:
            print("Error: No valid ignored usernames provided.")
            sys.exit(1)

        # Add to ignored users list
        add_ignored_users(ignored_usernames)

        # Show current list
        current_ignored = get_ignored_users()
        print(f"Ignored users updated: {', '.join(current_ignored)}")
    elif args.command == "colors":
        if args.action == "list":
            assignments = get_all_color_assignments()
            if not assignments:
                print("No color assignments found.")
            else:
                print("Username color assignments:")
                for username, color in sorted(assignments.items()):
                    colored_username = color_text(username, color)
                    print(f"  {colored_username} → {color}")
        elif args.action == "stats":
            stats = get_color_stats()
            print(f"Color assignment statistics:")
            print(f"  Total users: {stats['total_users']}")
            print(f"  Colors used: {stats['colors_used']}/{stats['colors_available']}")
            if stats['most_common_colors']:
                print("  Most used colors:")
                for color, count in sorted(stats['most_common_colors'], key=lambda x: x[1], reverse=True):
                    colored_name = color_text(color, color)
                    print(f"    {colored_name}: {count} users")
            if stats['unused_colors']:
                print("  Available colors:")
                for color in stats['unused_colors'][:10]:  # Show first 10
                    colored_name = color_text(color, color)
                    print(f"    {colored_name}")
                if len(stats['unused_colors']) > 10:
                    print(f"    ... and {len(stats['unused_colors']) - 10} more")
        elif args.action == "reset":
            reset_color_assignments()
            print("All color assignments have been reset.")
        elif args.action == "assign":
            if not args.username or not args.color:
                print("Usage: nprs colors assign <username> <color>")
                sys.exit(1)
            if args.color not in AVAILABLE_COLORS:
                print(f"Error: '{args.color}' is not a valid color.")
                print("Available colors:", ", ".join(AVAILABLE_COLORS))
                sys.exit(1)
            success = preassign_username_color(args.username, args.color)
            if success:
                colored_username = color_text(args.username, args.color)
                print(f"Assigned {colored_username} → {args.color}")
            else:
                print(f"Failed to assign color '{args.color}' to '{args.username}'")
        elif args.action == "palette":
            print("Available colors in the palette:")
            for i, color in enumerate(AVAILABLE_COLORS, 1):
                colored_name = color_text(f"{color:12}", color)
                if i % 4 == 0:  # New line every 4 colors
                    print(f"  {colored_name}")
                else:
                    print(f"  {colored_name}", end="")
            if len(AVAILABLE_COLORS) % 4 != 0:
                print()  # Final newline if needed


if __name__ == "__main__":
    run_cli()
