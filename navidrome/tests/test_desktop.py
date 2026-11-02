"""Desktop exports and Windows stylesheet installation use isolated files only."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('setup_desktop', ROOT / 'setup-desktop.py')
desktop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(desktop)


class DesktopSetupTests(unittest.TestCase):
    def workspace(self, directory):
        root = Path(directory) / 'repo'
        root.mkdir()
        for name in (*desktop.THEME_FILES, 'visualizer-presets.json'):
            shutil.copyfile(ROOT / name, root / name)
        return root

    def test_exports_are_individually_importable_with_their_gradients(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.workspace(directory)
            with patch.object(desktop, 'ROOT', root), patch('sys.argv', ['setup-desktop.py']), contextlib.redirect_stdout(io.StringIO()):
                desktop.main()
            destination = root / 'local' / 'desktop'
            configurations = sorted(destination.glob('*.json'))
            self.assertEqual(len(configurations), 3)
            for path in configurations:
                value = json.loads(path.read_text(encoding='utf-8'))
                gradients = {g['name'] for g in value['customGradients']}
                self.assertIn(value['gradient'], gradients)
                if value['channelLayout'] != 'single':
                    self.assertIn(value['gradientLeft'], gradients)
                    self.assertIn(value['gradientRight'], gradients)
                self.assertEqual(value['maxFPS'], 60)
                self.assertNotIn('presets', value)
            self.assertIn('drop-shadow', (destination / 'custom.css').read_text(encoding='utf-8'))

    @unittest.skipUnless(os.name == 'nt', 'Windows profile installation')
    def test_install_backs_up_existing_styles_and_preserves_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.workspace(directory)
            appdata = Path(directory) / 'AppData'
            profile = appdata / 'feishin'
            profile.mkdir(parents=True)
            (profile / 'custom.css').write_bytes(b'/* personal stylesheet */')
            (profile / 'config.json').write_bytes(b'{"untouched":true}')
            with patch.object(desktop, 'ROOT', root), patch.dict(os.environ, APPDATA=str(appdata)), patch('sys.argv', ['setup-desktop.py', '--install-css']), contextlib.redirect_stdout(io.StringIO()):
                desktop.main()
                desktop.main()
            backups = list(profile.glob('custom.css.*.bak'))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), b'/* personal stylesheet */')
            self.assertEqual((profile / 'config.json').read_bytes(), b'{"untouched":true}')
            self.assertEqual((profile / 'custom.css').read_bytes(), (root / 'local' / 'desktop' / 'custom.css').read_bytes())
