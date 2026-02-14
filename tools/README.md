# MAVLink header generation helper

This folder contains a helper script to generate MAVLink C headers for use by the firmware.

Prerequisites
- Python 3.8+ (recommended inside a virtual environment)

Quick steps (Windows PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r tools/requirements.txt
python tools/generate_mavlink_headers.py --out src/Mavlink/gen
```

Notes
- The generator uses `pymavlink` to produce C headers from built-in MAVLink dialect XML files.
- If you see a cross-drive `relpath` error on Windows, the script uses absolute paths and should work; ensure the venv's Python and `pymavlink` are installed on the drive where the repo lives.
- The script is non-fatal: the repository includes a minimal stub at `src/Mavlink/gen/mavlink.h` if you choose not to generate headers locally.

If you want me to also commit the generated headers into the repo, tell me which dialect(s) (`common`, `minimal`, `standard`, etc.) you prefer and I'll add them.