"""Optional Ed25519 signing for portable Chronos experiment reports."""
from __future__ import annotations
import base64, binascii, getpass, hashlib, json
from pathlib import Path
from typing import Any
from chronos.event_log import EventLogError

SIGNATURE_FILENAME = "signature.json"
SIGNATURE_FORMAT = "chronos-report-signature"
DOMAIN_SEPARATOR = b"CHRONOS-REPORT-SIGNATURE\x00v1\x00"
_FIELDS = {"format", "version", "algorithm", "key_id", "public_key", "report_sha256", "signature"}

def _crypto() -> tuple[Any, Any, Any]:
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    except ImportError as exc:
        raise EventLogError("Ed25519 support requires: pip install 'chronos-temporal-computing-engine[signing]'") from exc
    return serialization, Ed25519PrivateKey, Ed25519PublicKey

def _read(path: str | Path) -> bytes:
    try: return Path(path).read_bytes()
    except OSError as exc: raise EventLogError(f"cannot read key file {path}: {exc}") from exc

def _raw(key: Any) -> bytes:
    serialization, _, _ = _crypto()
    return key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)

def _key_id(raw: bytes) -> str: return hashlib.sha256(raw).hexdigest()
def _message(data: bytes) -> bytes: return DOMAIN_SEPARATOR + data

def sign_report_manifest(report_path: str | Path, private_key_path: str | Path) -> dict[str, object]:
    serialization, Private, _ = _crypto()
    try: key = serialization.load_pem_private_key(_read(private_key_path), password=None)
    except TypeError:
        password = getpass.getpass("Private key passphrase: ").encode("utf-8")
        try: key = serialization.load_pem_private_key(_read(private_key_path), password=password)
        except (TypeError, ValueError) as exc: raise EventLogError("cannot decrypt or parse the Ed25519 private key") from exc
    except ValueError as exc: raise EventLogError("cannot parse the Ed25519 private key") from exc
    if not isinstance(key, Private): raise EventLogError("signing key must be an Ed25519 private key")
    report = Path(report_path); data = report.read_bytes(); pub = _raw(key.public_key())
    envelope = {"format":SIGNATURE_FORMAT,"version":1,"algorithm":"Ed25519","key_id":_key_id(pub),
        "public_key":base64.b64encode(pub).decode("ascii"),"report_sha256":hashlib.sha256(data).hexdigest(),
        "signature":base64.b64encode(key.sign(_message(data))).decode("ascii")}
    report.with_name(SIGNATURE_FILENAME).write_text(json.dumps(envelope,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return envelope

def _load_object(path: Path) -> dict[str, Any]:
    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        obj={}
        for k,v in pairs:
            if k in obj: raise EventLogError(f"{path}: duplicate JSON field {k!r}")
            obj[k]=v
        return obj
    try: obj=json.loads(path.read_text(encoding="utf-8"),object_pairs_hook=hook)
    except json.JSONDecodeError as exc: raise EventLogError(f"{path}: invalid signature JSON: {exc}") from exc
    if not isinstance(obj,dict) or set(obj)!=_FIELDS: raise EventLogError("signature envelope has missing or unknown fields")
    return obj

def _decode(value: Any, label: str, size: int) -> bytes:
    if not isinstance(value,str): raise EventLogError(f"signature envelope {label} must be base64")
    try: raw=base64.b64decode(value,validate=True)
    except (binascii.Error,ValueError) as exc: raise EventLogError(f"signature envelope {label} is invalid base64") from exc
    if base64.b64encode(raw).decode("ascii")!=value or len(raw)!=size: raise EventLogError(f"signature envelope {label} has invalid encoding or length")
    return raw

def verify_report_signature(
    report_path: str | Path, *, trusted_public_key_path: str | Path | None = None
) -> dict[str, object]:
    serialization, _, Public = _crypto()
    manifest=Path(report_path); envelope=_load_object(manifest.with_name(SIGNATURE_FILENAME))
    if envelope["format"]!=SIGNATURE_FORMAT or type(envelope["version"]) is not int or envelope["version"]!=1: raise EventLogError("unsupported signature envelope format or version")
    if envelope["algorithm"]!="Ed25519": raise EventLogError("unsupported report signature algorithm")
    kid=envelope["key_id"]; digest=envelope["report_sha256"]
    if not isinstance(kid,str) or len(kid)!=64 or any(c not in "0123456789abcdef" for c in kid): raise EventLogError("signature envelope has invalid key identifier")
    if not isinstance(digest,str) or len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest): raise EventLogError("signature envelope has invalid report digest")
    pub=_decode(envelope["public_key"],"public_key",32); sig=_decode(envelope["signature"],"signature",64)
    if _key_id(pub)!=kid: raise EventLogError("signature envelope key identifier mismatch")
    data=manifest.read_bytes()
    if hashlib.sha256(data).hexdigest()!=digest: raise EventLogError("signed report manifest SHA-256 digest mismatch")
    try: Public.from_public_bytes(pub).verify(sig,_message(data))
    except Exception as exc: raise EventLogError("report signature is invalid") from exc
    trusted=False
    if trusted_public_key_path is not None:
        try: key=serialization.load_pem_public_key(_read(trusted_public_key_path))
        except (ValueError,TypeError) as exc: raise EventLogError("cannot parse trusted Ed25519 public key") from exc
        if not isinstance(key,Public): raise EventLogError("trusted key must be an Ed25519 public key")
        trusted=_raw(key)==pub
    return {"signature_valid":True,"trust_status":"trusted" if trusted else "untrusted","key_id":kid,
        "algorithm":"Ed25519","trust_note":"Trusted means exact match with the explicitly supplied local public key; it does not establish legal identity, authorization, revocation, or trusted time."}
