import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

HELPER = Path(__file__).resolve().parents[1] / 'plugins/okuma.dev_bar4omarchy.ram-cleaner/memory.py'
spec = importlib.util.spec_from_file_location('memory', HELPER)
memory = importlib.util.module_from_spec(spec)
previous = sys.dont_write_bytecode
try:
    sys.dont_write_bytecode = True
    spec.loader.exec_module(memory)
finally:
    sys.dont_write_bytecode = previous


class WindowFocusTests(unittest.TestCase):
    def run_focus(self, address='0xabc', pid=123, start='456'):
        with patch.object(sys, 'argv', [str(HELPER), 'focus', address, str(pid), start]):
            return memory.main()

    def test_focus_validates_window_and_uses_native_dispatcher(self):
        clients = [{'address': '0xabc', 'pid': 123, 'mapped': True}]
        with patch.object(memory, 'identity', return_value='456') as identity, \
             patch.object(memory, 'clients', return_value=clients), \
             patch.object(memory.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'ok', '')) as run:
            self.assertIn('Window focused', self.run_focus()['message'])
            identity.assert_called_once_with(123)
            run.assert_called_once_with(
                ['hyprctl', 'dispatch', 'hl.dsp.focus({ window = "address:0xabc" })'],
                capture_output=True, text=True, timeout=3)

    def test_stale_process_is_not_focused(self):
        with patch.object(memory, 'identity', return_value='other'), \
             patch.object(memory.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'Application changed'):
                self.run_focus()
            run.assert_not_called()

    def test_changed_window_is_not_focused(self):
        for clients in ([], [{'address': '0xabc', 'pid': 124, 'mapped': True}],
                        [{'address': '0xabc', 'pid': 123, 'mapped': False}]):
            with self.subTest(clients=clients), \
                 patch.object(memory, 'identity', return_value='456'), \
                 patch.object(memory, 'clients', return_value=clients), \
                 patch.object(memory.subprocess, 'run') as run:
                with self.assertRaisesRegex(ValueError, 'Window has closed or changed'):
                    self.run_focus()
                run.assert_not_called()

    def test_lua_injection_is_rejected(self):
        with patch.object(memory.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'Invalid window address'):
                self.run_focus('0xabc" }); os.execute("bad")')
            run.assert_not_called()

    def test_dispatch_failure_reports_hyprland_error(self):
        with patch.object(memory, 'identity', return_value='456'), \
             patch.object(memory, 'clients', return_value=[{'address': '0xabc', 'pid': 123, 'mapped': True}]), \
             patch.object(memory.subprocess, 'run', return_value=subprocess.CompletedProcess([], 7, 'dispatch failed', '')):
            with self.assertRaisesRegex(ValueError, 'Unable to focus window: dispatch failed'):
                self.run_focus()

    def test_old_close_action_is_not_available(self):
        with patch.object(sys, 'argv', [str(HELPER), 'close']), \
             patch.object(memory.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'Unknown action'):
                memory.main()
            run.assert_not_called()

    def test_checker_name_and_centered_compact_panel(self):
        import json
        manifest = json.loads(HELPER.with_name('manifest.json').read_text())
        self.assertEqual(manifest['name'], 'OkumaBar RAM Checker')
        self.assertEqual(manifest['barWidget']['displayName'], 'OkumaBar RAM Checker')
        widget = HELPER.with_name('Widget.qml').read_text()
        self.assertIn('text: "RAM Checker"', widget)
        self.assertIn('horizontalAlignment: Text.AlignHCenter', widget)
        self.assertIn('fittedContentWidth(Style.space(400))', widget)
        self.assertIn('fontSizeMode: Text.HorizontalFit', widget)

    def test_panel_and_application_list_have_bounded_scrolling(self):
        widget = HELPER.with_name('Widget.qml').read_text()
        self.assertIn('fittedContentHeight(content.implicitHeight, Style.space(640))', widget)
        self.assertIn('height: Math.min(Style.space(240), popup.availableCardHeight * 0.35,', widget)
        self.assertEqual(widget.count('interactive: contentHeight > height'), 2)
        self.assertEqual(widget.count('policy: Controls.ScrollBar.AsNeeded'), 2)
        self.assertIn('width: ListView.view.width - Style.space(12)', widget)

    def test_ui_has_focus_action_and_summary_refresh(self):
        widget = HELPER.with_name('Widget.qml').read_text()
        self.assertIn('text: "Open"', widget)
        self.assertIn('root.openWindow(modelData)', widget)
        self.assertIn('anchors.right: refreshButton.left', widget)
        self.assertIn('id: refreshButton', widget)
        self.assertNotIn('Confirm close', widget)
        self.assertNotIn('id: closer', widget)
        self.assertNotIn('root.pending', widget)


if __name__ == '__main__':
    unittest.main()
