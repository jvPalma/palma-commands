# VS Code Nerd Font Installer ( Web + Linux manual installation )

A comprehensive font management system for VS Code that allows you to:

- **Select from existing fonts**: Choose from pre-installed JetBrains Mono and Ubuntu Mono Nerd Fonts
- **Choose specific variants**: Pick only the font styles you want (Bold, Italic, Regular, etc.)
- **Save preferences**: Your font selections are remembered between sessions
- **Import custom fonts**: Download any font from the Nerd Fonts repository with a single command
- **Install to VS Code**: Works with both local VS Code and web-based VS Code containers
- **Auto-update support**: Easy re-installation when VS Code web containers update

Perfect for VS Code web environments where fonts need to be re-applied after container updates.

## Quick Install

To use this script without cloning the entire repository, run:

```bash
curl -s https://raw.githubusercontent.com/jvPalma/palma-commands/master/.fonts/_core/download.sh | bash
```

This will install to `~/.fonts` by default. To install to a custom location:

```bash
curl -s https://raw.githubusercontent.com/jvPalma/palma-commands/master/.fonts/_core/download.sh | bash -s -- "/path/to/your/fonts"
```

## Usage

Once installed, navigate to your font directory and run:

```bash
cd ~/.fonts
./install.sh
```

The installer provides:

- Interactive font selection menu
- Support for both web and local VS Code
- Dynamic CSS generation based on selected fonts
- Automatic font discovery

## What This Script Does

This font management system allows you to:

1. **Browse and select fonts** from the existing JetBrains Mono and Ubuntu Mono Nerd Fonts collections
2. **Choose specific variants** - pick only the font styles you want (Bold, Italic, Regular, Light, etc.)
3. **Save your preferences** - your font selections are remembered in `font-config.json`
4. **Import new fonts** - download any font from the Nerd Fonts repository using `./_core/import-font.sh <FontName>`
5. **Install to VS Code** - works with both local VS Code (`/usr/share/code/`) and web-based VS Code containers (`~/.vscode/cli/serve-web/`)
6. **Generate CSS** - automatically creates `nerdFonts.css` with @import statements for your selected fonts

Perfect for VS Code web environments where fonts need to be re-applied after container updates.

## Quick Access Setup

For easy font management, add this alias to your shell profile:

```bash
alias update-fonts="cd ~/.fonts && ./install.sh"
```

Then simply run `update-fonts` from anywhere to manage your fonts.

## VS Code Web Browser Setup

After installing fonts for VS Code web, you'll need to reload the browser to see the fonts:

1. **Open Developer Console**: Press `Ctrl+Shift+J` (or `Cmd+Option+J` on Mac)
2. **Hard Reload**: Press `Ctrl+Shift+R` (or `Cmd+Shift+R` on Mac)
3. **Alternative**: Navigate to Settings > Appearance > Font Family and reselect your font

## VS Code Settings Configuration

After installing fonts, configure VS Code to use them. Add these settings to your `settings.json`:

```json
{
  "editor.fontFamily": "JetBrains Mono Nerd Font, Ubuntu Mono Nerd Font, monospace",
  "editor.fontSize": 14,
  "editor.fontLigatures": true,
  "terminal.integrated.fontFamily": "JetBrains Mono Nerd Font, Ubuntu Mono Nerd Font, monospace",
  "terminal.integrated.fontSize": 14
}
```

**Example with actual installed fonts** (based on your current selections):
```json
{
  "editor.fontFamily": "JetBrains Mono Nerd Font, Ubuntu Mono Nerd Font, monospace",
  "terminal.integrated.fontFamily": "JetBrains Mono Nerd Font, Ubuntu Mono Nerd Font, monospace"
}
```
