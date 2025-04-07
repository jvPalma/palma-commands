# Palma Commands

**Palma Commands** is a personal collection of terminal tools and CLI utilities designed to boost developer productivity. This repository contains modular command-line tools built for Fish Shell and other environments.

## Tools Included

- **PRS**  
  A Pull Request Status CLI that displays GitHub PRs, along with their CI checks, review statuses, labels, and more. It features configurable verbosity, rich color formatting, and a modular design.

- *(Other tools can be listed here.)*

## PRS - Pull Request Status CLI

PRS is a Python-based command-line utility that helps you quickly inspect your open pull requests on GitHub. It displays detailed information with color-coded summaries and supports multiple verbosity modes.

### Features

- **List Open PRs:** Displays each PR with:
  - A 6-digit, zero-padded PR number.
  - A 70-character title (truncated with ellipsis if too long).
  - A structured summary line showing:
    - Status (`OPEN` or `DRFT`),
    - Checks summary,
    - Reviews summary,
    - Labels summary,
    - Author (with unique colors per user; own username in black-on-green).
  - Optional details: PR URL and branch name.
- **Configurable:** Set default verbosity levels in the configuration file (`~/.prsconfig`) and override them with CLI flags.
- **Modular Architecture:** Each component (checks, reviews, labels, title, author) has its own helper module for easy customization.

### Quick Start

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/your-user/palma-commands.git
   ```

2. **Build and Install PRS:**

   Follow the instructions in the [python/prs/README.md](python/prs/README.md) file to build the standalone executable and install it. For example, after building with PyInstaller:

   ```bash
   cd palma-commands/python/prs
   chmod +x ./install.sh
   ./install.sh # this will copy the dist/prs binary to the `/home/user/bin` folder
   # you may need to source ~/.bashrc to index the new binary, or, close and open a new one
   ```

3. **Run the Tool from Anywhere:**

   ```bash
   prs --help
   ```

## Contributing

Contributions, bug reports, and suggestions are welcome! Feel free to fork this repository and create pull requests with improvements.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
