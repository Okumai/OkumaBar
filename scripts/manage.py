#!/usr/bin/env python3
"""Install the OkumaBar preset without replacing unrelated Omarchy settings."""
import argparse
import copy
import datetime
import fcntl
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'okuma.dev_bar4omarchy.'
STATE_NAME = 'okumabar-state.json'


def read_json(path):
    with path.open(encoding='utf-8') as stream:
        result = json.load(stream)
    if not isinstance(result, dict):
        raise ValueError(f'Expected a JSON object: {path}')
    return result


def atomic_json(path, data):
    fd, name = tempfile.mkstemp(prefix='.okumabar-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def check():
    required = ['omarchy', 'quickshell', 'hyprctl', 'curl',
                'omarchy-weather-location', 'omarchy-weather-status',
                'omarchy-menu-timezone', 'omarchy-hyprland-workspace-layout-current',
                'omarchy-hyprland-workspace-layout-toggle']
    missing = [name for name in required if not shutil.which(name)]
    shell = Path(os.environ.get('OMARCHY_PATH', '/usr/share/omarchy')) / 'shell'
    if not (shell / 'Ui/BarWidget.qml').is_file():
        missing.append(str(shell / 'Ui/BarWidget.qml'))
    if missing:
        raise ValueError('Missing dependencies: ' + ', '.join(missing))
    print('Dependencies found. Target: Omarchy 4.5.0 Quickshell shell; not standalone Quickshell.')


def build_bar(without_weather=False):
    bar = read_json(ROOT / 'presets/bar.json')
    excluded = set()
    if without_weather:
        excluded.add(PREFIX + 'weather')
    for section, entries in bar['layout'].items():
        bar['layout'][section] = [e for e in entries if e['id'] not in excluded]
    return bar


def validate_plugins():
    result = []
    for source in sorted((ROOT / 'plugins').iterdir()):
        manifest = read_json(source / 'manifest.json')
        if manifest['id'] != source.name or not source.name.startswith(PREFIX):
            raise ValueError(f'Invalid plugin ID: {source}')
        for entry in manifest['entryPoints'].values():
            path = Path(entry)
            if path.is_absolute() or '..' in path.parts or not (source / path).is_file():
                raise ValueError(f'Invalid entry point: {source}/{entry}')
        result.append(source)
    if len(result) != 4:
        raise ValueError('Expected four bundled plugins')
    return result


def restore_plugins(config_dir, backup, names):
    for name in names:
        dest = config_dir / 'plugins' / name
        if dest.is_dir():
            shutil.rmtree(dest)
        elif dest.exists() or dest.is_symlink():
            dest.unlink()
        saved = backup / 'plugins' / name
        if saved.exists():
            shutil.copytree(saved, dest)


def install(config_dir, without_weather=False):
    state_path = config_dir / STATE_NAME
    if state_path.exists():
        raise ValueError('OkumaBar is already installed. Uninstall before updating/reinstalling.')
    shell_path = config_dir / 'shell.json'
    config = read_json(shell_path)  # Refuse missing/invalid config rather than inventing defaults.
    sources = validate_plugins()
    names = [source.name for source in sources]
    plugins = config_dir / 'plugins'
    plugins.mkdir(exist_ok=True)
    for name in names:
        dest = plugins / name
        if dest.is_symlink() or (dest.exists() and not dest.is_dir()):
            raise ValueError(f'Refusing non-directory/symlink plugin destination: {dest}')
    bar = build_bar(without_weather)
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]
    backup = config_dir / 'okumabar-backups' / stamp
    backup.mkdir(parents=True, mode=0o700)
    shutil.copy2(shell_path, backup / 'shell.json')
    (backup / 'plugins').mkdir()
    for name in names:
        if (plugins / name).exists():
            shutil.copytree(plugins / name, backup / 'plugins' / name)
    state = {'backup': str(backup.resolve()), 'plugins': names, 'installedBar': bar}
    atomic_json(backup / 'snapshot.json', state)
    updated = copy.deepcopy(config)
    updated['bar'] = bar
    try:
        for source in sources:
            dest = plugins / source.name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(source, dest)
        # Code must exist before the hot-reloaded config refers to it.
        atomic_json(shell_path, updated)
        atomic_json(state_path, state)
    except Exception:
        restore_plugins(config_dir, backup, names)
        atomic_json(shell_path, config)
        state_path.unlink(missing_ok=True)
        raise
    print(f'Installed OkumaBar. Backup: {backup}')
    print('Only bar settings changed; idle, Dock, plugins and other top-level settings are preserved.')
    print('Omarchy hot-reloads changes. If needed: omarchy restart shell')


def uninstall(config_dir, force=False):
    state_path = config_dir / STATE_NAME
    state = read_json(state_path)
    backup = Path(state['backup']).resolve()
    if backup.parent != (config_dir / 'okumabar-backups').resolve():
        raise ValueError('Backup path is outside the OkumaBar backup directory')
    names = state['plugins']
    if any(not isinstance(n, str) or not n.startswith(PREFIX) or '/' in n or '..' in n for n in names):
        raise ValueError('Unsafe plugin name in installation state')
    current = read_json(config_dir / 'shell.json')
    original = read_json(backup / 'shell.json')
    if current.get('bar') != state['installedBar'] and not force:
        raise ValueError('Bar changed after installation. Back up your edits, then use uninstall --force to restore the previous bar.')
    # Keep a rescue copy of edits before restoring. Unrelated settings survive.
    rescue = backup / ('before-uninstall-' + uuid.uuid4().hex[:8])
    rescue.mkdir()
    shutil.copy2(config_dir / 'shell.json', rescue / 'shell.json')
    (rescue / 'plugins').mkdir()
    for name in names:
        dest = config_dir / 'plugins' / name
        if dest.is_symlink():
            raise ValueError(f'Refusing symlink plugin destination: {dest}')
        if dest.exists():
            shutil.copytree(dest, rescue / 'plugins' / name)
    if 'bar' in original:
        current['bar'] = original['bar']
    else:
        current.pop('bar', None)
    atomic_json(config_dir / 'shell.json', current)
    restore_plugins(config_dir, backup, names)
    state_path.unlink()
    print(f'Previous bar and plugin files restored. Backups retained: {backup}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['install', 'uninstall', 'check'])
    parser.add_argument('--config-dir', type=Path, default=Path.home() / '.config/omarchy',
                        help='Omarchy config directory (default follows the Omarchy plugin registry)')
    parser.add_argument('--without-weather', action='store_true', help='Do not activate weather/network requests')
    parser.add_argument('--force', action='store_true', help='Uninstall even if bar settings changed')
    args = parser.parse_args()
    try:
        if args.action == 'check':
            check()
            validate_plugins()
            return
        config_dir = args.config_dir.expanduser().resolve()
        if not config_dir.is_dir():
            raise ValueError(f'Config directory does not exist: {config_dir}')
        # Serialize this tool's operations, not Omarchy's own configuration writes.
        with (config_dir / '.okumabar.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if args.action == 'install':
                check()
                install(config_dir, args.without_weather)
            else:
                uninstall(config_dir, args.force)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'OkumaBar: {error}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
