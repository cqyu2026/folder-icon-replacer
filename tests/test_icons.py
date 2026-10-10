import contextlib
import io
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import icons
from png_codec import decode, encode


class IconsTest(unittest.TestCase):
    def setUp(self):
        output = ROOT/'.build/tests'
        output.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=output)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.image = self.work/'03.png'
        self.pixels = bytearray(128*128*4)
        for y in range(24, 108):
            for x in range(16, 112):
                self.pixels[(y*128+x)*4:(y*128+x)*4+4] = bytes((130, 80, 190, 255))
        self.image.write_bytes(encode(128, 128, self.pixels))

    def test_valid_png_and_crc(self):
        self.assertEqual(icons.inspect(self.image)['status'], 'technical_pass')
        broken = bytearray(self.image.read_bytes())
        broken[-5] ^= 1
        with self.assertRaises(ValueError):
            decode(broken)

    def test_edge_and_isolated_pixel(self):
        self.pixels[3] = 1
        self.pixels[(10*128+10)*4+3] = 255
        self.image.write_bytes(encode(128, 128, self.pixels))
        errors = icons.inspect(self.image)['errors']
        self.assertIn('canvas_edges_not_fully_transparent', errors)
        self.assertIn('isolated_visible_pixels', errors)

    def test_blank_and_opaque_rejected(self):
        for alpha in (0, 255):
            self.image.write_bytes(encode(128, 128, bytes((120, 80, 200, alpha))*128*128))
            self.assertEqual(icons.inspect(self.image)['status'], 'failed')

    def test_non_mac_stops(self):
        with patch.object(sys, 'platform', 'linux'), patch.object(sys, 'argv',
                ['icons.py', 'check', str(self.image)]), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(icons.main(), 1)

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS only')
    def test_preview_sizes_and_backgrounds(self):
        paths = icons.previews(self.image, self.work/'previews')
        self.assertEqual(len(paths), 9)
        for path in paths:
            w, h, pixels = decode(Path(path).read_bytes())
            self.assertEqual(w, int(Path(path).name.split('-')[0]))
            self.assertEqual(w, h)
            self.assertEqual(min(pixels[3::4]), 255)

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS only')
    def test_native_apply_and_terminal_command(self):
        target = self.work/"旅行 ' 引号 空格"
        target.mkdir()
        sentinel = target/'contents.txt'
        sentinel.write_bytes(b'keep ordinary contents unchanged')
        nested = target/'nested'; nested.mkdir()
        (nested/'data').write_bytes(b'untouched')
        command = subprocess.check_output([sys.executable, str(ROOT/'scripts/icons.py'),
                    'command', str(self.image), str(target)], text=True).strip()
        self.assertEqual(shlex.split(command)[-2:], [str(self.image), str(target)])
        for _ in range(2):
            result = subprocess.run(['/bin/sh', '-c', command], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            self.assertRegex(result.stdout, r'icon_status=(verified|already_selected)')
        self.assertEqual(sentinel.read_bytes(), b'keep ordinary contents unchanged')
        self.assertEqual((nested/'data').read_bytes(), b'untouched')

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS only')
    def test_rejected_targets_and_image_change(self):
        binary = icons.build()
        target = self.work/'target'; target.mkdir()
        app = self.work/'test.app'; app.mkdir()
        link = self.work/'link'; link.symlink_to(target)
        digest = icons.inspect(self.image)['sha256']
        for rejected in (app, link, Path('/System')):
            identity = rejected.lstat()
            result = subprocess.run([str(binary), 'set-and-verify', str(self.image),
                    str(rejected), str(identity.st_dev), str(identity.st_ino), digest],
                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0, result.stdout+result.stderr)
        identity = target.stat()
        result = subprocess.run([str(binary), 'set-and-verify', str(self.image), str(target),
                str(identity.st_dev), str(identity.st_ino), '0'*64], capture_output=True, text=True)
        self.assertIn('image_changed_after_check', result.stderr)
        self.assertEqual(list(target.iterdir()), [])

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS only')
    def test_bad_png_never_applies(self):
        target = self.work/'target'; target.mkdir()
        self.pixels[3] = 1
        self.image.write_bytes(encode(128, 128, self.pixels))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(icons.apply(self.image, target), 1)
        self.assertEqual(list(target.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
