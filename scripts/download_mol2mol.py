"""Download the public, checksum-pinned Mol2Mol medium-similarity prior."""
import hashlib
import json
from pathlib import Path
import requests

root=Path(__file__).resolve().parents[1]
metadata=json.loads((root / "references/zenodo-15641297.json").read_bytes())
entry=next(f for f in metadata["files"] if f["key"]=="mol2mol_medium_similarity.prior")
target=root / "models" / entry["key"]
if target.exists():
    raise SystemExit("Model already exists; do not overwrite a verified prior")
temporary=target.with_suffix(".part")
url=entry["links"]["self"]
if not url.startswith("https://zenodo.org/") or entry["size"]>100_000_000:
    raise SystemExit("Unexpected source or download size")
hasher=hashlib.md5()
size=0
with requests.get(url,stream=True,timeout=(15,60)) as response:
    response.raise_for_status()
    with temporary.open("wb") as output:
        for chunk in response.iter_content(1024*1024):
            size+=len(chunk)
            if size>entry["size"]:
                raise RuntimeError("Download exceeds recorded size")
            hasher.update(chunk)
            output.write(chunk)
if size!=entry["size"] or "md5:"+hasher.hexdigest()!=entry["checksum"]:
    raise RuntimeError("Prior checksum mismatch")
temporary.replace(target)
print(json.dumps({"file":str(target),"bytes":size,"md5":hasher.hexdigest(),"sha256":hashlib.sha256(target.read_bytes()).hexdigest()},indent=2))
