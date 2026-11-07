# Contributing

Thanks for contributing to OkumaBar by ŌKUMA.

1. Open an issue or pull request at https://github.com/Okumai/Bar.
2. Include Omarchy/Quickshell/Hyprland versions and a description of the monitor layout.
3. Keep changes under this checkout. Never modify packaged `/usr/share/omarchy/` files.
4. Keep plugin IDs under `okuma.dev_bar4omarchy.*` and preserve Omarchy clone metadata/attribution.
5. Run `python3 -m unittest discover -s tests -v` and `node tests/models.test.cjs`.
6. For QML changes, test on a disposable profile/desktop as well as parsing with Qt tooling. Report any missing visual/runtime verification.

Installer tests use temporary directories; they must not change your actual desktop or use real credentials/network requests. Keep unrelated settings intact and preserve restoration paths.

Treat network responses, process/window names and configuration as untrusted. Use `Text.PlainText`, validate and bound downloaded data, keep HTTPS endpoints explicit, never interpolate downloaded text into shell commands, and add regression tests. Plugins are unsandboxed. Never commit auth files, caches, private configuration or screenshots containing personal data.

For animation changes use `Style.duration()` and honor disabled animations. New UI work should use Omarchy's translation APIs; existing components are not fully localized yet.

Do not commit personal birth dates, weather state or full `shell.json` exports. Add sanitized presets instead. Preserve upstream MIT notices. Contributions are submitted under this project's MIT license.

Before release, add clean screenshots, test install/uninstall on a supported Omarchy desktop, and verify multi-monitor behavior. For updates uninstall the previous installation first so the restore snapshot stays meaningful.
