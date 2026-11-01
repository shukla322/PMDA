# BTP-local dependencies

From 27 October 2026, all active project assets must live inside BTP. Copy a needed external reference here before using it. Do not add imports, editable installations, model paths, or launch commands pointing to sibling projects.

| Location | Purpose |
|---|---|
| `.venv/` | Dedicated environment and scientific package payloads |
| `vendor/REINVENT4/` | Local engine source, editable-installed into this environment |
| `vendor/solitarius-mcp/` | Local MCP server with the existing Windows sampling adaptation |
| `models/reinvent_pubchem.prior` | Local sampling prior |
| `references/` | Paper, both original planning documents, upstream source metadata, and Windows patch |
| `src/pmda/` | Original project implementation |
| `runtime/` | Generated verification evidence and campaign artifacts |

## How this environment was established

A fresh Python 3.12 virtual environment was created in BTP. Installed scientific package payloads were copied from the previously verified local environment to avoid downloading the large CPU scientific stack again. Old editable-loader files and old executable launchers were excluded. REINVENT4 and PMDA were then installed from BTP source with `--no-deps --no-build-isolation --no-index`, rebuilding their editable registrations and executable launchers locally. Other optional package command-line launchers have not been migrated; use module entry points or install the corresponding package when needed.

The migrated payload is now frozen in `environment/windows-py312-packages.zip`, with a SHA256 manifest and pinned package list. `scripts/rebuild_environment.py` recreates it offline in a new BTP subdirectory and reinstalls local editable source. A fresh `runtime/recreated-py312` environment passed package checks, the import-origin audit and a real 100-molecule CPU baseline. This is a Windows x64 CPython 3.12 binary snapshot, not a cross-platform or independently rebuilt wheel bundle. System Python and OS libraries remain prerequisites. The `.venv`, models, runtime and bundle archive are ignored by Git; a Git checkout alone therefore does not include them.

## Provenance

`references/sources.json` preserves the recorded upstream URLs and commits. The copied engine and MCP licenses remain in their source directories. The server includes the pre-existing Windows adaptation preserved in `references/windows-sampling.patch`. Copying third-party code does not make it original PMDA code. The historical documents and prior run manifests retain original paths as evidence; these are not active dependency references.

The VECTOR project is not used by the current implementation and is not a runtime dependency. Future assets from it must be reviewed and copied into BTP before integration.

Hardware inventory found an NVIDIA GeForce RTX 3060 Laptop GPU with Windows driver 31.0.15.4630. The verified runtime uses CPU-only PyTorch. No claim of CUDA compatibility or GPU acceleration is made, and no driver/system package was modified. GPU support is a separately unverified capability.

## Verification

From BTP, run:

```powershell
& .\.venv\Scripts\python.exe -m pip check
& .\.venv\Scripts\python.exe scripts\audit_local.py
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
& .\.venv\Scripts\python.exe scripts\baseline.py
```

The audit rejects active package/distribution origins and local direct-URL installations outside BTP, checks required local assets and the recorded prior checksum, and writes `runtime/local-dependency-audit.json`. It is not an OS sandbox and does not assert that every unused upstream example works. The baseline exercises actual MCP-to-REINVENT CPU sampling with BTP paths.
