# ruff: noqa: E501, E701, E702
"""Authenticated worker transport with durable SQLite inbox/outbox and retry delivery."""
from __future__ import annotations
import asyncio
from contextlib import contextmanager
from collections.abc import Iterator
import hashlib
import hmac
import json
import sqlite3
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

MAX_MESSAGE_BYTES=1024*1024

class WorkerProtocolError(ValueError):
    pass

def _canonical(value: Any) -> bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")

def sign_message(message: dict[str,Any], secret: bytes) -> dict[str,Any]:
    if len(secret)<32: raise ValueError("worker HMAC secret must contain at least 32 bytes")
    body={"message_id":message["message_id"],"source":message["source"],
        "target":message["target"],"kind":message["kind"],"payload":message["payload"]}
    signature=hmac.new(secret,_canonical(body),hashlib.sha256).hexdigest()
    return {"message":body,"signature":signature}

def sign_ack(message_id: str, secret: bytes, *, accepted: bool, duplicate: bool=False) -> dict[str,Any]:
    body={"message_id":message_id,"accepted":accepted,"duplicate":duplicate}
    return {"ack":body,"signature":hmac.new(secret,_canonical(body),hashlib.sha256).hexdigest()}

def verify_ack(document: dict[str,Any],message_id: str,secret: bytes) -> bool:
    if not isinstance(document,dict) or set(document)!={"ack","signature"} or not isinstance(document["ack"],dict): return False
    body=document["ack"]
    if set(body)!={"message_id","accepted","duplicate"} or body["message_id"]!=message_id: return False
    expected=hmac.new(secret,_canonical(body),hashlib.sha256).hexdigest()
    return isinstance(document["signature"],str) and hmac.compare_digest(expected,document["signature"]) and body["accepted"] is True

def verify_message(document: dict[str,Any], secret: bytes) -> dict[str,Any]:
    if not isinstance(document,dict) or set(document)!={"message","signature"} or not isinstance(document["message"],dict):
        raise WorkerProtocolError("invalid authenticated message envelope")
    message=document["message"]
    if set(message)!={"message_id","source","target","kind","payload"}:
        raise WorkerProtocolError("invalid message fields")
    if any(not isinstance(message[k],str) or not message[k] for k in ("message_id","source","target","kind")):
        raise WorkerProtocolError("message identity fields must be non-empty strings")
    if not isinstance(message["payload"],dict): raise WorkerProtocolError("payload must be an object")
    expected=hmac.new(secret,_canonical(message),hashlib.sha256).hexdigest()
    if not isinstance(document["signature"],str) or not hmac.compare_digest(expected,document["signature"]):
        raise WorkerProtocolError("message authentication failed")
    return message

class DurableMessageStore:
    """SQLite WAL-backed durable outbox/inbox; use one database per worker."""
    def __init__(self,path: str|Path) -> None:
        self.path=str(path)
        with self._session() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("CREATE TABLE IF NOT EXISTS outbox (message_id TEXT PRIMARY KEY, body BLOB NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, next_at REAL NOT NULL DEFAULT 0, last_error TEXT)")
            db.execute("CREATE TABLE IF NOT EXISTS inbox (message_id TEXT PRIMARY KEY, body BLOB NOT NULL, received_at REAL NOT NULL, processed INTEGER NOT NULL DEFAULT 0)")
    def _connect(self) -> sqlite3.Connection:
        db=sqlite3.connect(self.path,timeout=10)
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA synchronous=FULL")
        return db
    @contextmanager
    def _session(self) -> Iterator[sqlite3.Connection]:
        db=self._connect()
        try:
            with db:
                yield db
        finally:
            db.close()
    def enqueue(self,document: dict[str,Any],secret: bytes) -> None:
        message=verify_message(document,secret)
        body=_canonical(document)
        with self._session() as db:
            row=db.execute("SELECT body FROM outbox WHERE message_id=?",(message["message_id"],)).fetchone()
            if row is not None and bytes(row[0])!=body: raise WorkerProtocolError("outbox message ID conflict")
            db.execute("INSERT OR IGNORE INTO outbox(message_id,body) VALUES(?,?)",(message["message_id"],body))
    def due(self,now: float|None=None,limit: int=100) -> tuple[dict[str,Any],...]:
        if limit<1: raise ValueError("limit must be positive")
        instant=time.time() if now is None else now
        with self._session() as db:
            rows=db.execute("SELECT body FROM outbox WHERE next_at<=? ORDER BY next_at,message_id LIMIT ?",(instant,limit)).fetchall()
        return tuple(json.loads(bytes(row[0])) for row in rows)
    def acknowledge(self,message_id: str) -> None:
        with self._session() as db: db.execute("DELETE FROM outbox WHERE message_id=?",(message_id,))
    def fail(self,message_id: str,error: str,*,now: float|None=None,base_delay: float=0.25,max_delay: float=60) -> None:
        instant=time.time() if now is None else now
        with self._session() as db:
            row=db.execute("SELECT attempts FROM outbox WHERE message_id=?",(message_id,)).fetchone()
            if row is None: return
            attempts=int(row[0])+1
            delay=min(max_delay,base_delay*(2**min(attempts-1,20)))
            db.execute("UPDATE outbox SET attempts=?,next_at=?,last_error=? WHERE message_id=?",
                (attempts,instant+delay,error[:1000],message_id))
    def accept(self,message: dict[str,Any],*,now: float|None=None) -> bool:
        body=_canonical(message); instant=time.time() if now is None else now
        with self._session() as db:
            row=db.execute("SELECT body FROM inbox WHERE message_id=?",(message["message_id"],)).fetchone()
            if row is not None:
                if bytes(row[0])!=body: raise WorkerProtocolError("inbox message ID conflict")
                return False
            db.execute("INSERT INTO inbox(message_id,body,received_at) VALUES(?,?,?)",
                (message["message_id"],body,instant))
            return True
    def inbox_pending(self,limit: int=100) -> tuple[dict[str,Any],...]:
        with self._session() as db:
            rows=db.execute("SELECT body FROM inbox WHERE processed=0 ORDER BY received_at,message_id LIMIT ?",(limit,)).fetchall()
        return tuple(json.loads(bytes(row[0])) for row in rows)
    def mark_processed(self,message_id: str) -> None:
        with self._session() as db: db.execute("UPDATE inbox SET processed=1 WHERE message_id=?",(message_id,))
    def pending_count(self) -> int:
        with self._session() as db: return int(db.execute("SELECT COUNT(*) FROM outbox").fetchone()[0])

class WorkerServer:
    def __init__(self,worker_id: str,secret: bytes,store: DurableMessageStore,*,ssl_context: Any=None) -> None:
        if not worker_id or len(secret)<32: raise ValueError("worker ID and 32-byte secret are required")
        self.worker_id=worker_id; self.secret=secret; self.store=store; self.ssl_context=ssl_context
        self._server: asyncio.AbstractServer|None=None
        self._handlers: dict[str,Any]={}
    def register_handler(self,kind: str,handler: Any) -> None:
        if not kind or kind in self._handlers: raise ValueError("worker handler kind must be unique")
        self._handlers[kind]=handler
    def process_pending(self,limit: int=100) -> int:
        """Process durable inbox rows at least once; handlers must be idempotent."""
        processed=0
        for message in self.store.inbox_pending(limit):
            handler=self._handlers.get(message["kind"])
            if handler is None: continue
            handler(message)
            self.store.mark_processed(message["message_id"])
            processed+=1
        return processed
    async def run_forever(self,stop_event: asyncio.Event,*,poll_interval: float=0.1) -> None:
        """Continuously drain durable inbox work until the supplied stop event is set."""
        if poll_interval<=0: raise ValueError("poll_interval must be positive")
        while not stop_event.is_set():
            processed=await asyncio.to_thread(self.process_pending)
            if processed==0:
                try: await asyncio.wait_for(stop_event.wait(),timeout=poll_interval)
                except TimeoutError: pass
    async def start(self,host: str="127.0.0.1",port: int=0) -> tuple[str,int]:
        self._server=await asyncio.start_server(self._handle,host,port,ssl=self.ssl_context,limit=MAX_MESSAGE_BYTES+1)
        sockets=self._server.sockets
        if not sockets: raise RuntimeError("worker server started without a listening socket")
        socket=sockets[0]
        address=socket.getsockname()
        return str(address[0]),int(address[1])
    async def _handle(self,reader: asyncio.StreamReader,writer: asyncio.StreamWriter) -> None:
        try:
            raw=await asyncio.wait_for(reader.readline(),timeout=10)
            if not raw or len(raw)>MAX_MESSAGE_BYTES: raise WorkerProtocolError("message size or framing invalid")
            document=json.loads(raw)
            message=verify_message(document,self.secret)
            if message["target"]!=self.worker_id: raise WorkerProtocolError("message addressed to another worker")
            accepted=self.store.accept(message)
            writer.write(_canonical(sign_ack(message["message_id"],self.secret,accepted=True,duplicate=not accepted))+b"\n")
            await writer.drain()
        except (ValueError,TimeoutError,TypeError):
            writer.write(b'{"accepted":false}\n')
            try: await writer.drain()
            except OSError: pass
        finally:
            writer.close()
            try: await writer.wait_closed()
            except OSError: pass
    async def close(self) -> None:
        if self._server is not None:
            self._server.close(); await self._server.wait_closed(); self._server=None

class WorkerClient:
    def __init__(self,source_id: str,secret: bytes,store: DurableMessageStore,*,ssl_context: Any=None) -> None:
        if not source_id or len(secret)<32: raise ValueError("worker ID and 32-byte secret are required")
        self.source_id=source_id; self.secret=secret; self.store=store; self.ssl_context=ssl_context
    def publish(self,target: str,kind: str,payload: dict[str,Any],*,message_id: str|None=None) -> str:
        stable_id=message_id if message_id is not None else str(uuid4())
        message: dict[str,Any]={"message_id":stable_id,"source":self.source_id,
            "target":target,"kind":kind,"payload":payload}
        document=sign_message(message,self.secret)
        if len(_canonical(document))>MAX_MESSAGE_BYTES: raise WorkerProtocolError("message exceeds maximum size")
        self.store.enqueue(document,self.secret)
        return stable_id
    async def deliver_pending(self,host: str,port: int,*,now: float|None=None,
        limit: int=100,timeout: float=3.0) -> tuple[int,int]:
        delivered=failed=0
        for document in self.store.due(now,limit):
            message=document["message"]; message_id=message["message_id"]
            try:
                reader,writer=await asyncio.wait_for(asyncio.open_connection(host,port,ssl=self.ssl_context),timeout)
                writer.write(_canonical(document)+b"\n"); await writer.drain()
                response=await asyncio.wait_for(reader.readline(),timeout)
                writer.close(); await writer.wait_closed()
                if len(response)>1024 or not verify_ack(json.loads(response),message_id,self.secret):
                    raise WorkerProtocolError("remote worker rejected message or returned an invalid acknowledgement")
                self.store.acknowledge(message_id); delivered+=1
            except (OSError,TimeoutError,ValueError,TypeError) as exc:
                self.store.fail(message_id,str(exc),now=now); failed+=1
        return delivered,failed
