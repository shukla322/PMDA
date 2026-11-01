"""Offline local backup/restore. Requires stopped portal and no active jobs.

Includes portal accounts (hashed passwords), campaign inputs and artifacts.
Excludes the plaintext initial-access file and clears sessions on restore.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import socket
import sqlite3
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def stopped():
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1",8765)) == 0:
            raise RuntimeError("Stop the local portal before backup or restore")


def backup(source):
    source = Path(source).resolve()
    if not source.is_relative_to(ROOT / "runtime"):
        raise ValueError("Backup source must be inside BTP/runtime")
    for path in source.rglob("*.sqlite3"):
        with sqlite3.connect(path) as db:
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "jobs" in tables and db.execute("SELECT 1 FROM jobs WHERE status IN ('reserved','starting','running','ambiguous')").fetchone():
                raise ValueError("Resolve active/ambiguous jobs before backup")
            if "operations" in tables and db.execute("SELECT 1 FROM operations WHERE status IN ('queued','running')").fetchone():
                raise ValueError("Finish or resolve preparation before backup")
        db.close()
    destination = ROOT / "runtime/backups" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination.mkdir(parents=True)
    archive = destination / "portal.zip"
    manifest = {}
    with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as out:
        for path in sorted(source.rglob("*")):
            if not path.is_file() or path.name == "LOCAL_ACCESS.txt":
                continue
            if path.is_symlink() or not path.resolve().is_relative_to(source):
                raise ValueError("Backup contains a link outside its root")
            relative = path.relative_to(source).as_posix()
            raw = path.read_bytes()
            manifest[relative] = hashlib.sha256(raw).hexdigest()
            out.writestr(relative,raw)
    record = dict(source=str(source),files=manifest,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    (destination / "manifest.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
    return destination


def restore(backup_directory, destination):
    backup_directory, destination = Path(backup_directory).resolve(), Path(destination).resolve()
    if not backup_directory.is_relative_to(ROOT / "runtime") or not destination.is_relative_to(ROOT / "runtime") or destination.exists():
        raise ValueError("Use BTP/runtime paths and a new restore destination")
    manifest = json.loads((backup_directory / "manifest.json").read_bytes())
    archive = backup_directory / "portal.zip"
    if hashlib.sha256(archive.read_bytes()).hexdigest() != manifest["archive_sha256"]:
        raise ValueError("Backup archive hash mismatch")
    with zipfile.ZipFile(archive) as source:
        if set(source.namelist()) != set(manifest["files"]):
            raise ValueError("Archive contents differ from the manifest")
        for name in source.namelist():
            path = (destination / name).resolve()
            if not path.is_relative_to(destination) or hashlib.sha256(source.read(name)).hexdigest() != manifest["files"][name]:
                raise ValueError("Invalid backup entry")
        source.extractall(destination)
    # Evidence paths are absolute. Restores into a new directory are inspection
    # copies, not executable campaign resumptions; original-path restore needs
    # an operator-reviewed recovery procedure and must not silently rewrite hashes.
    db_path = destination / "portal.sqlite3"
    if db_path.exists():
        with sqlite3.connect(db_path) as db:
            db.execute("DELETE FROM sessions")
        db.close()
    original = destination == Path(manifest["source"]).resolve()
    note = "Restored to the original absolute location. Sessions were invalidated; sign in again. No engine job was relaunched." if original else "Inspection copy only. Campaign evidence contains original absolute paths; do not launch this copy as a resumed campaign."
    (destination / "RESTORE_NOTE.md").write_text("# Restore status\n\n" + note + "\n",encoding="utf-8")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action",choices=["backup","restore"])
    parser.add_argument("path")
    parser.add_argument("--destination")
    args = parser.parse_args()
    stopped()
    print(backup(args.path) if args.action == "backup" else restore(args.path,args.destination))
