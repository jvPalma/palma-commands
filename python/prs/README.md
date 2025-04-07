# PRS - Pull Request Status CLI (Python Version)

PRS is a command-line utility to inspect your GitHub pull requests. It shows open PRs with status checks, review states, labels, and additional details—all with rich color formatting and configurable verbosity.

## Features

- **List Open PRs:** Displays PR numbers (6-digit, zero-padded), titles (fixed 70 characters, truncated with ellipsis if needed), and a structured summary.
- **Detailed Information:** Configure verbosity (none, short, normal, long) for each section (checks, reviews, labels, URL, branch, and author).
- **Color-Coded Output:** Highlights statuses and uses unique per-user coloring (own user in black-on-green, others with distinct colors).
- **Configurable:** Defaults are loaded from a configuration file (`~/.prsconfig`), and you can override via CLI flags.
- **Modular Architecture:** Separate modules for title, author, checks, reviews, and labels.

## Requirements

- Python 3.6+
- GitHub CLI (`gh`)
- Terminal with ANSI color support

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/your-user/palma-commands.git
   ```

2. **Run the installer:**

   ```bash
   cd palma-commands/python/prs
   chmod +x ./install.sh
   ./install.sh # this will copy the dist/prs binary to the `/home/user/bin` folder
   ```

## Usage

You can run PRS either by invoking Python directly or by using the standalone executable:

- **Directly via Python:**
  
  ```bash
  python -m prs.main [options]
  ```
  
- **Using the Standalone Executable:**
  
  ```bash
  ./prs [options]
  ```

### CLI Options

Global options:
- `-d`, `--draft`  
  Include draft PRs.
- `-c`, `--checks`  
  Set display verbosity for checks: `none`, `short`, `normal`, or `long`.
- `-r`, `--reviews`  
  Set display verbosity for reviews: `none`, `short`, `normal`, or `long`.
- `-l`, `--labels`  
  Set display verbosity for labels: `none`, `short`, `normal`, or `long`.
- `--pr_url`  
  Set display verbosity for PR URL: `none`, `short`, `normal`, or `long`.
- `-b`, `--branch`  
  Set display verbosity for branch: `none`, `short`, `normal`, or `long`.

Subcommands:
- `config`  
  Get or set configuration values.
  - Example: `prs config set git.username your_username`
  - Example: `prs config get git.username`

## Configuration

A configuration file (`~/.prsconfig`) is automatically created if it does not exist. It includes sections such as `[git]`, `[git-org]`, `[vctool]`, and `[pr-info]`. Edit it to set default verbosity levels and other preferences.

Example configuration:
```ini
[git]
repo_name = your-repo
username = your_username
origin = username
upstream = username

[git-org]
team_name =
org_name =

[vctool]
platform = github

[pr-info]
author = short
pr_url = normal
branch = normal
checks = short
reviews = short
labels = short
authors = your_username
```

You can change those by editing the file directly, or using internal commands likw

```shell
nprs config set git.repo_name "anchorage"
nprs config set git.username "jvPalma-anchorage"
nprs config set git.origin "username" #   `username` | `org_name` | string
nprs config set git.upstream "org_name" # `username` | `org_name` | string

nprs config set git-org.org_name "anchorlabsinc"

nprs config set pr-info.pr_url "normal" #   `none` | `normal`
nprs config set pr-info.branch "none"  #    `none` | `normal`
nprs config set pr-info.author "normal" #   `none` | `normal`

nprs config set pr-info.checks "short" #    `none` | `short` | `normal` | `long`
nprs config set pr-info.reviews "short" #   `none` | `short` | `normal` | `long`
nprs config set pr-info.labels "short" #    `none` | `short` | `normal` | `long`
```


## Installation and Building

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/your-user/palma-commands.git
   cd palma-commands/python/prs
   ```

2. **(Optional) Create and Activate a Virtual Environment:**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Dependencies:**

   If you have a `requirements.txt` file, run:
   ```bash
   pip install -r requirements.txt
   ```
   Otherwise, ensure you have the required packages installed.

4. **Build a Standalone Executable with PyInstaller:**

   ```bash
   pyinstaller --onefile --name prs prs/main.py
   ```
   The executable will be created in the `dist/` directory.

5. **Test the Executable:**

   ```bash
   cd dist
   ./prs --help
   ```
   You should see the help message for the tool.

### Standalone Installation

To install the executable system-wide so you can run it from anywhere:

1. **Build the Executable** (see above).

2. **Copy the Executable to a Directory in Your PATH:**

   ```bash
   sudo cp dist/prs /usr/local/bin/prs
   ```

3. **Test from Anywhere:**

   ```bash
   prs --help
   ```

## License

MIT License © 2025 João Palma
