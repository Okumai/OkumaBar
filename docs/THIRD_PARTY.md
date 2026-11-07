# Provenance and third-party notices

OkumaBar is maintained by ŌKUMA: https://github.com/Okumai/Bar (`okuma.dev_bar4omarchy`). It is an independent community project, not an official Omarchy release.

## Omarchy

Upstream: https://github.com/omacom/omarchy

License: MIT. Copyright (c) David Heinemeier Hansson.

The complete upstream license is retained in [LICENSE-Omarchy](LICENSE-Omarchy). The license was retrieved from upstream during project assembly. The source desktop reported Omarchy package version `4.5.0-3`; the historical upstream commit for the earlier local clones was not recorded, so this project does not claim an exact commit-level provenance.

The clock, weather and workspace components were collected from the author's existing user customizations (`llm.clock`, `llm.weather`, `llm.workspaces`). Their manifests identify them as clones of `omarchy.clock`, `omarchy.weather` and `omarchy.workspaces`. Their QML/JS contains or derives from Omarchy code. The clock, weather and RAM components use small `LeftPanel.qml` adapters to Omarchy's built-in `KeyboardPanel`, sharing its screen-aware positioning and motion. Original upstream notices and the upstream license apply to derived portions.

The RAM widget/helper was collected from the author's existing local customization (`llm.ram-cleaner`). OkumaBar adds packaging, project metadata, namespaced manifests, bounded network responses, installation/restore tooling, documentation and tests.

Canonical `omarchy.*` module/IPC identifiers in cloned clock/weather/workspace QML are intentionally retained to integrate with upstream hotkeys and clone routing. Manifests and layout IDs use the OkumaBar namespace. Do not activate multiple clones of the same upstream component in one layout; duplicate canonical IPC handlers can conflict.

Built-in bar widgets and `qs.Ui` / `qs.Commons` imports are runtime dependencies from the installed Omarchy Shell, not bundled replacement implementations. No Dock or Launchpad source is included.

## External services

Weather uses wttr.in and Open-Meteo. Their data/service terms apply independently of this repository's code license. Agent status and quota queries are handled by Omarchy's built-in Agents widget and its own service integrations. No external service or data is relicensed by this project.
