#!/usr/bin/env python3
"""Read-only memory diagnostics and validated focus of existing windows."""
import json
import os
import re
from pathlib import Path
import subprocess
import sys


def clients():
    return json.loads(subprocess.check_output(['hyprctl', '-j', 'clients'], timeout=3))


def identity(pid):
    path = Path('/proc') / str(pid)
    if path.stat().st_uid != os.getuid():
        raise ValueError('Application does not belong to the current user')
    fields = (path / 'stat').read_text().rsplit(')', 1)[1].split()
    return fields[19]


def memory():
    values = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, value = line.split(':', 1)
        values[key] = int(value.split()[0]) * 1024
    total = values['MemTotal']
    available = values['MemAvailable']
    return dict(total=total, available=available, used=total-available,
                percent=round(100*(total-available)/total),
                cache=values['Cached'] + values['SReclaimable'],
                swap=values['SwapTotal']-values['SwapFree'])


def windows():
    # RSS includes shared pages: an estimate, not guaranteed reclaimable RAM.
    processes = {}
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():
            continue
        try:
            if path.stat().st_uid != os.getuid():
                continue
            fields = (path / 'stat').read_text().rsplit(')', 1)[1].split()
            processes[int(path.name)] = (int(fields[1]), int(fields[21])*os.sysconf('SC_PAGE_SIZE'))
        except (OSError, ValueError, IndexError):
            pass
    result = []
    for client in clients():
        if not client.get('mapped'):
            continue
        pid = client['pid']
        try:
            start = identity(pid)
        except (OSError, ValueError):
            continue
        descendants = {pid}
        while True:
            expanded = descendants | {p for p, (parent, _) in processes.items() if parent in descendants}
            if expanded == descendants:
                break
            descendants = expanded
        result.append(dict(address=client['address'], pid=pid, start=start,
                           name=client.get('class') or 'App', title=client.get('title', ''),
                           rss=sum(processes.get(p, (0, 0))[1] for p in descendants)))
    return sorted(result, key=lambda row: row['rss'], reverse=True)


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else 'stats'
    if action == 'focus':
        address, pid_text, start = sys.argv[2:]
        # Only a window address may enter the Lua dispatcher, never arbitrary text.
        if not re.fullmatch(r'0x[0-9a-fA-F]+', address):
            raise ValueError('Invalid window address')
        pid = int(pid_text)
        if identity(pid) != start:
            raise ValueError('Application changed; refresh and try again')
        if not any(c['address'] == address and c['pid'] == pid and c.get('mapped') for c in clients()):
            raise ValueError('Window has closed or changed')
        command = 'hl.dsp.focus({ window = ' + json.dumps('address:' + address) + ' })'
        result = subprocess.run(['hyprctl', 'dispatch', command],
                                capture_output=True, text=True, timeout=3)
        if result.returncode:
            detail = (result.stderr or result.stdout).strip()[:500]
            raise ValueError('Unable to focus window: ' + (detail or 'Hyprland rejected the request'))
        return {'message': 'Window focused. Close it manually if no longer needed.'}
    data = memory()
    if action == 'details':
        data['windows'] = windows()
    elif action != 'stats':
        raise ValueError('Unknown action')
    return data


if __name__ == '__main__':
    try:
        print(json.dumps(main(), ensure_ascii=False))
    except Exception as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False))
        sys.exit(1)
