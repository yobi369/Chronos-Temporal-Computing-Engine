"""Optional Ed25519 signing for portable Chronos experiment reports."""
from __future__ import annotations

import base64
import binascii
import getpass
import hashlib
import json
from pathlib import Path
from typing import Any, NoReturn, cast

from chronos.event_log import EventLogError

SIGNATURE_FILENAME = "signature.json"
SIGNATURE_FORMAT = "chronos-report-signature"
DOMAIN_SEPARATOR = b"CHRONOS-REPORT-SIGNATURE\x00v1\x00"
MAX_KEY_FILE_BYTES = 64 * 1024
MAX_SIGNATURE_ENVELOPE_BYTES = 16 * 1024
_FIELDS = {
    "format",
    "version",
    "algorithm",
    "key_id",
    "public_key",
    "report_sha256",
    "signature",
}


def _crypto() -> tuple[Any, Any, Any]:
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
            Ed25519PublicKey,
        )
    except ImportError as exc:
        message = (
            "Ed25519 support requires: pip install "
            "'chronos-temporal-computing-engine[signing]'"
        )
        raise EventLogError(message) from exc
    return serialization, Ed25519PrivateKey, Ed25519PublicKey


def _read_bounded(path: str | Path, *, limit: int, label: str) -> bytes:
    try:
        with Path(path).open("rb") as stream:
            data = stream.read(limit + 1)
    except OSError as exc:
        raise EventLogError(f"cannot read {label} {path}: {exc}") from exc
    if len(data) > limit:
        raise EventLogError(f"{path}: {label} exceeds the {limit}-byte limit")
    return data


def _read(path: str | Path) -> bytes:
    return _read_bounded(path, limit=MAX_KEY_FILE_BYTES, label="key file")


def _raw(key: Any) -> bytes:
    serialization, _, _ = _crypto()
    return cast(
        bytes,
        key.public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        ),
    )


def _key_id(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _message(data: bytes) -> bytes:
    return DOMAIN_SEPARATOR + data


def sign_report_manifest(
    report_path: str | Path,
    private_key_path: str | Path,
) -> dict[str, object]:
    serialization, private_type, _ = _crypto()
    key_data = _read(private_key_path)
    try:
        key = serialization.load_pem_private_key(key_data, password=None)
    except TypeError:
        try:
            password = getpass.getpass("Private key passphrase: ").encode("utf-8")
        except (EOFError, OSError) as exc:
            raise EventLogError(
                "cannot prompt for the encrypted Ed25519 private-key passphrase"
            ) from exc
        try:
            key = serialization.load_pem_private_key(key_data, password=password)
        except (TypeError, ValueError) as exc:
            raise EventLogError(
                "cannot decrypt or parse the Ed25519 private key"
            ) from exc
    except ValueError as exc:
        raise EventLogError("cannot parse the Ed25519 private key") from exc

    if not isinstance(key, private_type):
        raise EventLogError("signing key must be an Ed25519 private key")

    report = Path(report_path)
    try:
        data = report.read_bytes()
    except OSError as exc:
        raise EventLogError(f"cannot read report manifest {report}: {exc}") from exc

    public_bytes = _raw(key.public_key())
    envelope: dict[str, object] = {
        "format": SIGNATURE_FORMAT,
        "version": 1,
        "algorithm": "Ed25519",
        "key_id": _key_id(public_bytes),
        "public_key": base64.b64encode(public_bytes).decode("ascii"),
        "report_sha256": hashlib.sha256(data).hexdigest(),
        "signature": base64.b64encode(key.sign(_message(data))).decode("ascii"),
    }
    envelope_path = report.with_name(SIGNATURE_FILENAME)
    try:
        envelope_path.write_text(
            json.dumps(envelope, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise EventLogError(f"cannot write signature envelope {envelope_path}: {exc}") from exc
    return envelope


def _load_object(path: Path) -> dict[str, Any]:
    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise EventLogError(f"{path}: duplicate JSON field {key!r}")
            result[key] = value
        return result

    def reject_constant(value: str) -> NoReturn:
        raise EventLogError(f"{path}: non-standard JSON constant {value!r}")

    raw = _read_bounded(
        path,
        limit=MAX_SIGNATURE_ENVELOPE_BYTES,
        label="signature envelope",
    )
    try:
        source = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EventLogError(f"{path}: signature envelope must be UTF-8") from exc

    try:
        document = json.loads(
            source,
            object_pairs_hook=hook,
            parse_constant=reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise EventLogError(f"{path}: invalid signature JSON: {exc}") from exc
    except RecursionError as exc:
        raise EventLogError(f"{path}: signature JSON nesting is excessive") from exc
    if not isinstance(document, dict) or set(document) != _FIELDS:
        raise EventLogError("signature envelope has missing or unknown fields")
    return document


def _decode(value: Any, label: str, size: int) -> bytes:
    if not isinstance(value, str):
        raise EventLogError(f"signature envelope {label} must be base64")
    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise EventLogError(
            f"signature envelope {label} is invalid base64"
        ) from exc
    canonical = base64.b64encode(raw).decode("ascii")
    if canonical != value or len(raw) != size:
        raise EventLogError(
            f"signature envelope {label} has invalid encoding or length"
        )
    return raw


def verify_report_signature(
    report_path: str | Path,
    *,
    trusted_public_key_path: str | Path | None = None,
) -> dict[str, object]:
    serialization, _, public_type = _crypto()
    manifest = Path(report_path)
    envelope_path = manifest.with_name(SIGNATURE_FILENAME)
    envelope = _load_object(envelope_path)

    if (
        envelope["format"] != SIGNATURE_FORMAT
        or type(envelope["version"]) is not int
        or envelope["version"] != 1
    ):
        raise EventLogError("unsupported signature envelope format or version")
    if envelope["algorithm"] != "Ed25519":
        raise EventLogError("unsupported report signature algorithm")

    key_id = envelope["key_id"]
    digest = envelope["report_sha256"]
    if (
        not isinstance(key_id, str)
        or len(key_id) != 64
        or any(char not in "0123456789abcdef" for char in key_id)
    ):
        raise EventLogError("signature envelope has invalid key identifier")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(char not in "0123456789abcdef" for char in digest)
    ):
        raise EventLogError("signature envelope has invalid report digest")

    public_bytes = _decode(envelope["public_key"], "public_key", 32)
    signature = _decode(envelope["signature"], "signature", 64)
    if _key_id(public_bytes) != key_id:
        raise EventLogError("signature envelope key identifier mismatch")

    try:
        report_bytes = manifest.read_bytes()
    except OSError as exc:
        raise EventLogError(f"cannot read report manifest {manifest}: {exc}") from exc
    if hashlib.sha256(report_bytes).hexdigest() != digest:
        raise EventLogError("signed report manifest SHA-256 digest mismatch")

    try:
        public_type.from_public_bytes(public_bytes).verify(
            signature,
            _message(report_bytes),
        )
    except Exception as exc:
        raise EventLogError("report signature is invalid") from exc

    trusted = False
    if trusted_public_key_path is not None:
        try:
            trusted_key = serialization.load_pem_public_key(
                _read(trusted_public_key_path)
            )
        except (ValueError, TypeError) as exc:
            raise EventLogError(
                "cannot parse trusted Ed25519 public key"
            ) from exc
        if not isinstance(trusted_key, public_type):
            raise EventLogError("trusted key must be an Ed25519 public key")
        trusted = _raw(trusted_key) == public_bytes

    return {
        "signature_valid": True,
        "trust_status": "trusted" if trusted else "untrusted",
        "key_id": key_id,
        "algorithm": "Ed25519",
        "trust_note": (
            "Trusted means exact match with the explicitly supplied local public key; "
            "it does not establish legal identity, authorization, revocation, or trusted time."
        ),
    }
