from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
import re
from pathlib import Path
from typing import Any, Iterable

from cryptography.fernet import Fernet


@dataclass(frozen=True)
class ContactPaths:
    contact_dir: Path
    events_path: Path
    profile_path: Path
    role_path: Path
    state_path: Path


_INVALID_WIN_CHARS = re.compile(r"[<>:\"/\\|?*\x00-\x1f]")


def _safe_dirname(name: str) -> str:
    name = name.strip()
    name = _INVALID_WIN_CHARS.sub("_", name)
    name = name.rstrip(". ")
    if not name:
        return "unknown"
    return name[:80]


def get_contact_paths(data_dir: Path, contact_id: str, *, encrypt: bool = True) -> ContactPaths:
    safe = _safe_dirname(contact_id)
    contact_dir = data_dir / "contacts" / safe
    return ContactPaths(
        contact_dir=contact_dir,
        events_path=contact_dir / ("events.jsonl.enc" if encrypt else "events.jsonl"),
        profile_path=contact_dir / ("profile.json.enc" if encrypt else "profile.json"),
        role_path=contact_dir / ("role.json.enc" if encrypt else "role.json"),
        state_path=contact_dir / ("state.json.enc" if encrypt else "state.json"),
    )


class EncryptedJSONStore:
    def __init__(self, path: Path, fernet: Fernet | None):
        self._path = path
        self._fernet = fernet

    def write(self, obj: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        plaintext = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        token = plaintext if self._fernet is None else self._fernet.encrypt(plaintext)
        tmp = self._path.with_suffix(self._path.suffix + f".{os.getpid()}.tmp")
        tmp.write_bytes(token)
        tmp.replace(self._path)

    def read(self) -> dict[str, Any] | None:
        if not self._path.exists():
            return None
        token = self._path.read_bytes()
        plaintext = token if self._fernet is None else self._fernet.decrypt(token)
        return json.loads(plaintext.decode("utf-8"))


class EncryptedJSONLStore:
    def __init__(self, path: Path, fernet: Fernet | None):
        self._path = path
        self._fernet = fernet

    def append(self, obj: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        plaintext = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if self._fernet is None:
            line = plaintext + b"\n"
        else:
            token = self._fernet.encrypt(plaintext)
            line = base64.urlsafe_b64encode(token) + b"\n"
        with self._path.open("ab") as f:
            f.write(line)

    def append_and_trim(self, obj: dict[str, Any], *, max_lines: int) -> None:
        self.append(obj)
        if max_lines <= 0:
            return
        if not self._path.exists():
            return
        lines = _tail_lines(self._path, max_lines)
        tmp = self._path.with_suffix(self._path.suffix + f".{os.getpid()}.tmp")
        with tmp.open("wb") as f:
            for ln in lines:
                f.write(ln + b"\n")
        tmp.replace(self._path)

    def tail(self, limit: int) -> list[dict[str, Any]]:
        if limit <= 0:
            return []
        if not self._path.exists():
            return []
        lines = _tail_lines(self._path, limit)
        out: list[dict[str, Any]] = []
        for line in lines:
            if self._fernet is None:
                out.append(json.loads(line.decode("utf-8")))
            else:
                token = base64.urlsafe_b64decode(line)
                plaintext = self._fernet.decrypt(token)
                out.append(json.loads(plaintext.decode("utf-8")))
        return out

    def iter_all(self) -> Iterable[dict[str, Any]]:
        if not self._path.exists():
            return
        with self._path.open("rb") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                if self._fernet is None:
                    yield json.loads(raw.decode("utf-8"))
                else:
                    token = base64.urlsafe_b64decode(raw)
                    plaintext = self._fernet.decrypt(token)
                    yield json.loads(plaintext.decode("utf-8"))


def _tail_lines(path: Path, limit: int) -> list[bytes]:
    with path.open("rb") as f:
        f.seek(0, os.SEEK_END)
        end = f.tell()
        block = 4096
        data = b""
        pos = end
        while pos > 0 and data.count(b"\n") <= limit:
            read_size = min(block, pos)
            pos -= read_size
            f.seek(pos)
            data = f.read(read_size) + data
        parts = [p for p in data.split(b"\n") if p]
        return parts[-limit:]
