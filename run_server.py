import os
import sys
from pathlib import Path

# Redirigir a backend/run_server.py
current_dir = Path(__file__).resolve().parent
candidates = [
    current_dir / "CDR-Graf-System-main" / "backend" / "run_server.py",
    current_dir / "backend" / "run_server.py",
]

target = next((p for p in candidates if p.exists()), None)
if target:
    import runpy
    sys.path.insert(0, str(target.parent))
    runpy.run_path(str(target), run_name="__main__")
else:
    print("[ERROR] No se encontro run_server.py en las carpetas del backend.")
    sys.exit(1)
