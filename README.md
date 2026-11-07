# OkumaBar

**A curated top bar for Omarchy, powered by Quickshell.**

Author: **ŌKUMA** · Project ID: `okuma.dev_bar4omarchy` · Repository: [Okumai/Bar](https://github.com/Okumai/Bar)

[Contributing](CONTRIBUTING.md) · [Credits](docs/THIRD_PARTY.md)

OkumaBar packages four custom widgets and a complete top-bar layout into one installable project. It extends the existing Omarchy Shell; it is **not** a replacement shell, a standalone Quickshell configuration, or an official Omarchy project.

## Widgets

| Widget | Features |
| --- | --- |
| Clock | Date/time, calendar, ISO week numbers, year progress, optional life-progress view |
| Weather | Current conditions, four-day forecast, city search, temperature units |
| Workspaces | Per-monitor workspace indicators, scrolling, layout mode controls |
| RAM Checker | RAM/swap/cache information, per-window RSS estimates, shortcuts to focus existing windows |

The included layout reproduces the source desktop's current top bar:

- **Left:** clock → world clocks → weather → system update → RAM.
- **Center:** Omarchy menu, with indicators before it and workspaces after it.
- **Right:** tray → keyboard layout → agents → Bluetooth → network → audio → monitor → power.

Built-in widgets are supplied by Omarchy, not copied into this repository. Dock and Launchpad are separate projects: [Dock](https://github.com/Okumai/Dock), [Launchpad](https://github.com/Okumai/Launchpad).

## Requirements

- An existing **Omarchy 4.5.0-style Quickshell shell** installation with `~/.config/omarchy/shell.json`.
- Hyprland and Omarchy's workspace Lua functions/helpers. This is **not compatible with older Waybar-based Omarchy installations** or arbitrary Hyprland configurations.
- Python 3 (standard library only), `curl`, `hyprctl`, Quickshell, and Omarchy commands. No `sudo` or automatic package installation.
- A Nerd Font supported by the active Omarchy theme.

Source capture: Omarchy package `4.5.0-3`. Packaging and isolated installer tests are included; verify the visual result on your Omarchy version before relying on it. Shell APIs may change between releases.

## Install / activate

Inspect the repository and scripts before running:

```bash
git clone https://github.com/Okumai/Bar.git OkumaBar
cd OkumaBar
python3 scripts/manage.py check
./install.sh
```

Already cloned? **`./install.sh` is the one-command activation.** Do not run as root. Close the bar settings editor during install/uninstall to avoid concurrent configuration writes.

Installation displays the affected configuration and asks for explicit consent
before any configuration write. Non-interactive installation is refused unless
you pass `./install.sh --yes`; that flag explicitly authorizes replacing the bar.

The installer copies plugins into `~/.config/omarchy/plugins/okuma.dev_bar4omarchy.*` and replaces **only the `bar` key** in `shell.json`. It preserves unrelated settings, including idle/lock, Dock pins, and other top-level plugins. It does replace your previous bar layout and bar-specific options; a backup is created first.

Before activation it saves the previous configuration and any matching plugin directories in:

```text
~/.config/omarchy/okumabar-backups/<timestamp>/
```

The active installation record is `~/.config/omarchy/okumabar-state.json`. A second install is refused until uninstall, preventing accidental loss of the original restore point. Installation failures attempt rollback. Keep the backup directory until you no longer need to restore.

Omarchy should hot-reload automatically. If necessary, run `omarchy restart shell`. The installer intentionally does not restart your desktop shell.

### Disable weather requests

Installing the default layout enables weather requests. To exclude the custom weather widget:

```bash
./install.sh --without-weather
```

All four plugin directories are copied, but weather is not referenced in the layout and does not run. Built-in widgets, including Agents, follow Omarchy's own settings and network behavior. To change activation options later, uninstall and install again.

## Restore / uninstall

```bash
./uninstall.sh
```

Restores the previous `bar` configuration and matching plugin directories; settings outside `bar` edited since installation are preserved. Existing original `llm.*` plugins are never deleted or modified. Backup files remain on disk.

If you changed bar settings after installation, the uninstaller stops rather than silently discarding them. Review/back up your edits, then explicitly restore:

```bash
./uninstall.sh --force
```

A rescue copy of current configuration and installed plugin files is also saved under the backup directory before removal. **Force restores the old bar and discards subsequent bar edits from the active configuration.** Restore operations are not a live-shell transaction; retain backups if interrupted.

For upgrades: uninstall, update the checkout, then install again. After replacing QML components, run `omarchy restart shell`: plugin rescanning can leave previously loaded QML types cached, so hot reload alone may still show the old panels. Reapply desired post-install bar edits afterward.

## Configure

Edit `presets/bar.json` **before installation** to choose layout or defaults. Once installed, edit `~/.config/omarchy/shell.json` or use Omarchy's bar settings. Plugin settings live on their entries in `bar.layout`.

Plugin IDs are the project ID plus `.clock`, `.weather`, `.workspaces`, or `.ram-cleaner`. This suite uses multiple manifests because each bar widget is independently discoverable by Omarchy; `project.json` describes the overall project.

Example clock entry:

```json
{
  "id": "okuma.dev_bar4omarchy.clock",
  "format": "yyyy-MM-dd HH:mm",
  "formatAlt": "d MMMM 'W'ww yyyy",
  "verticalFormat": "HH\n—\nmm"
}
```

- Clock: left-click calendar; right-click cycle formats; middle-click timezone menu. Optional `birthYear`, `lifeExpectancy` and `weekStartDay` are not prefilled with personal information.
- Weather: left-click details/city editor; middle-click refresh; right-click Omarchy weather notification. `unit`: `metric` or `imperial`; `refreshMinutes`: default 15, minimum 1. Location uses Omarchy's shared `~/.local/state/omarchy/settings/weather.json`; it is not copied into the project.
- Workspaces: click another workspace to focus; click the active layout glyph to cycle layouts; scroll to navigate.
- RAM: click details; right-click refresh, or use Refresh beside the Available/Cache/Swap summary. Open dismisses the panel and focuses the selected existing window so you can review and close it manually; it never launches another instance. No cache dropping, killing, or window-closing commands. The application list scrolls within a bounded height; the full panel also scrolls when needed on short screens. RSS may count shared memory more than once.
- Agents: use Omarchy's built-in entry for agent status and quota queries. OkumaBar does not bundle a separate quota reader.

The initial world-clock list is Singapore, Los Angeles, New York, London and Dubai; customize the built-in `omarchy.elsewhen` entry as needed.

## Privacy and security

- Weather uses HTTPS `wttr.in`, `api.open-meteo.com` and `geocoding-api.open-meteo.com`; refreshes at startup/every 15 minutes by default and when manually refreshed. It sends the configured location/coordinates/search, or uses the public IP for location detection. Request timeouts and size bounds are enforced; services see your public IP. Disable with `--without-weather`.
- Agent status and quota queries are provided by Omarchy's built-in Agents widget, not a bundled OkumaBar helper.
- Uninstall leaves Omarchy's shared weather location state untouched.
- RAM reads `/proc` and Hyprland clients. It validates process ownership/start time/window identity before focusing the selected window. It never closes windows or terminates processes.
- No credentials, weather state, local caches, personal Dock entries or original full desktop configuration are bundled. Plugins run unsandboxed in Omarchy's shell; review code before installing.

## Marketplace publication

This checkout is a suite/preset, not a root Omarchy plugin. Do not submit it as
`okuma.dev_bar4omarchy` or add a placeholder manifest. New marketplace submissions
require exactly one real plugin manifest at the repository root.

Export the existing widgets as four self-contained root-plugin sources:

```bash
python3 scripts/export_plugins.py ../OkumaBar-publication
for plugin in ../OkumaBar-publication/*; do
  omarchy plugin validate "$plugin"
done
```

The output must be a new directory outside this checkout; existing destinations
are never overwritten. Exporting does not install, enable, edit your bar or make
network requests. Each directory includes its manifest, implementation, README,
MIT license and upstream notices. Publish each as a separate GitHub repository,
replace the README's OWNER/REPOSITORY placeholder and manifest homepage with its
actual URL, and test installation/removal on a live desktop before submitting.
Submit each widget separately, not the enclosing export directory. The original
suite remains the optional complete-layout installer. Exported widgets do not
apply that layout. Marketplace security checks and approval are still required.

## Development

```bash
python3 -m unittest discover -s tests -v
node tests/models.test.cjs
```

Edit `plugins/` for release sources. Installed copies do not automatically sync back to the checkout. User interface text currently follows the original components and is primarily English; full live localization is not yet implemented. Screenshots and validation on additional monitors/Omarchy versions are welcome.

## License

MIT. Original project contributions © 2026 ŌKUMA. Omarchy-derived code retains its upstream MIT notice in [docs/LICENSE-Omarchy](docs/LICENSE-Omarchy); see [provenance](docs/THIRD_PARTY.md).
