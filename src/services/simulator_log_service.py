"""Read the optional simulator's activity log without importing the extension."""
from datetime import datetime, timezone
import os
from pathlib import Path
import sys

MAX_READ_BYTES = 256 * 1024


def read_simulator_log(limit=200, *, base_dir=None):
    if not 1 <= limit <= 500:
        raise ValueError("El límite debe estar entre 1 y 500")
    # Same location as the optional worker, including a packaged executable.
    base = Path(base_dir) if base_dir is not None else (
        Path(sys.executable).resolve().parent if getattr(sys, "frozen", False)
        else Path(__file__).resolve().parents[2]
    )
    path = base / "logs" / "activity-simulator.log"
    lines, available, updated_at, truncated = [], False, None, False
    remaining = MAX_READ_BYTES
    for suffix in ("", ".1", ".2", ".3"):
        candidate = path.with_name(path.name + suffix)
        if len(lines) >= limit or remaining <= 0:
            truncated = truncated or candidate.is_file()
            continue
        try:
            with candidate.open("rb") as stream:
                info = os.fstat(stream.fileno())
                available = True
                updated_at = max(updated_at or 0, info.st_mtime)
                size = info.st_size
                start = max(0, size - remaining)
                stream.seek(start)
                data = stream.read(size - start)
        except FileNotFoundError:
            # No activity yet, or a file moved during rotation.
            continue
        remaining -= len(data)
        if start:
            # The first bytes may start in the middle of a line or UTF-8 character.
            data = data.partition(b"\n")[2]
            truncated = True
        # Do not display a record while the writer is still appending it.
        data = data[:data.rfind(b"\n") + 1]
        chunk = data.decode("utf-8", errors="replace").splitlines()
        lines = chunk + lines
        if len(lines) > limit:
            lines = lines[-limit:]
            truncated = True
        if start:
            break
    return {
        "available": available,
        "lines": lines,
        "truncated": truncated,
        "updated_at": datetime.fromtimestamp(updated_at, timezone.utc).isoformat() if updated_at else None,
    }
