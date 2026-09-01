"""Hash-chained audit trail.

Every decision, human resolution, contract change and regression run appends
one record. Each record carries the hash of the one before it, so a record
cannot be removed or edited after the fact without breaking the chain -- which
is the difference between an audit trail and a log file.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = ROOT / "outputs" / "audit.jsonl"

GENESIS = "0" * 64


class AuditTrail:
    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def reset(self) -> None:
        self.path.write_text("")

    def _last_hash(self) -> tuple[int, str]:
        if not self.path.exists() or not self.path.stat().st_size:
            return 0, GENESIS
        last = None
        for line in self.path.read_text().splitlines():
            if line.strip():
                last = json.loads(line)
        return (last["seq"], last["hash"]) if last else (0, GENESIS)

    def append(self, event: str, payload: dict[str, Any]) -> dict[str, Any]:
        seq, prev = self._last_hash()
        record = {
            "seq": seq + 1,
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "event": event,
            "payload": payload,
            "prev_hash": prev,
        }
        record["hash"] = hashlib.sha256(
            json.dumps(record, sort_keys=True).encode()
        ).hexdigest()
        with self.path.open("a") as fh:
            fh.write(json.dumps(record) + "\n")
        return record

    def records(self) -> Iterator[dict[str, Any]]:
        if not self.path.exists():
            return iter(())
        return (json.loads(l) for l in self.path.read_text().splitlines() if l.strip())

    def verify(self) -> tuple[bool, str]:
        prev = GENESIS
        n = 0
        for rec in self.records():
            n += 1
            if rec["prev_hash"] != prev:
                return False, f"chain broken at seq {rec['seq']}: prev_hash does not match"
            body = {k: v for k, v in rec.items() if k != "hash"}
            if hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() != rec["hash"]:
                return False, f"record {rec['seq']} has been modified since it was written"
            prev = rec["hash"]
        return True, f"{n} records verified; chain intact"
