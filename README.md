# ☕ Coffee - Modern tmux Plugin Manager

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE) [![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)]()

Coffee is a modern and intuitive tmux plugin manager with powerful CLI and terminal UI (TUI). It empowers users to easily install, update, enable/disable, and remove tmux plugins with rich progress feedback and asynchronous operations.

![Coffee TUI Home](screenshots/coffee-home.png "Coffee TUI Home Tab")

## Features

### 🚀 Modern Interface

- Rich Terminal UI (TUI) with tabbed navigation and detailed plugin information
- Comprehensive CLI with intuitive commands and progress feedback
- Real-time plugin status showing version, update status, source files, and last updated

### 📦 Smart Plugin Management

- YAML-based configuration - cleaner than .tmux.conf declarations
- Automatic dependency resolution and conflict detection
- Version locking with rollback capabilities via lock files
- Selective updates - control which plugins auto-update

### ⚡ Performance & Reliability

- Asynchronous operations with progress bars for faster installs/updates
- Git-native - direct repository cloning, tag checkout, and branch switching
- Atomic transactions - failed operations don't break your setup
- Enable/disable plugins without reinstallation

## Installation

### Prerequisites

- tmux >= 3.0
- Python 3.8+
- git

### Clone & Setup

```bash
git clone https://github.com/PraaneshSelvaraj/coffee.tmux ~/.local/share/coffee
cd ~/.local/share/coffee
pip install -r requirements.txt
```

### Add Coffee CLI to PATH

```bash
export PATH="$HOME/.local/share/coffee/bin:$PATH"
```

Add this line to your shell config file (e.g. `~/.bashrc` or `~/.zshrc`) to make it permanent.

### tmux Configuration

Add the following to your `.tmux.conf` (or `$XDG_CONFIG_HOME/tmux/tmux.conf`):

```bash
source-file ~/.local/share/coffee/coffee.tmux
```

After editing your tmux config, reload it with:

```bash
tmux source-file ~/.tmux.conf
```

### Install Plugins

After setup and reloading tmux, run:

```bash
coffee install
```

This installs all plugins configured in your YAML files.

## Usage

### CLI Commands

```bash
coffee install # Install configured plugins
coffee update # Check for plugin updates
coffee upgrade # Upgrade plugins with available updates
coffee upgrade tmux-sensible # Upgrade a specific plugin
coffee remove tmux-sensible # Remove a plugin
coffee list # List installed plugins
coffee info tmux-sensible # Show plugin details
coffee enable tmux-sensible # Enable a plugin
coffee disable tmux-sensible # Disable a plugin
```

### TUI Interface

Launch the TUI interface via by pressing the keybinding (e.g., `prefix + C`).

Navigate with keys:

- `H` - Home tab (view installed/enabled plugins)
- `I` - Install tab (view and install plugins from config)
- `U` - Update tab (check and apply updates)
- `R` - Remove tab (remove plugins)

Use `j`/`k` or arrow keys to move selections, `Space` to mark/toggle, and follow on-screen controls.

## Plugin Configuration

Create YAML files in:

```bash
~/.config/tmux/coffee/plugins/
```

Example configuration:

```yaml
name: "tmux-resurrect"
url: "tmux-plugins/tmux-resurrect"
local: False
tag: "v3.0.0"
skip_auto_update: False
source: ["resurrect.tmux"]
```

Fields:

- `name`: Plugin name (required)
- `url`: GitHub repo path `<owner>/<repo>` (required)
- `local`: Set false for github repos
- `tag`: Optional tag or branch to check out
- `skip_auto_update` : Disable automatic updates (default: false)
- `source`: List of plugin source script files loaded by tmux

## Uninstall Plugins

To uninstall a plugin, remove its YAML configuration file and run:

```bash
coffee remove <plugin-name>
```

Alternatively, use the Remove tab in the TUI to uninstall plugins interactively.

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:

- Setting up your development environment
- Reporting issues and requesting features
- Coding style and tests
- Submitting pull requests

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

Inspired by [tmux-plugins/tpm](https://github.com/tmux-plugins/tpm), and powered by [rich](https://github.com/Textualize/rich) and [textual](https://github.com/Textualize/textual).

## Contact

Maintainer: Praanesh S  
GitHub: [PraaneshSelvaraj](https://github.com/PraaneshSelvaraj)  
Email: praaneshselvaraj2003@gmail.com

For questions or support, please open an issue on GitHub.
