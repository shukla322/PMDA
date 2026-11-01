"""Download pinned free CPU inference assets into BTP, without global installation."""
import hashlib
import json
from pathlib import Path
import zipfile
import requests

ROOT = Path(__file__).resolve().parents[1]
REV = "91cad51170dc346986eccefdc2dd33a9da36ead9"
ASSETS = [
    ("vendor/llama.cpp/runtime.zip", "https://github.com/ggml-org/llama.cpp/releases/download/b11669/llama-b11669-bin-win-cpu-x64.zip", "37b3efcf962847ca869745fd4ccf7f5e7e8dacfeff9fa3523b4ca8cdc66d632b"),
    ("models/agents/qwen2.5-1.5b-instruct-q4_k_m.gguf", f"https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/{REV}/qwen2.5-1.5b-instruct-q4_k_m.gguf", None),
    ("models/agents/LICENSE", f"https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/{REV}/LICENSE", None),
    ("vendor/llama.cpp/LICENSE", "https://raw.githubusercontent.com/ggml-org/llama.cpp/b11669/LICENSE", None),
]


def main():
    records = []
    for relative, url, expected in ASSETS:
        path = ROOT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            partial = path.with_suffix(path.suffix + ".partial")
            with requests.get(url, stream=True, timeout=(30, 90)) as response:
                response.raise_for_status()
                with partial.open("wb") as out:
                    for chunk in response.iter_content(1024 * 1024):
                        out.write(chunk)
            partial.replace(path)
        with path.open("rb") as stream:
            sha = hashlib.file_digest(stream, "sha256").hexdigest()
        if expected and sha != expected:
            raise ValueError("Release checksum mismatch: " + relative)
        records.append(dict(path=relative, url=url, sha256=sha, size=path.stat().st_size))
        print(relative, path.stat().st_size, flush=True)
    destination = ROOT / "vendor/llama.cpp/bin"
    destination.mkdir(exist_ok=True)
    with zipfile.ZipFile(ROOT / ASSETS[0][0]) as archive:
        for item in archive.infolist():
            if not (destination / item.filename).resolve().is_relative_to(destination.resolve()):
                raise ValueError("Archive path escape")
        archive.extractall(destination)
    (ROOT / "models/agents/provenance.json").write_text(json.dumps({"model_revision": REV, "runtime_release": "b11669", "assets": records}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
