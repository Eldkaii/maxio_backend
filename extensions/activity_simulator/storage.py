"""Atomic checkpoints and an OS-released exclusive process lock."""
from contextlib import contextmanager
import json
import os
import shutil
import uuid
from pathlib import Path


class Store:
    def __init__(self, path: Path):
        self.path = path

    def load(self):
        if not self.path.exists():
            return None
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if data.get("version") != 1:
            raise ValueError("Estado incompatible; no se reemplazará")
        return data

    def save(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self.path)

    def backup(self):
        """Local recovery copy; never print its sensitive contents. Hold the lock."""
        destination = self.path.with_name(self.path.name + ".recovery-" + uuid.uuid4().hex + ".bak")
        shutil.copy2(self.path, destination)
        return destination

    @contextmanager
    def lock(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.with_suffix(".lock").open("a+b") as handle:
            if os.name == "nt":
                import msvcrt
                handle.write(b"0")
                handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                yield
            finally:
                if os.name == "nt":
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle, fcntl.LOCK_UN)
