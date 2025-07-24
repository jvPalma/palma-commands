# PRS - Pull Request Status CLI

PRS is a powerful command-line utility to monitor and manage your GitHub pull requests. It displays PRs with rich formatting, status checks, review states, labels, and comprehensive filtering options—all with configurable verbosity levels and an intuitive panel-based interface.

## 🚀 Key Features

### Core Functionality
- **📋 Rich Panel Display:** Beautiful panel-based interface with color-coded borders reflecting PR health
- **🔍 Multi-source PR Tracking:** Monitor PRs where you're the author, reviewer, or both
- **📊 Comprehensive Status:** Shows checks, reviews, labels, and branch information
- **🎨 Smart Color Coding:** Dynamic panel colors and unique per-user color assignments
- **⚙️ Highly Configurable:** Flexible verbosity levels (none, short, normal, long) for each component

### Advanced Features
- **🚫 PR Filtering:** Ignore specific PRs or users to maintain a clean view
- **📈 Smart Sorting:** PRs sorted by number (oldest to newest) for consistent tracking
- **👥 User Management:** Track multiple team members and filter by user roles
- **🔧 Configuration Management:** Built-in config editor and command-line configuration
- **📱 Responsive Layout:** Dynamic column sizing with intelligent width distribution
- **🎯 Reviewer Integration:** Dedicated support for PRs where you're assigned as reviewer

## 📋 Requirements

- **Python 3.6+**
- **GitHub CLI (`gh`)** - Must be authenticated
- **Terminal with ANSI color support**

## 🛠️ Installation

### Quick Install (Recommended)

```bash
# Download and install in one command
curl -sSL https://raw.githubusercontent.com/jvPalma/palma-commands/main/python/prs/download.sh | bash
```

### Manual Installation

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/jvPalma/palma-commands.git
   cd palma-commands/python/prs
   ```

2. **Build and Install:**
   ```bash
   # Build the executable
   pyinstaller --onefile --name prs prs/main.py
   
   # Install system-wide
   chmod +x ./install.sh
   ./install.sh
   ```

3. **Verify Installation:**
   ```bash
   prs --help
   ```

## 🎯 Usage

### Basic Commands

```bash
# List all open PRs with default settings
prs

# Include draft PRs
prs --draft

# Exclude PRs where you're a reviewer
prs --no-reviewer

# Exclude PRs where you've already reviewed
prs --no-reviewed

# Set verbosity for specific components
prs --checks long --reviews normal --labels short
```

### Configuration Commands

```bash
# View current configuration
prs config all

# Get specific setting
prs config get git.username

# Set configuration values
prs config set git.username myusername
prs config set pr-info.checks long

# Open config file in editor
prs config open
```

### PR Management Commands

```bash
# Ignore specific PRs
prs ignore 1234 1235 1236

# Ignore specific users
prs ignore-users bot-user ci-bot

# View version information
prs --version
```

## ⚙️ Configuration

### Configuration File Location
`~/.prsconfig` (automatically created on first run)

### Essential Configuration Sections

#### Repository Settings (`[git]`)
```ini
[git]
repo_name = your-repo
username = your_username
upstream = org_name  # "username" | "org_name" | literal value
```

#### Organization Settings (`[git-org]`)
```ini
[git-org]
org_name = your-organization
team_name = your-team
```

#### Display Preferences (`[pr-info]`)
```ini
[pr-info]
authors = user1,user2,user3  # Comma-separated list
author = short               # none | short | normal | long
checks = short               # none | short | normal | long  
reviews = short              # none | short | normal | long
labels = short               # none | short | normal | long
pr_url = normal              # none | short | normal | long
branch = normal              # none | short | normal | long
```

#### Filtering Options (`[pr-filter]`)
```ini
[pr-filter]
ignored = 1234,1235,1236                    # Comma-separated PR numbers
ignored_users = bot-user,ci-bot             # Comma-separated usernames
include_reviewer_prs = true                 # Include PRs where you're a reviewer
include_reviewed_prs = true                 # Include PRs you've already reviewed
```

### Quick Configuration Examples

```bash
# Repository setup
prs config set git.repo_name "my-awesome-project"
prs config set git.username "johndoe"
prs config set git.upstream "org_name"

# Organization setup
prs config set git-org.org_name "mycompany"

# Display preferences
prs config set pr-info.checks "long"
prs config set pr-info.reviews "normal"
prs config set pr-info.labels "short"

# Multi-user monitoring  
prs config set pr-info.authors "alice,bob,charlie"
```

## 🎨 Display Modes

### Verbosity Levels

- **`none`**: Hide component completely
- **`short`**: Compact badge format `[CHKS] [RVWS] [LABL]`
- **`normal`**: Summary text on separate line
- **`long`**: Detailed multi-line breakdown with full information

### Panel Color System

Panel borders reflect PR health status:
- **🟢 Green**: All checks passing, approved reviews
- **🟡 Yellow**: Some issues, needs attention
- **🔴 Red**: Failed checks or requested changes
- **🔵 Cyan**: Draft PRs with passing checks
- **⚪ Gray**: Draft PRs with issues

### Role Indicators

- **No prefix**: Author only
- **`[R*]`**: Has pending review request
- **`[Rd]`**: Has completed review
- **`[A+R*]`**: Author with pending review request
- **`[A+Rd]`**: Author with completed review

## 🔧 Advanced Features

### Dynamic Column Layout

The tool uses intelligent column width distribution:
- **Checks column**: Gets 30% more space than other columns in long mode
- **Responsive sizing**: Adapts to terminal width automatically
- **Multi-column support**: Up to 4 columns with optimal spacing

### User Color Management

```bash
# View color assignments
prs config get-colors

# Reset color assignments
prs config reset-colors

# Pre-assign colors to users
prs config assign-color username red
```

### Filtering and Ignoring

```bash
# Ignore problematic PRs
prs ignore 1001 1002 1003

# Ignore bot users
prs ignore-users dependabot renovate-bot

# View current ignore lists
prs config all | grep ignored
```

## 🏗️ Development and Building

### Development Setup

```bash
# Clone and setup
git clone https://github.com/jvPalma/palma-commands.git
cd palma-commands/python/prs

# Install in development mode
pip install -e .

# Run tests
python run_tests.py
```

### Building Standalone Executable

```bash
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller --onefile --name prs prs/main.py

# Test the executable
./dist/prs --help
```

### Testing

```bash
# Run all tests
python run_tests.py

# Run specific test files
python -m pytest prs/core/__tests__/test_models.py -v
```

## 📚 Architecture

### High-Level Design

```
CLI Layer (prs/cli.py)
    ↓
Business Logic (prs/core/usecases.py)
    ↓
Domain Models (prs/core/models.py)
    ↓
External Adapters (prs/vc_tools/github/)
    ↓
GitHub CLI (subprocess calls to 'gh')
```

### Key Modules

- **`prs/cli.py`**: Argument parsing and colored help formatter
- **`prs/core/models.py`**: Domain models (PullRequest entity)
- **`prs/core/display/`**: Modular display system with panel rendering
- **`prs/vc_tools/github/`**: GitHub integration via CLI
- **`prs/config.py`**: Configuration management
- **`prs/utils/`**: Formatting utilities and color management

## 🐛 Troubleshooting

### Common Issues

1. **`gh: command not found`**
   ```bash
   # Install GitHub CLI
   # See: https://cli.github.com/manual/installation
   ```

2. **No PRs showing**
   ```bash
   # Check authentication
   gh auth status
   
   # Verify configuration
   prs config all
   ```

3. **Colors not working**
   ```bash
   # Check terminal support
   echo $TERM
   
   # Test colors
   prs --checks short --reviews short
   ```

### Debug Mode

```bash
# Enable verbose output (if implemented)
PRS_DEBUG=1 prs
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run tests: `python run_tests.py`
5. Commit changes: `git commit -m 'Add amazing feature'`
6. Push to branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

## 📄 License

MIT License © 2025 João Palma

## 🙏 Acknowledgments

- Built with Python and Rich library for terminal UI
- Uses GitHub CLI for seamless GitHub integration
- Developed with AI assistance from Claude (Anthropic)