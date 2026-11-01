"""Download a bounded, provenance-preserving public ChEMBL research snapshot.

Raw records are not a curated training dataset. No credentials are required.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[1]
API = "https://www.ebi.ac.uk/chembl/api/data/"


def main():
    folder = ROOT / "data" / "raw" / ("egfr-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    folder.mkdir(parents=True, exist_ok=False)
    client = requests.Session()
    client.mount("https://", HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])))
    manifest = {"status": "incomplete", "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "target": "CHEMBL203", "files": [], "counts": {}, "curated": False}

    def save_manifest():
        (folder / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    def fetch(endpoint, params, filename):
        response = client.get(API + endpoint, params=params, timeout=(15, 60))
        response.raise_for_status()
        data = response.json()
        content = response.content
        (folder / filename).write_bytes(content)
        manifest["files"].append({"file": filename, "url": response.url,
                                  "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})
        save_manifest()
        return data

    def pages(endpoint, key, params):
        total, seen, ids = None, 0, set()
        for page in range(100):
            data = fetch(endpoint + ".json", {**params, "limit": 1000, "offset": seen}, f"{endpoint}-{page:03d}.json")
            meta = data["page_meta"]
            if total is None:
                total = meta["total_count"]
            if total != meta["total_count"]:
                raise RuntimeError("Source count changed during download; retry a fresh snapshot")
            records = data[key]
            for row in records:
                identifier = row["activity_id" if endpoint == "activity" else "assay_chembl_id"]
                if identifier in ids:
                    raise RuntimeError("Duplicate identifier across pages")
                ids.add(identifier)
            seen += len(records)
            print(f"{endpoint}: {seen}/{total}", flush=True)
            if seen == total:
                manifest["counts"][endpoint] = seen
                save_manifest()
                return
            if not records or seen > total:
                raise RuntimeError("Unexpected pagination")
        raise RuntimeError("Download exceeded 100-page limit")

    try:
        before = fetch("status.json", {}, "status-before.json")
        target = fetch("target/CHEMBL203.json", {}, "target.json")
        if target["organism"] != "Homo sapiens" or target["target_type"] != "SINGLE PROTEIN":
            raise RuntimeError("Target identity mismatch")
        pages("activity", "activities", {"target_chembl_id": "CHEMBL203", "standard_type": "IC50",
              "standard_units": "nM", "standard_relation": "=", "assay_type": "B", "order_by": "activity_id"})
        pages("assay", "assays", {"target_chembl_id": "CHEMBL203", "assay_type": "B", "order_by": "assay_chembl_id"})
        after = fetch("status.json", {}, "status-after.json")
        if before.get("chembl_db_version") != after.get("chembl_db_version"):
            raise RuntimeError("Database release changed during download")
        manifest.update(status="downloaded_not_curated", release=before.get("chembl_db_version"))
        print(f"Snapshot: {folder}", flush=True)
    except Exception as exc:
        manifest["failure"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        save_manifest()
        client.close()


if __name__ == "__main__":
    main()
