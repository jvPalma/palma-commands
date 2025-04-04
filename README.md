# 🛠️ Palma Commands

**Palma Commands** is a personal collection of terminal tools, helpers, and CLI enhancements built for productivity and daily developer workflows.  
Designed to work with Fish Shell and modern tooling like `gh`, `jq`, `docker`, and more.

> This repository is modular — each tool or command lives in its own folder and is self-contained, documented, and ready to install.

### Feel free to fork and adapt these scripts for your own workflows. :muscle:

---

## 📦 Tools Available

| Tool                | Description                                                                                                                                           |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`prs`](./fish/prs) | A CLI utility to inspect your GitHub pull requests, check CI status, review states, labels, and more — all from the terminal with colors and control. |

---

## 🧭 How to Use

Each tool comes with its own:

- Installation script (`install.sh`)
- Documentation (`README.md`)
- Configuration if needed (e.g., `.env` files)
- Fish Shell-compatible code

To install a tool, navigate into its folder and follow the specific instructions.

For example:

```bash
cd fish/prs
./install.sh
```
