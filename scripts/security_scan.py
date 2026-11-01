"""Bounded secret-pattern scan. Reports locations only, never matched values."""
import json
from pathlib import Path
import re

root=Path(__file__).resolve().parents[1]
patterns={"openai_like":re.compile(r"sk-[A-Za-z0-9_-]{24,}"),
          "huggingface_like":re.compile(r"hf_[A-Za-z0-9]{25,}"),
          "aws_access_id":re.compile(r"AKIA[0-9A-Z]{16}"),
          "private_key":re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")}
excluded={".venv","runtime","models",".git","__pycache__","data","environment"}
findings=[]
count=0
for path in root.rglob("*"):
    if any(p in excluded for p in path.relative_to(root).parts) or not path.is_file():
        continue
    if path.suffix.lower() not in {".py",".md",".json",".toml",".yaml",".yml",".txt",".env"} or path.stat().st_size>2_000_000:
        continue
    count+=1
    content=path.read_text(encoding="utf-8",errors="replace")
    for name,pattern in patterns.items():
        for match in pattern.finditer(content):
            findings.append({"file":str(path.relative_to(root)),"line":content.count("\n",0,match.start())+1,"pattern":name})
report={"status":"review_required" if findings else "no_matches_in_scanned_patterns","files_scanned":count,
        "findings":findings,"limitation":"Pattern-based scan cannot prove absence of every secret or provider-side revocation"}
out=root / "runtime/security-scan.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2))
raise SystemExit(bool(findings))
