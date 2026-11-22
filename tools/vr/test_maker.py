"""Synthetic checks for the local PC Maker (no game files or build required)."""
import tempfile
import unittest
import os
import shutil
import subprocess
from pathlib import Path

from maker import (Config, MakerError, RunLogger, build, copy_game_files, cpu_make_args, sysroot_openxr,
                   validate_game_files, validate_ref)

ROOT = Path(__file__).resolve().parents[2]


class MakerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'fake-extracted'
        (self.root / 'exefs').mkdir(parents=True)
        (self.root / 'romfs' / 'System').mkdir(parents=True)
        (self.root / 'exefs' / 'main').write_bytes(b'NSO0synthetic fixture')
        for name in ('main.npdm', 'rtld', 'sdk', 'subsdk0'):
            (self.root / 'exefs' / name).write_bytes(b'synthetic')
        (self.root / 'romfs' / 'System' / 'Version.txt').write_text('1.9.0\n')
        (self.root / 'save').mkdir()
        (self.root / 'save' / 'user.sav').write_bytes(b'not a game asset')

    def tearDown(self):
        self.temp.cleanup()

    def test_validates_synthetic_game_tree(self):
        root, version = validate_game_files(self.root)
        self.assertEqual(root, self.root.resolve())
        self.assertEqual(version, '1.9.0')

    def test_rejects_wrong_game_version(self):
        (self.root / 'romfs' / 'System' / 'Version.txt').write_text('1.8.2\n')
        with self.assertRaisesRegex(MakerError, '1.9.0'):
            validate_game_files(self.root)

    def test_copies_only_allowlisted_game_files(self):
        (self.root / 'aoc1').mkdir()
        (self.root / 'aoc1' / 'synthetic.txt').write_text('DLC fixture')
        dest = Path(self.temp.name) / 'copy'
        copy_game_files(self.root, dest, lambda _message: None)
        self.assertTrue((dest / 'exefs' / 'main').is_file())
        self.assertTrue((dest / 'aoc1' / 'synthetic.txt').is_file())
        self.assertFalse((dest / 'save').exists())

    def test_validates_git_refs(self):
        validate_ref('main')
        validate_ref('vr-2026.11.21')
        with self.assertRaises(MakerError):
            validate_ref('--upload-pack=bad')
        with self.assertRaises(MakerError):
            validate_ref('branch name')

    def test_cpu_profile_args_match_requested_target(self):
        c = Config('linux', self.root, Path(self.temp.name) / 'output', cpu='v2')
        self.assertEqual(cpu_make_args(c), ['GENARCH=-march=x86-64-v2', 'GENARCH_COMPAT='])
        c = Config('steamframe', self.root, Path(self.temp.name) / 'output', cpu='v3')
        self.assertEqual(cpu_make_args(c), [])

    def test_finds_openxr_loader_in_arm64_sysroot(self):
        sysroot = Path(self.temp.name) / 'sysroot'
        loader = sysroot / 'usr' / 'lib' / 'aarch64-linux-gnu' / 'libopenxr_loader.so.1'
        loader.parent.mkdir(parents=True)
        loader.write_bytes(b'synthetic ARM64 loader')
        self.assertEqual(sysroot_openxr(sysroot), loader.resolve())

    def test_refuses_existing_output_without_touching_it(self):
        output = Path(self.temp.name) / 'existing-output'
        output.mkdir()
        marker = output / 'keep.txt'
        marker.write_text('user data')
        with self.assertRaisesRegex(MakerError, 'ya existe'):
            build(Config('linux', self.root, output), lambda _message: None)
        self.assertEqual(marker.read_text(), 'user data')

    def test_run_log_keeps_timestamped_messages_for_attachment(self):
        path = Path(self.temp.name) / 'logs' / 'pc-maker.log'
        log = RunLogger(path)
        log('build step: compiling game library')
        log.close()
        text = path.read_text()
        self.assertIn(' UTC] build step: compiling game library', text)

    @unittest.skipUnless(os.name == 'posix', 'AppRun uses a POSIX shell')
    def test_maker_apprun_uses_sibling_data_and_defaults_to_vr(self):
        package = Path(self.temp.name) / 'package'
        appdir = package / 'AppDir'
        (appdir / 'usr' / 'bin').mkdir(parents=True)
        (package / 'data' / 'extracted').mkdir(parents=True)
        image = package / 'build.AppImage'
        image.write_bytes(b'synthetic')
        app = appdir / 'usr' / 'bin' / 'savagewind'
        app.write_text('#!/bin/sh\nprintf "%s\\n%s\\n" "$SAVAGEWIND_DATA_ROOT" "$SAVAGEWIND_VR"\n')
        app.chmod(0o755)
        apprun = appdir / 'AppRun'
        apprun.write_bytes((ROOT / 'tools/linux/AppRun.maker').read_bytes())
        run = subprocess.run(['sh', str(apprun)],
                             env=dict(os.environ, APPIMAGE=str(image)), text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
        self.assertEqual(run.stdout.splitlines(), [str(package / 'data'), '1'])

    @unittest.skipUnless(os.name == 'posix', 'AppRun uses a POSIX shell')
    def test_appruns_log_pre_runtime_loader_errors_and_show_log_path(self):
        fake_bin = Path(self.temp.name) / 'bin'
        fake_bin.mkdir()
        for name in ('date', 'dirname', 'grep', 'id', 'mkdir', 'mv', 'readlink', 'sed', 'tail', 'uname'):
            source = shutil.which(name)
            if source:
                (fake_bin / name).symlink_to(source)
        env = {key: value for key, value in os.environ.items()
               if key not in ('SAVAGEWIND_DATA_ROOT', 'XDG_DATA_HOME', 'PATH', 'APPIMAGE')}
        env.update({'HOME': str(Path(self.temp.name) / 'home'), 'PATH': str(fake_bin)})
        for wrapper_name in ('AppRun', 'AppRun.maker'):
            with self.subTest(wrapper=wrapper_name):
                package = Path(self.temp.name) / wrapper_name
                appdir = package / 'AppDir'
                runtime = appdir / 'usr' / 'bin' / 'savagewind'
                runtime.parent.mkdir(parents=True)
                runtime.write_text('#!/bin/sh\nprintf "%s\\n" "savagewind: error while loading shared libraries: '
                                   'libSDL3.so.0: cannot open shared object file: No such file or directory" >&2\nexit 127\n')
                runtime.chmod(0o755)
                wrapper = appdir / 'AppRun'
                wrapper.write_bytes((ROOT / 'tools' / 'linux' / wrapper_name).read_bytes())
                wrapper.chmod(0o755)
                if wrapper_name == 'AppRun.maker':
                    (package / 'data' / 'extracted').mkdir(parents=True)
                    image = package / 'build.AppImage'
                    image.write_bytes(b'synthetic image')
                    env['APPIMAGE'] = str(image)
                else:
                    env.pop('APPIMAGE', None)
                run = subprocess.run(['/bin/sh', str(wrapper)], cwd=self.temp.name, env=env, text=True,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
                self.assertEqual(run.returncode, 127)
                self.assertIn('required Linux library is missing', run.stdout)
                self.assertIn('Detailed log:', run.stdout)
                log_path = (package / 'data' / 'savagewind-launcher.log' if wrapper_name == 'AppRun.maker'
                            else Path(env['HOME']) / '.local' / 'share' / 'savagewind' / 'savagewind-launcher.log')
                self.assertIn(str(log_path), run.stdout)
                self.assertIn('libSDL3.so.0', log_path.read_text())
                self.assertIn('Runtime exit status: 127', log_path.read_text())
                runtime.unlink()
                missing = subprocess.run(['/bin/sh', str(wrapper)], cwd=self.temp.name, env=env, text=True,
                                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
                self.assertEqual(missing.returncode, 127)
                self.assertIn('runtime executable is missing', missing.stdout)
                self.assertIn('ERROR: runtime executable is missing', log_path.read_text())
                self.assertIn('libSDL3.so.0', log_path.with_name('savagewind-launcher.prev.log').read_text())
        popup = fake_bin / 'zenity'
        popup.write_text('#!/bin/sh\nprintf "%s\\n" "$*" > "$POPUP_CAPTURE"\n')
        popup.chmod(0o755)
        env['POPUP_CAPTURE'] = str(Path(self.temp.name) / 'popup.txt')
        run = subprocess.run(['/bin/sh', str(wrapper)], cwd=self.temp.name, env=env, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        self.assertEqual(run.returncode, 127)
        self.assertEqual(run.stdout, '')
        self.assertIn('runtime executable is missing', Path(env['POPUP_CAPTURE']).read_text())
        self.assertIn(str(log_path), Path(env['POPUP_CAPTURE']).read_text())

    @unittest.skipUnless(os.name == 'posix', 'AppRun uses a POSIX shell')
    def test_packaged_vr_apprun_defaults_to_vr_mode(self):
        appdir = Path(self.temp.name) / 'AppDir'
        (appdir / 'usr' / 'bin').mkdir(parents=True)
        runtime = appdir / 'usr' / 'bin' / 'savagewind'
        runtime.write_text('#!/bin/sh\nprintf "vr=%s\\n" "${SAVAGEWIND_VR:-0}"\n')
        runtime.chmod(0o755)
        wrapper = appdir / 'AppRun'
        wrapper.write_bytes((ROOT / 'tools' / 'linux' / 'AppRun').read_bytes())
        wrapper.chmod(0o755)
        subprocess.run(['sed', '-i', 's|^# SAVAGEWIND_VR_DEFAULT$|export SAVAGEWIND_VR=${SAVAGEWIND_VR:-1}|',
                        str(wrapper)], check=True)
        env = {key: value for key, value in os.environ.items() if key not in ('SAVAGEWIND_VR', 'SAVAGEWIND_DATA_ROOT')}
        env['HOME'] = str(Path(self.temp.name) / 'home')
        run = subprocess.run(['/bin/sh', str(wrapper)], cwd=self.temp.name, env=env, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
        self.assertEqual(run.stdout.strip(), 'vr=1')


if __name__ == '__main__':
    unittest.main()
