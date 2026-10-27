"""Local packaging helper: python build.py --target mac|windows|current"""
import argparse, platform, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).parent
parser=argparse.ArgumentParser()
parser.add_argument("--target",choices=["mac","windows","current"],default="current")
args=parser.parse_args()
target=platform.system().lower() if args.target=="current" else args.target
if target in ("mac","darwin"):
    cmd=[sys.executable,"-m","PyInstaller","--noconfirm","--clean","--windowed","--name","KeyPressor","--add-data",f"{ROOT/'assets'}:assets",str(ROOT/"app.py")]
elif target in ("windows","win"):
    cmd=[sys.executable,"-m","PyInstaller","--noconfirm","--clean","--windowed","--name","KeyPressor","--add-data",f"{ROOT/'assets'};assets",str(ROOT/"app.py")]
else:
    raise SystemExit(f"Unsupported target: {target}. Use mac or windows.")
print("Packaging:", " ".join(cmd)); subprocess.run(cmd,cwd=ROOT,check=True)
