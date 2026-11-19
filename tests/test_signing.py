"""Negative-format and key-handling tests for signed Chronos reports."""
from __future__ import annotations

import base64
import json

import pytest

from chronos.event_log import EventLogError
from chronos.signing import (
    MAX_KEY_FILE_BYTES,
    MAX_SIGNATURE_ENVELOPE_BYTES,
    _load_object,
    _read,
    sign_report_manifest,
    verify_report_signature,
)


def _signed_report(tmp_path):
    crypto = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.ed25519")
    from cryptography.hazmat.primitives import serialization

    private = crypto.Ed25519PrivateKey.generate()
    private_path = tmp_path / "signer-private.pem"
    report_path = tmp_path / "report.json"
    private_path.write_bytes(
        private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    report_path.write_bytes(b'{"format":"test-report","version":1}\n')
    sign_report_manifest(report_path, private_path)
    return report_path, report_path.with_name("signature.json"), private


def _write_envelope(path, envelope):
    path.write_text(
        json.dumps(envelope, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_signature_envelope_rejects_duplicate_json_fields(tmp_path):
    path = tmp_path / "signature.json"
    path.write_text('{"format":"first","format":"second"}', encoding="utf-8")

    with pytest.raises(EventLogError, match="duplicate JSON field"):
        _load_object(path)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (b"\xff", "must be UTF-8"),
        (b'{"value":NaN}', "non-standard JSON constant"),
    ],
)
def test_signature_envelope_rejects_invalid_json_encodings(tmp_path, payload, message):
    path = tmp_path / "signature.json"
    path.write_bytes(payload)

    with pytest.raises(EventLogError, match=message):
        _load_object(path)


def test_signature_envelope_has_a_strict_size_limit(tmp_path):
    path = tmp_path / "signature.json"
    path.write_bytes(b" " * (MAX_SIGNATURE_ENVELOPE_BYTES + 1))

    with pytest.raises(EventLogError, match="signature envelope exceeds"):
        _load_object(path)


def test_key_files_have_a_strict_size_limit(tmp_path):
    path = tmp_path / "oversized-key.pem"
    path.write_bytes(b"x" * (MAX_KEY_FILE_BYTES + 1))

    with pytest.raises(EventLogError, match="key file exceeds"):
        _read(path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("version", 2, "unsupported signature envelope"),
        ("algorithm", "RSA-PSS", "unsupported report signature algorithm"),
    ],
)
def test_signature_verification_rejects_unsupported_format_values(
    tmp_path, field, value, message
):
    report_path, envelope_path, _ = _signed_report(tmp_path)
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    envelope[field] = value
    _write_envelope(envelope_path, envelope)

    with pytest.raises(EventLogError, match=message):
        verify_report_signature(report_path)


def test_signature_verification_rejects_key_identifier_mismatch(tmp_path):
    report_path, envelope_path, _ = _signed_report(tmp_path)
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    envelope["key_id"] = "0" * 64
    _write_envelope(envelope_path, envelope)

    with pytest.raises(EventLogError, match="key identifier mismatch"):
        verify_report_signature(report_path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("public_key", "%%%", "invalid base64"),
        ("signature", base64.b64encode(b"short").decode("ascii"), "invalid encoding or length"),
    ],
)
def test_signature_verification_rejects_malformed_base64_fields(
    tmp_path, field, value, message
):
    report_path, envelope_path, _ = _signed_report(tmp_path)
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    envelope[field] = value
    _write_envelope(envelope_path, envelope)

    with pytest.raises(EventLogError, match=message):
        verify_report_signature(report_path)


def test_signature_verification_rejects_signature_byte_tampering(tmp_path):
    report_path, envelope_path, _ = _signed_report(tmp_path)
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    signature = base64.b64decode(envelope["signature"], validate=True)
    changed = bytes([signature[0] ^ 1]) + signature[1:]
    envelope["signature"] = base64.b64encode(changed).decode("ascii")
    _write_envelope(envelope_path, envelope)

    with pytest.raises(EventLogError, match="signature is invalid"):
        verify_report_signature(report_path)


def test_encrypted_private_key_uses_passphrase_prompt(tmp_path, monkeypatch):
    crypto = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.ed25519")
    from cryptography.hazmat.primitives import serialization

    private = crypto.Ed25519PrivateKey.generate()
    private_path = tmp_path / "encrypted-private.pem"
    report_path = tmp_path / "report.json"
    private_path.write_bytes(
        private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.BestAvailableEncryption(b"test-passphrase"),
        )
    )
    report_path.write_bytes(b'{"format":"test-report","version":1}\n')
    monkeypatch.setattr(
        "chronos.signing.getpass.getpass",
        lambda prompt: "test-passphrase",
    )

    sign_report_manifest(report_path, private_path)

    result = verify_report_signature(report_path)
    assert result["signature_valid"] is True
    assert result["trust_status"] == "untrusted"

def test_signing_matches_fixed_chronos_ed25519_vector(tmp_path):
    crypto = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.ed25519")
    from cryptography.hazmat.primitives import serialization

    # Public RFC 8032 test seed; never use this key outside this deterministic test.
    seed = bytes.fromhex(
        "9d61b19deffd5a60ba844af492ec2cc4"
        "4449c5697b326919703bac031cae7f60"
    )
    private = crypto.Ed25519PrivateKey.from_private_bytes(seed)
    private_path = tmp_path / "vector-private.pem"
    report_path = tmp_path / "report.json"
    private_path.write_bytes(
        private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    report_path.write_bytes(b'{"format":"test-report","version":1}\n')

    envelope = sign_report_manifest(report_path, private_path)

    assert envelope["public_key"] == "11qYAYKxCrfVS/7TyWQHOg7hcvPapiMlrwIaaPcHURo="
    assert envelope["key_id"] == (
        "21fe31dfa154a261626bf854046fd227"
        "1b7bed4b6abe45aa58877ef47f9721b9"
    )
    assert envelope["signature"] == (
        "dO+S+UdA/BLFuVGeiF3qcBvuzs71DbJWM3uY3wsWR/5ECwZV"
        "sbWr1ffQJI4mdr2ZJrPX07G9MSEpZ5Agvym6Dg=="
    )
    result = verify_report_signature(report_path)
    assert result["signature_valid"] is True
    assert result["trust_status"] == "untrusted"


@pytest.mark.parametrize("operation", ["sign", "verify"])
def test_signing_fails_clearly_without_optional_dependency(
    monkeypatch, tmp_path, operation
):
    import builtins

    original_import = builtins.__import__

    def reject_cryptography(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "cryptography" or name.startswith("cryptography."):
            raise ImportError("simulated missing optional dependency")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", reject_cryptography)

    with pytest.raises(EventLogError, match=r"Ed25519 support requires: pip install"):
        if operation == "sign":
            sign_report_manifest(tmp_path / "unused-report.json", tmp_path / "unused-key.pem")
        else:
            verify_report_signature(tmp_path / "unused-report.json")
