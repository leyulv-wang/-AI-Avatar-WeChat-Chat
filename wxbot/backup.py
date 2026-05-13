from __future__ import annotations

import time
import zipfile
from pathlib import Path


def create_backup(*, data_dir: Path, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    name = f"backup_{int(time.time())}.zip"
    out = backup_dir / name
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
        if data_dir.exists():
            for p in data_dir.rglob("*"):
                if p.is_file():
                    z.write(p, arcname=str(p.relative_to(data_dir)))
    return out


def restore_backup(*, backup_zip: Path, data_dir: Path) -> None:
    with zipfile.ZipFile(backup_zip, "r") as z:
        z.extractall(data_dir)

