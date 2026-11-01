"""Freeze the verified Windows CPython 3.12 package payload for offline recreation.

This is a platform-specific binary bundle, not a cross-platform wheel lock.
"""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
import zipfile

root = Path(__file__).resolve().parents[1]
destination = root / "environment"
destination.mkdir(exist_ok=True)
source = root / ".venv/Lib/site-packages"
archive = destination / "windows-py312-packages.zip"
if archive.exists():
    raise SystemExit("Bundle already exists; preserve this version before rebuilding")
freeze = subprocess.run([sys.executable,"-m","pip","freeze","--exclude-editable"],check=True,capture_output=True,text=True)
(destination / "requirements.lock.txt").write_text(freeze.stdout,encoding="utf-8")
count = 0
with zipfile.ZipFile(archive,"x",compression=zipfile.ZIP_DEFLATED,compresslevel=1) as bundle:
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if not path.is_file() or "__pycache__" in relative.parts or path.suffix in {".pyc",".pyo"}:
            continue
        first = relative.parts[0].lower()
        if first.startswith(("__editable__","reinvent-","pmda-")):
            continue
        if path.is_symlink():
            raise RuntimeError("Package symlink requires manual review")
        bundle.write(path,relative.as_posix())
        count += 1
manifest = {"platform":platform.platform(),"python":platform.python_version(),"architecture":platform.machine(),
    "archive":archive.name,"sha256":hashlib.file_digest(archive.open("rb"),"sha256").hexdigest(),
    "bytes":archive.stat().st_size,"files":count,"format":"site-packages payload; local editable distributions reinstalled",
    "limitations":["Requires compatible Windows x64 CPython 3.12 and system libraries",
                    "Only pip and project console launchers are recreated; other packages remain importable",
                    "Installed-package snapshot, not independently rebuilt upstream wheels"]}
(destination / "manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
print(json.dumps(manifest,indent=2),flush=True)
