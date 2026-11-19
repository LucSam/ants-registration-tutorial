#!/usr/bin/env python3
"""Check dependencies, or install the tutorial in its own .venv directory."""
import argparse
import importlib.metadata
from pathlib import Path
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent
ENV = ROOT / '.venv'
CLI_TOOLS = ('antsRegistration', 'antsApplyTransforms', 'antsRegistrationSyNQuick.sh')
CLI_GUIDE = 'https://github.com/ANTsX/ANTs/wiki/Installing-ANTs-release-binaries'


def requirements():
    return [line.strip() for line in (ROOT / 'requirements.txt').read_text().splitlines()
            if line.strip() and not line.lstrip().startswith('#')]


def check(with_brain_extraction=False, require_cli=False):
    print('Python:', sys.version.split()[0], '\nInterpreter:', sys.executable)
    failures = []
    if not (3, 10) <= sys.version_info[:2] <= (3, 12):
        failures.append('Use Python 3.10–3.12; this environment was tested with 3.12.')
    try:
        from packaging.requirements import Requirement
    except ImportError:
        Requirement = None
    specs = requirements() + (['antspynet>=0.2.8,<0.4'] if with_brain_extraction else [])
    for spec in specs:
        name = spec.split('>')[0].split('<')[0].split('=')[0]
        try:
            version = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            failures.append(f'Missing: {spec}')
            print('MISSING', spec)
            continue
        compatible = Requirement is None or Requirement(spec).specifier.contains(version)
        print('OK' if compatible else 'VERSION', name, version)
        if not compatible:
            failures.append(f'{name} {version} does not satisfy {spec}')
    if Requirement is None:
        failures.append('Install packaging to check version constraints.')

    print('\nOptional ANTs command-line section:')
    missing_cli = [name for name in CLI_TOOLS if not shutil.which(name)]
    for name in CLI_TOOLS:
        print('OK' if shutil.which(name) else 'MISSING', name)
    if missing_cli:
        print('Install guide for the terminal examples:', CLI_GUIDE)
        if require_cli:
            failures.append('ANTs command-line tools are required by --require-cli.')
    print('ANTsPyNet: optional; use --with-brain-extraction only for unstripped images.')

    input_files = ['assets/a.png', 'assets/b.png', 'assets/MNI152_T1_1mm_brain.nii.gz']
    input_files += [f'data/UCSF-PDGM-0033/UCSF-PDGM-0033_{suffix}.nii.gz'
                    for suffix in ('T1', 'T1c', 'tumor_segmentation')]
    missing_inputs = [name for name in input_files if not (ROOT / name).is_file()]
    if missing_inputs:
        failures.append('Missing input files: ' + ', '.join(missing_inputs) + '. See DATA.md.')
    else:
        print('OK: all tutorial images are present.')
    if failures:
        print('\nItems to resolve:')
        for failure in failures:
            print('-', failure)
        return 1
    print('\nCore environment is ready.')
    return 0


def install(with_brain_extraction=False, require_cli=False):
    if not (3, 10) <= sys.version_info[:2] <= (3, 12):
        raise RuntimeError('Run this installer with Python 3.10–3.12, preferably Python 3.12.')
    if not ENV.exists():
        venv.EnvBuilder(with_pip=True).create(ENV)
    elif not (ENV / 'pyvenv.cfg').is_file():
        raise RuntimeError('.venv exists but is not a virtual environment; it was not changed.')
    python = ENV / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
    command = [str(python), '-m', 'pip', 'install', '-r', str(ROOT / 'requirements.txt')]
    if with_brain_extraction:
        command.append('antspynet>=0.2.8,<0.4')
    subprocess.run(command, check=True)
    subprocess.run([str(python), '-m', 'pip', 'check'], check=True)
    subprocess.run([str(python), '-m', 'ipykernel', 'install', '--prefix', str(ENV),
                    '--name', 'ants-registration', '--display-name', 'ANTs registration tutorial'], check=True)
    command = [str(python), str(Path(__file__).resolve())]
    if with_brain_extraction:
        command.append('--with-brain-extraction')
    if require_cli:
        command.append('--require-cli')
    subprocess.run(command, check=True)
    print('\nStart Jupyter from the tutorial folder:')
    print(f'"{python}" -m jupyterlab ants_registration_tutorial.ipynb')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', action='store_true', help='Create .venv and install missing/incompatible Python packages there')
    parser.add_argument('--with-brain-extraction', action='store_true', help='Also check/install ANTsPyNet and its TensorFlow dependencies')
    parser.add_argument('--require-cli', action='store_true', help='Treat missing ANTs executables as an error')
    args = parser.parse_args()
    if args.install:
        install(args.with_brain_extraction, args.require_cli)
    else:
        return check(args.with_brain_extraction, args.require_cli)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError, OSError) as error:
        print(f'Setup failed: {error}', file=sys.stderr)
        raise SystemExit(1)
