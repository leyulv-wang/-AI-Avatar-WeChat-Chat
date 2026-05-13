from __future__ import annotations

from pathlib import Path

from wxbot.backup import create_backup, restore_backup


def test_backup_create_and_restore(tmp_path: Path):
    data_dir = tmp_path / "data"
    backup_dir = tmp_path / "backups"
    (data_dir / "a").mkdir(parents=True)
    (data_dir / "a" / "x.txt").write_text("hello", encoding="utf-8")

    z = create_backup(data_dir=data_dir, backup_dir=backup_dir)
    assert z.exists()

    restored = tmp_path / "restored"
    restore_backup(backup_zip=z, data_dir=restored)
    assert (restored / "a" / "x.txt").read_text(encoding="utf-8") == "hello"

