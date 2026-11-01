"""Recreate the pinned local runtime in an empty BTP subdirectory, offline."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import venv
import zipfile

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("destination")
args = parser.parse_args()
destination = Path(args.destination).resolve()
if not destination.is_relative_to(root) or destination == root or destination.exists():
    raise SystemExit("Destination must be a new directory inside BTP")
if sys.version_info[:2]!=(3,12) or platform.system()!="Windows":
    raise SystemExit("Bundle requires Windows CPython 3.12")
manifest = json.loads((root / "environment/manifest.json").read_bytes())
archive = root / "environment" / manifest["archive"]
with archive.open("rb") as stream:
    if hashlib.file_digest(stream,"sha256").hexdigest()!=manifest["sha256"]:
        raise SystemExit("Bundle checksum mismatch")
venv.EnvBuilder(with_pip=True).create(destination)
packages = destination / "Lib/site-packages"
with zipfile.ZipFile(archive) as bundle:
    for item in bundle.infolist():
        if not (packages / item.filename).resolve().is_relative_to(packages):
            raise SystemExit("Unsafe archive member")
    bundle.extractall(packages)
python = destination / "Scripts/python.exe"
subprocess.run([str(python),"-m","pip","install","--no-index","--no-deps","--no-build-isolation","-e",str(root / "vendor/REINVENT4"),"-e",str(root)],check=True)
subprocess.run([str(python),"-m","pip","check"],check=True)
subprocess.run([str(python),str(root / "scripts/audit_local.py")],cwd=root,check=True)
print(f"Recreated: {destination}")
