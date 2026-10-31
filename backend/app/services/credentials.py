"""VC-style signed enrolment records with Ed25519, live revocation and QR.

These are NOT W3C-conformant verifiable credentials and make no official claim.
No APAAR, name or date of birth is placed in the credential or the QR.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import secrets
from datetime import datetime

from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.crypto import decrypt_text
from app.models import Credential, Enrolment, Institution, Programme


def generate_institution_keys() -> tuple[str, str]:
    key = SigningKey.generate()
    return (
        bytes(key.verify_key).hex(),
        base64.b64encode(bytes(key)).decode(),
    )


def canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _signing_key(institution: Institution) -> SigningKey:
    raw = decrypt_text(institution.private_key_enc)
    if not raw:
        raise ValueError("Institution signing key is unavailable.")
    return SigningKey(base64.b64decode(raw))


def issue_credential(db: Session, enrollment: Enrolment, institution: Institution) -> Credential:
    programme = db.get(Programme, enrollment.programme_id)
    if programme is None:
        raise ValueError("Programme not found.")
    credential_id = "cred_" + secrets.token_hex(8)
    payload = {
        "id": credential_id,
        "type": "EnrolmentCredential",
        "issuer": {
            "institution_id": institution.id,
            "institution_code": institution.aicte_code,
            "name": institution.name,
            "key_id": f"inst-{institution.id}-key-1",
        },
        "subject": {"enrolment_ref": enrollment.enrolment_ref},
        "claims": {
            "programme": programme.name,
            "programme_code": programme.code,
            "academic_year": enrollment.academic_year,
            "status": "enrolled",
            "seat_category": enrollment.seat_category,
        },
        "issuedAt": datetime.utcnow().isoformat() + "Z",
        "statusRef": credential_id,
        "disclaimer": "VC-style signed record for a prototype. Not an official APAAR certificate.",
    }
    signature = base64.b64encode(_signing_key(institution).sign(canonical(payload)).signature).decode()
    credential = Credential(
        credential_id=credential_id,
        enrolment_id=enrollment.id,
        issuer_institution_id=institution.id,
        payload_json=json.dumps(payload, sort_keys=True),
        signature=signature,
        status="valid",
    )
    db.add(credential)
    enrollment.status = "verified"
    db.flush()
    return credential


def verify_credential(db: Session, credential_id: str) -> dict:
    credential = db.scalars(
        select(Credential).where(Credential.credential_id == credential_id)
    ).first()
    if credential is None:
        return {
            "status": "NOT_FOUND",
            "credential_id": credential_id,
            "message": "No credential exists for this reference.",
            "simulated": True,
        }
    institution = db.get(Institution, credential.issuer_institution_id)
    try:
        payload = json.loads(credential.payload_json)
    except json.JSONDecodeError:
        payload = {}
    signature_ok = False
    if institution and institution.public_key:
        try:
            VerifyKey(bytes.fromhex(institution.public_key)).verify(
                canonical(payload), base64.b64decode(credential.signature)
            )
            signature_ok = True
        except (BadSignatureError, ValueError):
            signature_ok = False

    if credential.status == "revoked":
        status = "REVOKED"
        message = "This credential was revoked by the issuing institution."
    elif not signature_ok:
        status = "TAMPERED"
        message = "The signature does not match the credential contents."
    else:
        status = "VALID"
        message = "Signature verified and the credential is active."
    return {
        "status": status,
        "credential_id": credential_id,
        "message": message,
        "simulated": True,
        "credential": payload,
        "issuer_name": institution.name if institution else None,
        "issuer_code": institution.aicte_code if institution else None,
        "issued_at": credential.issued_at.isoformat(),
        "revoked_at": credential.revoked_at.isoformat() if credential.revoked_at else None,
        "revoke_reason": credential.revoke_reason,
        "signature_valid": signature_ok,
    }


def revoke_credential(db: Session, credential_id: str, reason: str) -> Credential:
    credential = db.scalars(
        select(Credential).where(Credential.credential_id == credential_id)
    ).first()
    if credential is None:
        raise LookupError("Credential not found.")
    credential.status = "revoked"
    credential.revoked_at = datetime.utcnow()
    credential.revoke_reason = reason[:240]
    db.flush()
    return credential


def public_verify_url(credential_id: str) -> str:
    base = get_settings().public_base_url.rstrip("/")
    return f"{base}/verify/{credential_id}"


def qr_png(credential_id: str) -> bytes:
    import qrcode

    qr = qrcode.QRCode(box_size=8, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(public_verify_url(credential_id))
    qr.make(fit=True)
    image = qr.make_image(fill_color="#1F3864", back_color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def qr_svg(credential_id: str) -> str:
    import qrcode
    import qrcode.image.svg

    qr = qrcode.QRCode(box_size=8, border=2, image_factory=qrcode.image.svg.SvgPathImage)
    qr.add_data(public_verify_url(credential_id))
    qr.make(fit=True)
    image = qr.make_image()
    buffer = io.BytesIO()
    image.save(buffer)
    return buffer.getvalue().decode()


def credential_fingerprint(credential: Credential) -> str:
    return hashlib.sha256(credential.signature.encode()).hexdigest()[:16].upper()
