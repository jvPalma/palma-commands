# PRS - Pull Request Status CLI for Fish Shell 🐟

`prs` is a handy CLI utility for developers working with GitHub and Fish Shell. It allows you to quickly check the status of your open pull requests — including checks, reviews, and labels — all from your terminal with rich formatting, color highlighting, and optional configuration.

---

## 🚀 Features

- View open PRs with CI check summaries or detailed breakdowns
- Review state summary or per-reviewer detail
- Color-coded labels and status
- Configurable `.env` file for persistent options
- Toggle display options via flags
- Easily extensible with helper functions

---

## ⚙️ Setup

1. Clone this repo (or copy the files):

```bash
git clone https://github.com/your-user/palma-commands.git
cd palma-commands/fish/prs
```

2. Run the install script:

```bash
./install.sh
```

3. Load the function (if not restarting Fish):

```fish
source ~/.config/fish/config.fish
```

4. Your config file will be created at:

```bash
~/.prs.env
```

Example content:

```bash
REPO="your-org/your-repo"
USERNAME="@me"

CHECK_ONLY=0
CHECK_DETAILED=1
REVIEWS_ONLY=0
REVIEWS_DETAILED=1
LABELS_ONLY=0
LABELS_DETAILED=1

SHOW_DRAFTS=0
```

---

## 🧪 Usage

```bash
prs [options]
```

### 🔧 Options

| Flag                | Description                          |
| ------------------- | ------------------------------------ |
| `-h`, `--help`      | Show help message                    |
| `-d`, `--draft`     | Include draft PRs                    |
| `-c`, `--checks`    | Show detailed CI check info          |
| `-C`                | Only show CI checks                  |
| `-r`, `--reviewers` | Show detailed reviewers info         |
| `-R`                | Only show reviewers                  |
| `-l`, `--labels`    | Show detailed labels                 |
| `-L`                | Only show labels                     |
| `--save`            | Save current Flags in use as default |

---

## 💡 Use Cases

### 🟢 Basic Usage

```bash
prs
```

Shows all open PRs authored by you with a summary of status checks, reviews, and labels.

---

### 🧪 See only the CI tests information

```bash
prs -C
```

Shows **only** PRs' CI check summary (e.g., failures/pending/success).

---

### 👀 Get full review details

```bash
prs --reviews
```

List all reviewers and their latest review status per PR.

---

### 🏷️ Focus on labels

```bash
prs -L
```

Only display PRs and their label classifications (e.g., `skip-ci`, `ready-to-merge`, etc).

---

### 🧪 + 👀 Combo Example

```bash
prs -c -r -d
```

Show all open PR's, including the ones in **draft**, detailed **checks** and **reviewers** together.

---

## 📦 Requirements

- [Fish Shell](https://fishshell.com/)
- [GitHub CLI (`gh`)](https://cli.github.com/)
- [`jq`](https://stedolan.github.io/jq/) for JSON processing

---

## 🪪 License

MIT © 2025 João Palma
