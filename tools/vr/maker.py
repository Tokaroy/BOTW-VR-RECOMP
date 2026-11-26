#!/usr/bin/env python3
"""Build a local, transfer-ready BOTW VR package from a GitHub ref and the user's own game files.

Run without arguments for the Tk UI, or use:
  python tools/vr/maker.py --target steamframe --game-files /path/to/extracted --output /path/to/package \
      --sysroot /path/to/aarch64-sysroot --ref main

The selected game files and generated game library stay local. Nothing is uploaded.
"""
import argparse
import ctypes
import os
import platform
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_SOURCE = 'https://github.com/guideahon/BOTW-VR-RECOMP.git'
DEFAULT_REF = 'main'
RUNNING_REPO = Path(__file__).resolve().parents[2]
EXEFS_REQUIRED = ('main', 'main.npdm', 'rtld', 'sdk', 'subsdk0')
GAME_ITEMS = ('exefs', 'romfs', 'romfs.bin') + tuple('aoc{}'.format(i) for i in range(1, 9)) \
    + tuple('aoc{}.bin'.format(i) for i in range(1, 9))
VERSION_RE = re.compile(r'^#define SAVAGEWIND_VERSION "([^"]+)"', re.M)


def botwvr_version(repo):
    """BOTW VR's own version (runtime/vr/botwvr_version.h): <phase>-<release>"""
    text = (repo / 'runtime/vr/botwvr_version.h').read_text(encoding='utf-8')
    phase = re.search(r'^#define BOTWVR_PHASE "([^"]+)"', text, re.M).group(1)
    release = re.search(r'^#define BOTWVR_RELEASE "([^"]+)"', text, re.M).group(1)
    return phase + '-' + release


class MakerError(RuntimeError):
    pass


class RunLogger:
    def __init__(self, path, sink=None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = self.path.open('x', encoding='utf-8', buffering=1)
        self.sink = sink
        self.lock = threading.Lock()

    def __call__(self, message):
        line = '[{}] {}'.format(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'), message)
        with self.lock:
            self.stream.write(line + '\n')
            self.stream.flush()
        if self.sink:
            self.sink(str(message))

    def exception(self, error):
        self('ERROR: {}'.format(error))
        self('Traceback:')
        for line in traceback.format_exc().rstrip().splitlines():
            self(line)

    def close(self):
        with self.lock:
            if not self.stream.closed:
                self.stream.flush()
                self.stream.close()


def create_run_logger(config, sink=None):
    log_dir = Path.home() / 'Savage Wind VR Maker Logs'
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    target = config.target if hasattr(config, 'target') else str(config)
    for suffix in range(100):
        name = 'pc-maker-{}-{}-{}{}.log'.format(target, stamp, os.getpid(),
                                                '-{}'.format(suffix) if suffix else '')
        try:
            return RunLogger(log_dir / name, sink)
        except FileExistsError:
            continue
    raise MakerError('No se pudo crear un log único en {}'.format(log_dir))


@dataclass
class Config:
    target: str
    game_files: Path
    output: Path
    source: str = DEFAULT_SOURCE
    ref: str = DEFAULT_REF
    sysroot: Path = None
    cpu: str = 'auto'
    jobs: int = max(1, min(os.cpu_count() or 1, 8))
    keep_work: bool = False


def log_command(command, cwd, env, log):
    shown = subprocess.list2cmdline([str(x) for x in command]) if os.name == 'nt' else ' '.join(
        "'{}'".format(str(x).replace("'", "'\\''")) for x in command)
    log('$ ' + shown)
    try:
        proc = subprocess.Popen(command, cwd=str(cwd) if cwd else None, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace',
                                bufsize=1)
    except OSError as e:
        raise MakerError('{}: {}'.format(command[0], e)) from e
    assert proc.stdout is not None
    for line in proc.stdout:
        log(line.rstrip())
    code = proc.wait()
    if code:
        raise MakerError('{} exited with status {}'.format(Path(str(command[0])).name, code))


def run_capture(command, cwd=None, env=None):
    return subprocess.run(command, cwd=str(cwd) if cwd else None, env=env, text=True,
                          encoding='utf-8', errors='replace', stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, check=False)


def is_within(path, parent):
    try:
        Path(path).resolve().relative_to(Path(parent).resolve())
        return True
    except ValueError:
        return False


def validate_ref(ref):
    if not ref or ref.startswith('-') or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/-]{0,127}', ref):
        raise MakerError('El ref debe ser un nombre de rama, tag o hash, sin espacios.')


def game_root(path):
    root = Path(path).expanduser().resolve()
    for candidate in (root, root / 'extracted'):
        if (candidate / 'exefs').is_dir() and (candidate / 'romfs').is_dir():
            return candidate
    raise MakerError('Elegí la carpeta que contiene exefs/ y romfs/ (o su carpeta padre).')


def validate_game_files(path):
    root = game_root(path)
    missing = [name for name in EXEFS_REQUIRED if not (root / 'exefs' / name).is_file()]
    if missing:
        raise MakerError('Faltan archivos de ExeFS: ' + ', '.join(missing))
    with (root / 'exefs' / 'main').open('rb') as f:
        magic = f.read(4)
    if magic != b'NSO0':
        raise MakerError('ExeFS/main no parece un NSO válido (se esperaba NSO0).')
    version_file = root / 'romfs' / 'System' / 'Version.txt'
    if not version_file.is_file():
        raise MakerError('No se encontró romfs/System/Version.txt; seleccioná la raíz de RomFS.')
    version = version_file.read_text(errors='replace').strip()
    if '1.9.0' not in version:
        raise MakerError('El Maker requiere los archivos de BOTW 1.9.0; RomFS informa {!r}.'.format(version))
    if (root / 'romfs' / 'System' / 'AocVersion.txt').exists():
        raise MakerError('La carpeta romfs elegida parece ser el DLC; seleccioná el RomFS principal.')
    return root, version


def copy_game_files(src, dest, log):
    dest.mkdir(parents=True)
    for name in GAME_ITEMS:
        item = src / name
        if not item.exists():
            continue
        target = dest / name
        if item.is_dir():
            log('Copiando archivos locales del juego: ' + name)
            shutil.copytree(item, target, symlinks=False, ignore=shutil.ignore_patterns('.DS_Store'))
        elif item.is_file():
            shutil.copy2(item, target, follow_symlinks=True)


def detect_cpu_profile():
    machine = platform.machine().lower()
    if machine not in ('x86_64', 'amd64', 'x64'):
        return 'v2'
    if sys.platform == 'win32':
        try:
            kernel = ctypes.windll.kernel32
            if kernel.IsProcessorFeaturePresent(40):  # PF_AVX2_INSTRUCTIONS_AVAILABLE
                return 'v3'
        except Exception:
            pass
    else:
        try:
            flags = set()
            for line in Path('/proc/cpuinfo').read_text(errors='replace').splitlines():
                if line.lower().startswith(('flags', 'features')) and ':' in line:
                    flags.update(line.split(':', 1)[1].lower().split())
            if {'avx2', 'fma', 'bmi2'} <= flags:
                return 'v3'
        except OSError:
            pass
    return 'v2'


def cpu_make_args(config):
    if config.target == 'steamframe':
        return []
    profile = detect_cpu_profile() if config.cpu == 'auto' else config.cpu
    if profile not in ('v2', 'v3'):
        raise MakerError('CPU target inválido: elegí auto, v2 o v3.')
    return ['GENARCH=-march=x86-64-' + profile, 'GENARCH_COMPAT=']


def sysroot_openxr(sysroot):
    candidates = []
    for subdir in ('usr/lib/aarch64-linux-gnu', 'lib/aarch64-linux-gnu', 'usr/lib64', 'usr/lib', 'lib'):
        candidates.extend(sorted((sysroot / subdir).glob('libopenxr_loader.so*')))
    for path in candidates:
        if path.exists():
            return path.resolve()
    raise MakerError('El sysroot no contiene libopenxr_loader.so para ARM64. Agregá los paquetes OpenXR de desarrollo al sysroot.')


def host_environment(target):
    env = os.environ.copy()
    if target == 'windows' and sys.platform == 'win32':
        msys = Path(os.environ.get('MSYS2_ROOT', r'C:\msys64'))
        ucrt = msys / 'ucrt64' / 'bin'
        usr = msys / 'usr' / 'bin'
        if not (ucrt / 'clang.exe').is_file() or not (usr / 'make.exe').is_file():
            raise MakerError('Falta MSYS2 UCRT64. Ejecutá tools/setup_windows.ps1 y luego iniciá el Maker desde Windows.')
        env['PATH'] = os.pathsep.join((str(ucrt), str(usr), env.get('PATH', '')))
        env['MSYSTEM'] = 'UCRT64'
        env['CHERE_INVOKING'] = '1'
    return env


def check_host(config, env):
    machine = platform.machine().lower()
    if config.target == 'windows':
        if sys.platform != 'win32':
            raise MakerError('El paquete Windows se compila desde Windows con MSYS2 UCRT64.')
    elif config.target == 'linux':
        if sys.platform != 'linux' or machine not in ('x86_64', 'amd64'):
            raise MakerError('El paquete Linux x86_64 se compila desde Linux x86_64.')
    elif config.target == 'steamframe':
        if sys.platform != 'linux' or machine not in ('x86_64', 'amd64'):
            raise MakerError('El paquete Steam Frame se cruza desde Linux x86_64.')
        if not config.sysroot or not config.sysroot.is_dir():
            raise MakerError('Steam Frame requiere la ruta a un sysroot Linux ARM64 con OpenXR.')
    else:
        raise MakerError('Destino desconocido: ' + config.target)

    tools = ('git', 'make', 'python3') if config.target != 'windows' else (
        'git', 'make', 'clang', 'clang++', 'windres', 'ldd', 'bash', 'nproc', 'cygpath', 'curl', 'sha256sum', 'tar')
    missing = [tool for tool in tools if shutil.which(tool, path=env.get('PATH')) is None]
    if config.target != 'windows':
        required = ('clang', 'clang++', 'ld.lld', 'llvm-ar', 'llvm-ranlib', 'cmake', 'ninja', 'pkg-config',
                    'curl', 'readelf', 'patchelf', 'nm', 'sha256sum', 'ldconfig')
        missing.extend(tool for tool in required if shutil.which(tool, path=env.get('PATH')) is None)
        if not (env.get('LLVM_STRIP') and shutil.which(env['LLVM_STRIP'], path=env.get('PATH'))) and not any(
                shutil.which('llvm-strip' + ('-' + str(version) if version else ''), path=env.get('PATH'))
                for version in ('',) + tuple(range(30, 10, -1))):
            missing.append('llvm-strip (or set LLVM_STRIP)')
    if missing:
        raise MakerError('Faltan herramientas de compilación: ' + ', '.join(sorted(set(missing))))


def ensure_python_env(repo, env, log):
    venv = repo / 'tools' / 'venv'
    py = venv / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not py.is_file():
        log('Creando el entorno Python local del clon...')
        log_command([sys.executable, '-m', 'venv', str(venv)], repo, env, log)
    check = run_capture([str(py), '-c', 'import capstone, lz4, unicorn'], cwd=repo, env=env)
    if check.returncode:
        log('Instalando lz4, capstone y unicorn en el entorno Python local...')
        log_command([str(py), '-m', 'pip', 'install', 'lz4==4.4.5', 'capstone==5.0.9', 'unicorn==2.1.4'], repo, env, log)
    return py


def verify_supported_game(repo, py, env, log):
    code = ("import sys; sys.path.insert(0, 'tools'); "
            "from game_sites import supported_version; from nso import header; "
            "v=supported_version(header(sys.argv[1])['build_id']); "
            "print(v.name if v and v.supported else 'unsupported')")
    result = run_capture([str(py), '-c', code, str(repo / 'extracted' / 'exefs' / 'main')], cwd=repo, env=env)
    if result.returncode:
        raise MakerError('No se pudo comprobar la versión del ejecutable del juego: ' + result.stdout.strip())
    version = result.stdout.strip()
    if version != '1.9.0':
        raise MakerError('El ExeFS no corresponde a la versión compatible 1.9.0 (detectada: {}).'.format(version))
    log('ExeFS verificado: BOTW ' + version)


def prepare_checkout(work, config, env, log):
    validate_ref(config.ref)
    repo = work / 'src'
    repo.mkdir()
    run = lambda args: log_command(['git', '-C', str(repo)] + args, work, env, log)
    run(['init'])
    run(['config', 'core.autocrlf', 'false'])
    run(['config', 'core.eol', 'lf'])
    run(['remote', 'add', 'origin', config.source])
    run(['fetch', '--depth', '1', 'origin', config.ref])
    run(['checkout', '--detach', 'FETCH_HEAD'])
    commit = run_capture(['git', '-C', str(repo), 'rev-parse', 'HEAD'], cwd=work, env=env)
    if commit.returncode:
        raise MakerError('No se pudo identificar el commit descargado.')
    return repo, commit.stdout.strip()


def build_windows(repo, env, config, log):
    env = env.copy()
    env['SW_BUILD_JOBS'] = str(config.jobs)
    py = ensure_python_env(repo, env, log)
    verify_supported_game(repo, py, env, log)
    log_command(['make', '-j{}'.format(config.jobs), 'deps-windows'], repo, env, log)
    log_command(['make', 'gen'], repo, env, log)
    b = Path('build/maker/windows')
    cpu_args = cpu_make_args(config)
    args = ['make', '-j{}'.format(config.jobs), 'VR=1', 'VR_DEFAULT=1', 'VR_MAKER=1', 'RELEASE=1',
            'DEPS=build/deps-win', 'B=' + b.as_posix()] + cpu_args + [
                (b / 'savagewind-vr-runtime.exe').as_posix(), (b / 'savagewind-vr.exe').as_posix(),
                (b / 'swgame.dll').as_posix()]
    log_command(args, repo, env, log)
    return repo / b


def build_linux(repo, env, config, log):
    py = ensure_python_env(repo, env, log)
    verify_supported_game(repo, py, env, log)
    arch = 'aarch64' if config.target == 'steamframe' else 'x86_64'
    b = Path('build/linux') / arch / 'game'
    deps = Path('build/linux') / arch / 'deps'
    build_env = env.copy()
    build_env['SW_BUILD_JOBS'] = str(config.jobs)
    make_vars = ['ARCH=' + arch, 'VR=1', 'VR_DEFAULT=1', 'VR_MAKER=1', 'B=' + b.as_posix(),
                 'DEPS=' + deps.as_posix()]
    if config.target == 'steamframe':
        sysroot = config.sysroot.resolve()
        build_env['SYSROOT'] = str(sysroot)
        build_env['OPENXR_LOADER'] = str(sysroot_openxr(sysroot))
        make_vars.append('SYSROOT=' + str(sysroot))
    make_vars += cpu_make_args(config)
    log_command(['make', 'gen', 'ARCH=' + arch] + (['SYSROOT=' + str(config.sysroot.resolve())]
                if config.target == 'steamframe' else []), repo, build_env, log)
    log_command(['tools/linux/build_deps.sh', arch], repo, build_env, log)
    log_command(['make', '-j{}'.format(config.jobs)] + make_vars + [(b / 'swgame.so').as_posix()], repo, build_env, log)
    package_env = build_env.copy()
    package_env['VR'] = '1'
    package_env['VR_MAKER'] = '1'
    if config.target != 'steamframe':
        profile = detect_cpu_profile() if config.cpu == 'auto' else config.cpu
        package_env['GENARCH'] = '-march=x86-64-' + profile
        package_env['GENARCH_COMPAT'] = ''
    log_command(['tools/linux/package.sh', arch], repo, package_env, log)
    return repo


def copy_windows_runtime(repo, runtime_dir, output, env, log):
    runtime = runtime_dir / 'savagewind-vr-runtime.exe'
    launcher = runtime_dir / 'savagewind-vr.exe'
    game_lib = runtime_dir / 'swgame.dll'
    if not all(p.is_file() for p in (runtime, launcher, game_lib, runtime_dir / 'swgame.dll.id')):
        raise MakerError('Falta una salida Windows esperada (runtime, launcher o swgame.dll).')
    shutil.copy2(launcher, output / 'Savage Wind VR.exe')
    shutil.copy2(runtime, output / runtime.name)
    shutil.copy2(game_lib, output / game_lib.name)
    shutil.copy2(runtime_dir / 'swgame.dll.id', output / 'swgame.dll.id')
    ldd_env = env.copy()
    ldd_env['PATH'] = os.pathsep.join((str(runtime_dir), env.get('PATH', '')))
    log('Resolviendo las DLL del runtime y del juego recompilado...')
    cygpath = shutil.which('cygpath', path=env.get('PATH'))
    for binary in (runtime, game_lib):
        ldd = run_capture(['ldd', str(binary)], cwd=repo, env=ldd_env)
        if ldd.returncode:
            raise MakerError('No se pudieron resolver las DLL de {}: {}'.format(binary.name, ldd.stdout.strip()))
        for line in ldd.stdout.splitlines():
            match = re.search(r'=>\s+(.+?)\s+\(0x[0-9a-fA-F]+\)', line)
            if not match:
                if 'not found' in line:
                    raise MakerError('Falta una dependencia de Windows: ' + line.strip())
                continue
            raw = match.group(1).strip()
            if raw.lower().endswith('vulkan-1.dll'):
                continue  # Vulkan loader comes from the installed GPU driver.
            if raw.startswith('/') and cygpath:
                conv = run_capture([cygpath, '-w', raw], cwd=repo, env=env)
                if conv.returncode:
                    raise MakerError('No se pudo convertir la ruta MSYS2: ' + raw)
                raw = conv.stdout.strip()
            source = Path(raw)
            if not source.is_file():
                raise MakerError('No se encontró la DLL requerida: ' + raw)
            normalized = str(source).replace('\\', '/').lower()
            if '/ucrt64/' not in normalized and '/deps-win/bin/' not in normalized:
                continue  # Windows system DLLs are provided by Windows itself.
            if source.name.lower() == 'vulkan-1.dll':
                continue
            dest = output / source.name
            if not dest.exists():
                shutil.copy2(source, dest)
    bad = [p.name for p in output.iterdir() if re.search(r'x264|x265|xvid|postproc', p.name, re.I)]
    if bad:
        raise MakerError('Se detectaron bibliotecas FFmpeg GPL que no deben incluirse: ' + ', '.join(bad))


def write_package_docs(output, target, commit, config, version, game_version, appimage=None):
    if target == 'windows':
        start = 'Ejecutá "Savage Wind VR.exe". El paquete ya incluye el juego recompilado y tus archivos locales.'
        data = 'Los archivos extraídos, partidas y ajustes quedan en esta carpeta.'
    else:
        start = 'Hacé ejecutable el AppImage si hace falta y abrilo. También podés usar "Run Savage Wind VR.sh".'
        data = 'Los archivos extraídos, partidas y ajustes quedan en data/ junto al AppImage.'
    if target == 'steamframe':
        start = 'Transferí la carpeta completa al Steam Frame, marcá el AppImage como ejecutable y abrilo desde SteamOS.'
    if appimage:
        start += '\nAppImage: ' + appimage.name
    readme = ('Savage Wind VR - paquete preparado en PC\n\n' + start + '\n' + data + '\n'
              'El juego recompilado se construyó con los archivos que seleccionaste; al iniciar no necesita recompilar. '
              'Se requiere un runtime OpenXR y un controlador Vulkan compatible.\n\n'
              'No subas ni compartas esta carpeta: contiene archivos de juego de tu copia personal.\n')
    (output / 'LEEME.txt').write_text(readme, encoding='utf-8')
    (output / 'BUILD-INFO.txt').write_text(
        'Savage Wind VR Maker\n'
        'Source: {}\nRef: {}\nCommit: {}\nTarget: {}\nVersion: {}\nGame version: {}\n'
        'CPU profile: {}\nBuilt UTC: {}\n'.format(config.source, config.ref, commit, target, version,
            game_version, 'ARM64' if target == 'steamframe' else (detect_cpu_profile() if config.cpu == 'auto' else config.cpu),
            datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')),
        encoding='utf-8')


def stage_windows(repo, runtime_dir, out, commit, config, game_root_path, game_version, env, log):
    copy_windows_runtime(repo, runtime_dir, out, env, log)
    for name in ('README.md', 'LICENSE'):
        shutil.copy2(repo / name, out / name)
    shutil.copy2(repo / 'docs' / 'VR.md', out / 'VR.md')
    shutil.move(str(repo / 'extracted'), str(out / 'extracted'))
    version = botwvr_version(repo)
    write_package_docs(out, 'windows', commit, config, version, game_version)


def stage_linux(repo, out, commit, config, game_root_path, game_version, log):
    dist = repo / 'build' / 'dist'
    images = sorted(dist.glob('BOTW-VR-*.AppImage'))
    if len(images) != 1:
        raise MakerError('Se esperaba un AppImage VR; encontrados: {}'.format(len(images)))
    version = botwvr_version(repo)
    appimage = out / images[0].name
    shutil.move(str(images[0]), str(appimage))
    appimage.chmod(appimage.stat().st_mode | 0o111)
    data_dir = out / 'data'
    data_dir.mkdir()
    shutil.move(str(repo / 'extracted'), str(data_dir / 'extracted'))
    runner = out / 'Run Savage Wind VR.sh'
    runner.write_text('#!/bin/sh\nHERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n'
                      'export SAVAGEWIND_DATA_ROOT="$HERE/data"\n'
                      'exec "$HERE/{}" "$@"\n'.format(appimage.name), encoding='utf-8')
    runner.chmod(runner.stat().st_mode | 0o111)
    for name in ('README.md', 'LICENSE'):
        shutil.copy2(repo / name, out / name)
    write_package_docs(out, config.target, commit, config, version, game_version, appimage)


def build(config, log):
    log('PC Maker started')
    log('Target: {} | ref: {} | source: {}'.format(config.target, config.ref, config.source))
    log('Host: {} | Python: {}'.format(platform.platform(), sys.version.replace('\n', ' ')))
    log('Game files: {}'.format(config.game_files.expanduser()))
    log('Output: {}'.format(config.output.expanduser()))
    log('Sysroot: {}'.format(config.sysroot.expanduser() if config.sysroot else '(not used)'))
    log('Jobs: {} | CPU profile: {}'.format(config.jobs, config.cpu))
    source_game, game_version = validate_game_files(config.game_files)
    output = config.output.expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise MakerError('La carpeta de salida ya existe; elegí una carpeta nueva para no sobrescribir archivos.')
    if is_within(output, source_game) or is_within(source_game, output):
        raise MakerError('La carpeta de salida y la carpeta de archivos del juego no pueden contenerse entre sí.')
    if is_within(output, RUNNING_REPO):
        raise MakerError('Elegí una carpeta de salida fuera del checkout del proyecto para no agregar archivos del juego al repo.')
    validate_ref(config.ref)
    parent = output.parent
    parent.mkdir(parents=True, exist_ok=True)
    env = host_environment(config.target)
    check_host(config, env)
    if config.target == 'steamframe':
        sysroot_openxr(config.sysroot.resolve())
    free = shutil.disk_usage(parent).free
    log('Espacio libre en el volumen de trabajo: {:.1f} GB'.format(free / (1024 ** 3)))
    if free < 35 * 1024 ** 3:
        raise MakerError('Se recomiendan al menos 35 GB libres para generar, compilar y preparar el paquete.')
    work = Path(tempfile.mkdtemp(prefix='.botw-vr-maker-', dir=str(parent)))
    owns_output = False
    try:
        log('Descargando el código desde GitHub; los archivos del juego permanecen locales...')
        repo, commit = prepare_checkout(work, config, env, log)
        log('Commit: ' + commit)
        copy_game_files(source_game, repo / 'extracted', log)
        if config.target == 'windows':
            runtime_dir = build_windows(repo, env, config, log)
            output.mkdir()
            owns_output = True
            stage_windows(repo, runtime_dir, output, commit, config, source_game, game_version, env, log)
        else:
            build_linux(repo, env, config, log)
            output.mkdir()
            owns_output = True
            stage_linux(repo, output, commit, config, source_game, game_version, log)
        log('Paquete listo: ' + str(output))
        return output
    except Exception:
        if owns_output:
            shutil.rmtree(output, ignore_errors=True)
        raise
    finally:
        if config.keep_work:
            log('Clon y archivos de compilación conservados localmente en: ' + str(work))
        else:
            shutil.rmtree(work, ignore_errors=True)


def target_choices():
    if sys.platform == 'win32':
        return ('windows',)
    if sys.platform == 'linux' and platform.machine().lower() in ('x86_64', 'amd64'):
        return ('linux', 'steamframe')
    return ()


def run_gui():
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except ImportError as e:
        raise MakerError('Tkinter no está instalado. Usá el Maker desde terminal con --target.') from e

    choices = target_choices()
    if not choices:
        raise MakerError('La interfaz está disponible en Windows x64 o Linux x86_64.')
    root = tk.Tk()
    root.title('Savage Wind VR PC Maker')
    root.geometry('900x720')
    root.minsize(780, 620)
    frame = ttk.Frame(root, padding=12)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='Prepará un paquete VR para transferir', font=('TkDefaultFont', 14, 'bold')).pack(anchor='w')
    ttk.Label(frame, text=('El código se descarga de GitHub y se compila en esta PC. Los archivos seleccionados '
                           'del juego se usan localmente y quedan dentro del paquete; nunca se suben.'),
              wraplength=850).pack(anchor='w', pady=(4, 10))
    fields = {}

    def path_row(key, label, directory=True):
        row = ttk.Frame(frame)
        row.pack(fill='x', pady=3)
        ttk.Label(row, text=label, width=25).pack(side='left')
        var = tk.StringVar()
        fields[key] = var
        entry = ttk.Entry(row, textvariable=var)
        entry.pack(side='left', fill='x', expand=True, padx=5)
        def browse():
            initial = var.get() or str(Path.home())
            if key == 'output':
                picked = filedialog.askdirectory(initialdir=initial)
                if picked:
                    var.set(str(Path(picked) / 'Savage Wind VR package'))
                return
            picked = filedialog.askdirectory(initialdir=initial, mustexist=False) if directory else filedialog.askopenfilename(initialdir=initial)
            if picked:
                var.set(picked)
        ttk.Button(row, text='Elegir…', command=browse).pack(side='left')
        return entry

    path_row('game_files', 'Carpeta exefs/ + romfs/')
    path_row('output', 'Carpeta de salida')
    fields['output'].set(str(Path.home() / 'Savage Wind VR package'))
    row = ttk.Frame(frame)
    row.pack(fill='x', pady=3)
    ttk.Label(row, text='Destino', width=25).pack(side='left')
    target = tk.StringVar(value=choices[0])
    target_widget = ttk.Combobox(row, textvariable=target, values=choices, state='readonly', width=25)
    target_widget.pack(side='left', padx=5)
    ttk.Label(row, text='x86-64:').pack(side='left', padx=(12, 4))
    cpu = tk.StringVar(value='auto')
    cpu_widget = ttk.Combobox(row, textvariable=cpu, values=('auto', 'v2', 'v3'), state='readonly', width=10)
    cpu_widget.pack(side='left')
    sysroot_entry = None
    if 'steamframe' in choices:
        sysroot_entry = path_row('sysroot', 'Sysroot Linux ARM64')
        fields['sysroot'].set(os.environ.get('STEAMFRAME_SYSROOT', ''))
        ttk.Label(frame, text='Steam Frame necesita un sysroot Linux AArch64 de desarrollo con OpenXR.',
                  wraplength=850).pack(anchor='w', padx=(205, 0), pady=(0, 3))
    row = ttk.Frame(frame)
    row.pack(fill='x', pady=3)
    ttk.Label(row, text='URL de GitHub', width=25).pack(side='left')
    source = tk.StringVar(value=DEFAULT_SOURCE)
    fields['source'] = source
    ttk.Entry(row, textvariable=source).pack(side='left', fill='x', expand=True, padx=5)
    row = ttk.Frame(frame)
    row.pack(fill='x', pady=3)
    ttk.Label(row, text='Rama, tag o commit', width=25).pack(side='left')
    ref = tk.StringVar(value=DEFAULT_REF)
    fields['ref'] = ref
    ttk.Entry(row, textvariable=ref).pack(side='left', fill='x', expand=True, padx=5)
    jobs = tk.IntVar(value=max(1, min(os.cpu_count() or 1, 8)))
    row = ttk.Frame(frame)
    row.pack(fill='x', pady=3)
    ttk.Label(row, text='Trabajos paralelos', width=25).pack(side='left')
    ttk.Spinbox(row, from_=1, to=max(1, os.cpu_count() or 1), textvariable=jobs, width=8).pack(side='left', padx=5)

    log_box = tk.Text(frame, height=18, bg='#11151b', fg='#e6edf3', wrap='word', font=('Consolas', 9))
    log_box.pack(fill='both', expand=True, pady=(10, 5))
    events = queue.Queue()
    start = ttk.Button(frame, text='Crear paquete VR')
    start.pack(anchor='w')

    def sync_target_controls(*_):
        if target.get() == 'steamframe':
            cpu_widget.state(['disabled'])
        else:
            cpu_widget.state(['!disabled'])
        if sysroot_entry:
            sysroot_entry.state(['!disabled'] if target.get() == 'steamframe' else ['disabled'])

    target_widget.bind('<<ComboboxSelected>>', sync_target_controls)
    sync_target_controls()

    def append(text):
        events.put(text)

    def do_build(cfg, run_log):
        try:
            result = build(cfg, run_log)
            run_log('Package ready: ' + str(result))
            events.put(('done', str(result), str(run_log.path)))
        except Exception as e:
            run_log.exception(e)
            events.put(('error', str(e), str(run_log.path)))
        finally:
            run_log.close()

    def start_build():
        try:
            run_log = create_run_logger(target.get(), append)
        except Exception as e:
            messagebox.showerror('PC Maker', 'No se pudo crear el log detallado:\n{}'.format(e))
            return
        try:
            sysroot_value = fields['sysroot'].get().strip() if 'sysroot' in fields else ''
            cfg = Config(target=target.get(), game_files=Path(fields['game_files'].get()),
                         output=Path(fields['output'].get()), source=source.get().strip(), ref=ref.get().strip(),
                         sysroot=Path(sysroot_value) if sysroot_value else None,
                         cpu=cpu.get(), jobs=max(1, int(jobs.get())))
        except Exception as e:
            run_log.exception(e)
            run_log.close()
            messagebox.showerror('PC Maker', '{}\n\nLog detallado:\n{}'.format(e, run_log.path))
            return
        run_log('PC Maker log: ' + str(run_log.path))
        start.state(['disabled'])
        threading.Thread(target=do_build, args=(cfg, run_log), daemon=True).start()

    start.configure(command=start_build)

    def pump():
        try:
            while True:
                item = events.get_nowait()
                if isinstance(item, tuple):
                    start.state(['!disabled'])
                    if item[0] == 'done':
                        log_box.insert('end', 'Listo: ' + item[1] + '\n')
                        messagebox.showinfo('PC Maker', 'Paquete creado en:\n{}\n\nLog detallado:\n{}'.format(item[1], item[2]))
                    else:
                        log_box.insert('end', 'ERROR: ' + item[1] + '\n')
                        messagebox.showerror('PC Maker', '{}\n\nAdjuntá este log al informar el error:\n{}'.format(item[1], item[2]))
                else:
                    log_box.insert('end', str(item) + '\n')
                log_box.see('end')
        except queue.Empty:
            pass
        root.after(100, pump)

    root.after(100, pump)
    root.mainloop()


def main():
    ap = argparse.ArgumentParser(description='Crea paquetes Savage Wind VR listos para transferir.')
    ap.add_argument('--target', choices=('windows', 'linux', 'steamframe'))
    ap.add_argument('--game-files', type=Path, help='carpeta con exefs/ y romfs/')
    ap.add_argument('--output', type=Path, help='carpeta nueva donde se crea el paquete')
    ap.add_argument('--source', default=DEFAULT_SOURCE, help='repositorio Git; default: BOTW-VR-RECOMP')
    ap.add_argument('--ref', default=DEFAULT_REF, help='rama, tag o commit; default: main')
    ap.add_argument('--sysroot', type=Path, help='sysroot Linux ARM64 para Steam Frame')
    ap.add_argument('--cpu', choices=('auto', 'v2', 'v3'), default='auto', help='perfil x86-64 del dispositivo destino')
    ap.add_argument('--jobs', type=int, default=max(1, min(os.cpu_count() or 1, 8)))
    ap.add_argument('--keep-work', action='store_true', help='conserva el clon temporal y los archivos de compilación')
    args = ap.parse_args()
    try:
        if not args.target:
            run_gui()
            return 0
        if not args.game_files or not args.output:
            ap.error('--game-files y --output son obligatorios con --target')
        cfg = Config(args.target, args.game_files, args.output, args.source, args.ref, args.sysroot,
                     args.cpu, max(1, args.jobs), args.keep_work)
        run_log = create_run_logger(cfg, lambda line: print(line, flush=True))
        print('Log detallado: {}'.format(run_log.path), flush=True)
        try:
            build(cfg, run_log)
            run_log('Package ready: ' + str(cfg.output))
        except Exception as e:
            run_log.exception(e)
            print('Maker: {}\nLog detallado: {}'.format(e, run_log.path), file=sys.stderr)
            return 1
        finally:
            run_log.close()
        return 0
    except MakerError as e:
        print('Maker: ' + str(e), file=sys.stderr)
        return 1
    except OSError as e:
        print('Maker: ' + str(e), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('\nMaker cancelado.', file=sys.stderr)
        return 130


if __name__ == '__main__':
    sys.exit(main())
