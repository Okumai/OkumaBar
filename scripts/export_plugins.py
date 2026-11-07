#!/usr/bin/env python3
"""Export self-contained root-plugin repositories; never install or activate them."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def export_plugins(output):
    output = Path(output).expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise ValueError(f'Refusing existing export destination: {output}')
    if output.is_relative_to(ROOT):
        raise ValueError('Export outside the source checkout to avoid nested plugin manifests')
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.okumabar-export-', dir=output.parent))
    try:
        for source in sorted((ROOT / 'plugins').iterdir()):
            if not source.is_dir() or source.is_symlink():
                raise ValueError(f'Unexpected plugin directory: {source}')
            if any(p.is_symlink() for p in source.rglob('*')):
                raise ValueError(f'Symlinks are not allowed: {source}')
            manifest = json.loads((source / 'manifest.json').read_text())
            plugin_id = manifest['id']
            if plugin_id != source.name:
                raise ValueError(f'Plugin identity mismatch: {source}')
            dest = stage / plugin_id
            shutil.copytree(source, dest, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            shutil.copy2(ROOT / 'LICENSE', dest / 'LICENSE')
            (dest / 'docs').mkdir(exist_ok=True)
            for name in ('LICENSE-Omarchy', 'THIRD_PARTY.md'):
                shutil.copy2(ROOT / 'docs' / name, dest / 'docs' / name)
            # Full provenance, dependencies and privacy disclosure travel with each widget.
            shutil.copy2(ROOT / 'README.md', dest / 'docs/SUITE.md')
            (dest / 'README.md').write_text(f'''# {manifest['name']}

{manifest['description']}

Author: ŌKUMA. Plugin ID: `{plugin_id}`. License: MIT; see
[LICENSE](LICENSE), [upstream license](docs/LICENSE-Omarchy) and
[provenance](docs/THIRD_PARTY.md).

## Requirements

Omarchy's Quickshell shell with schema-version-1 bar widgets and shared
`qs.Commons` / `qs.Ui` APIs, Hyprland, Python 3, curl and a Nerd Font.
This is not a standalone Quickshell configuration or a Waybar widget.
See [suite documentation](docs/SUITE.md) for required Omarchy helper commands,
compatibility limitations and component settings.

## Install and remove

Publish this directory as its own public GitHub repository with these files at
the root. Review all source first: plugins execute unsandboxed as your user.
Replace OWNER/REPOSITORY below with that repository before publication:

```bash
omarchy plugin add https://github.com/OWNER/REPOSITORY.git --enable
omarchy bar put {plugin_id} --section left
```

Only this widget is installed; the complete OkumaBar preset is not applied.
Enabling may replace its built-in counterpart when clone metadata is present;
review the bar layout first. Save desired settings before removal:

```bash
omarchy plugin disable {plugin_id}
omarchy plugin remove {plugin_id}
```

Omarchy asks for removal confirmation. Do not delete shell.json or restore an
entire old config over later user edits. Local-copy installations are backed up
by Omarchy; saved state and backups are not securely erased.

## Privacy and behavior

The weather widget contacts wttr.in and Open-Meteo over HTTPS, sending location,
coordinates or search terms; IP-based location detection exposes your public IP.
It refreshes at startup and periodically (15 minutes by default). Services see
your public IP. Do not enable weather if you do not consent to these requests.
Weather location is shared Omarchy state and is not deleted on removal.
Clock, workspace and RAM widgets do not include these weather requests.
RAM reads /proc and Hyprland client metadata and can focus an existing window;
it does not kill processes, close windows or drop caches.
Full details: [suite privacy and configuration](docs/SUITE.md).

## Validate before submission

```bash
omarchy plugin validate .
```

Set the actual repository URL in this README and manifest homepage, test on a
live Omarchy desktop, then submit this repository separately. Structural
validation does not replace marketplace security checks or maintainer approval.
''', encoding='utf-8')
        stage.rename(output)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='New directory outside this checkout')
    args = parser.parse_args()
    try:
        output = export_plugins(args.output)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f'Export failed: {error}\n')
    print(f'Exported independent plugin sources to {output}; nothing installed or enabled.')


if __name__ == '__main__':
    main()
