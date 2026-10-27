"""Build a local KeyPro distribution with PyInstaller."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
BUILD = ROOT / "build"


def main() -> None:
    try:
        subprocess.check_call([sys.executable, "-m", "PyInstaller", "--version"], stdout=subprocess.DEVNULL)
    except (OSError, subprocess.CalledProcessError):
        raise SystemExit("PyInstaller is not installed. Run: pip install -r requirements-dev.txt")
    spec = ROOT / "packaging" / "keypro.spec"
    if DIST.exists():
        shutil.rmtree(DIST)
    if BUILD.exists():
        shutil.rmtree(BUILD)
    subprocess.check_call([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--distpath", str(DIST), "--workpath", str(BUILD), str(spec),
    ], cwd=ROOT)
    print(f"Built: {DIST / 'KeyPro'}")


if __name__ == "__main__":
    main()
