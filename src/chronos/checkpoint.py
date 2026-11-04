# ruff: noqa: E701, E702, E501
"""Crash-recoverable single-writer checkpoint generations."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

class CheckpointError(ValueError):
    pass

def _canonical(value: Any) -> bytes:
    try: return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")
    except (TypeError,ValueError) as exc: raise CheckpointError(f"checkpoint is not canonical JSON: {exc}") from exc

class CheckpointStore:
    """Atomic generation files plus an atomic CURRENT pointer; one writer per directory."""
    def __init__(self, directory: str|Path, *, max_bytes: int=64*1024*1024) -> None:
        if max_bytes<1: raise ValueError("max_bytes must be positive")
        self.directory=Path(directory); self.max_bytes=max_bytes
        self.directory.mkdir(parents=True,exist_ok=True)
    def _atomic_write(self,path: Path,data: bytes) -> None:
        fd,name=tempfile.mkstemp(prefix=".chronos-",dir=self.directory)
        try:
            with os.fdopen(fd,"wb") as stream:
                stream.write(data); stream.flush(); os.fsync(stream.fileno())
            os.replace(name,path)
            dir_fd=os.open(self.directory,os.O_RDONLY)
            try: os.fsync(dir_fd)
            finally: os.close(dir_fd)
        finally:
            if os.path.exists(name): os.unlink(name)
    def save(self,payload: dict[str,Any], *, generation: int) -> str:
        if generation<0: raise ValueError("generation must be non-negative")
        body=_canonical(payload)
        if len(body)>self.max_bytes: raise CheckpointError("checkpoint exceeds configured size limit")
        digest=hashlib.sha256(body).hexdigest()
        envelope=_canonical({"schema":1,"generation":generation,"sha256":digest,"payload":payload})
        if len(envelope)>self.max_bytes: raise CheckpointError("checkpoint envelope exceeds configured size limit")
        target=self.directory/f"checkpoint-{generation:020d}.json"
        self._atomic_write(target,envelope)
        self._atomic_write(self.directory/"CURRENT",f"{generation:020d}\n".encode())
        return digest
    def recover(self) -> tuple[int,dict[str,Any]]:
        pointer=self.directory/"CURRENT"
        if not pointer.exists(): raise CheckpointError("no committed checkpoint pointer")
        raw=pointer.read_text(encoding="ascii").strip()
        if not raw.isdigit(): raise CheckpointError("invalid CURRENT pointer")
        generation=int(raw); path=self.directory/f"checkpoint-{generation:020d}.json"
        data=path.read_bytes()
        if len(data)>self.max_bytes: raise CheckpointError("checkpoint exceeds configured size limit")
        try: envelope=json.loads(data)
        except (UnicodeDecodeError,json.JSONDecodeError) as exc: raise CheckpointError("checkpoint JSON is corrupt") from exc
        if not isinstance(envelope,dict) or set(envelope)!={"schema","generation","sha256","payload"} or envelope["schema"]!=1 or envelope["generation"]!=generation or not isinstance(envelope["payload"],dict):
            raise CheckpointError("checkpoint envelope is invalid")
        digest=hashlib.sha256(_canonical(envelope["payload"])).hexdigest()
        if digest!=envelope["sha256"]: raise CheckpointError("checkpoint checksum mismatch")
        return generation,envelope["payload"]
