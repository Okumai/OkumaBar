import copy
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('manage', ROOT / 'scripts/manage.py')
manage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manage)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = Path(self.temp.name)
        self.original = {
            'version': 1, 'bar': {'position': 'bottom', 'layout': {'left': [{'id': 'llm.clock'}]}},
            'idle': {'lock': 123}, 'plugins': [{'id': 'example.dock', 'pinned': ['private']}],
            'disabledPlugins': ['example.disabled'], 'custom': {'hello': 'world'}}
        manage.atomic_json(self.config / 'shell.json', self.original)
        plugins = self.config / 'plugins'
        plugins.mkdir()
        (plugins / 'llm.clock').mkdir()
        (plugins / 'llm.clock/source').write_text('original local customization')

    def current(self):
        return manage.read_json(self.config / 'shell.json')

    def test_round_trip_preserves_unrelated_settings_and_existing_plugins(self):
        old = self.config / 'plugins' / (manage.PREFIX + 'clock')
        old.mkdir()
        (old / 'custom.txt').write_text('existing namespaced source')
        manage.install(self.config)
        installed = self.current()
        for key in self.original.keys() - {'bar'}:
            self.assertEqual(installed[key], self.original[key])
        self.assertEqual(installed['bar']['position'], 'top')
        with self.assertRaisesRegex(ValueError, 'already installed'):
            manage.install(self.config)
        installed['idle']['lock'] = 456
        manage.atomic_json(self.config / 'shell.json', installed)
        manage.uninstall(self.config)
        expected = copy.deepcopy(self.original)
        expected['idle']['lock'] = 456
        self.assertEqual(self.current(), expected)
        self.assertEqual((old / 'custom.txt').read_text(), 'existing namespaced source')
        self.assertFalse((self.config / 'plugins' / (manage.PREFIX + 'weather')).exists())
        self.assertTrue((self.config / 'plugins/llm.clock/source').exists())

    def test_weather_can_be_excluded(self):
        manage.install(self.config, without_weather=True)
        ids = [e['id'] for entries in self.current()['bar']['layout'].values() for e in entries]
        self.assertNotIn(manage.PREFIX + 'weather', ids)
        manage.uninstall(self.config)
        self.assertEqual(self.current(), self.original)

    def test_bar_edit_requires_explicit_force_and_is_rescued(self):
        manage.install(self.config)
        changed = self.current()
        changed['bar']['position'] = 'bottom'
        manage.atomic_json(self.config / 'shell.json', changed)
        with self.assertRaisesRegex(ValueError, 'Bar changed'):
            manage.uninstall(self.config)
        self.assertEqual(self.current(), changed)
        manage.uninstall(self.config, force=True)
        self.assertEqual(self.current(), self.original)
        self.assertTrue(list(self.config.glob('okumabar-backups/*/before-uninstall-*/shell.json')))

    def test_missing_bar_restores_absence(self):
        original = {'version': 1, 'plugins': []}
        manage.atomic_json(self.config / 'shell.json', original)
        manage.install(self.config)
        manage.uninstall(self.config)
        self.assertEqual(self.current(), original)

    def test_invalid_config_does_not_get_overwritten(self):
        (self.config / 'shell.json').write_text('{invalid')
        with self.assertRaises(ValueError):
            manage.install(self.config)
        self.assertEqual((self.config / 'shell.json').read_text(), '{invalid')
        self.assertFalse((self.config / manage.STATE_NAME).exists())

    def test_failure_rolls_back(self):
        real_atomic = manage.atomic_json

        def fail_state(path, data):
            if path.name == manage.STATE_NAME:
                raise OSError('Simulated write failure')
            real_atomic(path, data)

        with patch.object(manage, 'atomic_json', side_effect=fail_state):
            with self.assertRaises(OSError):
                manage.install(self.config)
        self.assertEqual(self.current(), self.original)
        self.assertFalse(list((self.config / 'plugins').glob(manage.PREFIX + '*')))

    def test_symlink_destination_is_refused(self):
        target = self.config / 'do-not-touch'
        target.mkdir()
        (self.config / 'plugins' / (manage.PREFIX + 'clock')).symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            manage.install(self.config)
        self.assertEqual(self.current(), self.original)


class ConsentTests(unittest.TestCase):
    def test_noninteractive_install_requires_yes(self):
        with patch.object(manage.sys.stdin, 'isatty', return_value=False):
            with self.assertRaisesRegex(ValueError, 'Explicit consent'):
                manage.confirm_install(Path('/example'))
            manage.confirm_install(Path('/example'), assume_yes=True)

    def test_interactive_cancel(self):
        with patch.object(manage.sys.stdin, 'isatty', return_value=True), patch('builtins.input', return_value='n'):
            with self.assertRaisesRegex(ValueError, 'cancelled'):
                manage.confirm_install(Path('/example'))


class ExportTests(unittest.TestCase):
    def test_exports_are_self_contained_and_never_overwrite(self):
        spec = importlib.util.spec_from_file_location('export_plugins', ROOT / 'scripts/export_plugins.py')
        exporter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(exporter)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'release'
            exporter.export_plugins(output)
            self.assertEqual(len(list(output.iterdir())), 4)
            for plugin in output.iterdir():
                subprocess.run(['omarchy', 'plugin', 'validate', str(plugin)], check=True)
                for name in ('README.md', 'LICENSE', 'docs/LICENSE-Omarchy', 'docs/THIRD_PARTY.md'):
                    self.assertTrue((plugin / name).is_file(), name)
                self.assertEqual(len(list(plugin.rglob('manifest.json'))), 1)
            with self.assertRaisesRegex(ValueError, 'existing'):
                exporter.export_plugins(output)
            with self.assertRaisesRegex(ValueError, 'outside'):
                exporter.export_plugins(ROOT / 'must-not-create-release')


class ProjectTests(unittest.TestCase):
    def test_manifests_and_preset(self):
        sources = manage.validate_plugins()
        known = {p.name for p in sources}
        for source in sources:
            manifest = manage.read_json(source / 'manifest.json')
            self.assertEqual(manifest['author'], 'ŌKUMA')
            self.assertEqual(manifest['schemaVersion'], 1)
        for entries in manage.build_bar()['layout'].values():
            for entry in entries:
                self.assertTrue(entry['id'].startswith('omarchy.') or entry['id'] in known)

    def test_sources_have_no_machine_specific_paths(self):
        for path in (ROOT / 'plugins').rglob('*'):
            if path.is_file():
                text = path.read_text()
                self.assertNotIn('/home/llm', text, str(path))
                self.assertNotIn('"llm.', text, str(path))

    def test_weather_dynamic_text_is_plain(self):
        panel = (ROOT / 'plugins' / (manage.PREFIX + 'weather') / 'Panel.qml').read_text()
        # Dynamic weather/city/forecast values must not enter AutoText sinks.
        for block in re.findall(r'\bText\s*\{([^{}]*)\}', panel, re.S):
            if re.search(r'\btext:\s*(?:root\.(?:report|day|bare)|modelData\.)', block):
                self.assertIn('textFormat: Text.PlainText', block)
        self.assertIn('--max-filesize', panel)

    def test_popups_use_builtin_screen_aware_panel(self):
        for widget in ('clock', 'weather', 'ram-cleaner'):
            panel = (ROOT / 'plugins' / (manage.PREFIX + widget) / 'LeftPanel.qml').read_text()
            self.assertIn('import qs.Ui', panel)
            self.assertRegex(panel, r'KeyboardPanel\s*\{')
            self.assertNotIn('anchorWindow.height', panel)

    def test_agents_is_the_only_quota_entry(self):
        ids = [e['id'] for entries in manage.build_bar()['layout'].values() for e in entries]
        self.assertIn('omarchy.agents', ids)
        self.assertFalse(any('codex' in name for name in ids))
        self.assertEqual(len(manage.validate_plugins()), 4)

    def test_ram_bar_label_is_compact(self):
        widget = (ROOT / 'plugins' / (manage.PREFIX + 'ram-cleaner') / 'Widget.qml').read_text()
        self.assertIn('text: root.stats ? "RAM " + root.stats.percent + "%" : "RAM …"', widget)
        self.assertNotIn('stats.percent + "% · "', widget)

    def test_memory_stats_are_read_only(self):
        helper = ROOT / 'plugins' / (manage.PREFIX + 'ram-cleaner') / 'memory.py'
        data = json.loads(subprocess.check_output(['python3', str(helper), 'stats'], text=True))
        self.assertGreater(data['total'], 0)
        self.assertGreaterEqual(data['percent'], 0)
        self.assertLessEqual(data['percent'], 100)


if __name__ == '__main__':
    unittest.main()
