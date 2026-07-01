import base64
import io
from datetime import timedelta

import pyotp
import qrcode
from cryptography.fernet import Fernet

from app.core.config import get_settings
from app.utils.security import create_access_token, decode_access_token

settings = get_settings()


class TOTPService:
    def __init__(self) -> None:
        self.fernet = Fernet(settings.totp_encryption_key.encode())

    def generate_secret(self) -> str:
        return pyotp.random_base32()

    def encrypt_secret(self, secret: str) -> str:
        return self.fernet.encrypt(secret.encode()).decode()

    def decrypt_secret(self, encrypted_secret: str) -> str:
        return self.fernet.decrypt(encrypted_secret.encode()).decode()

    def generate_qr_code_base64(self, secret: str, username: str) -> str:
        totp = pyotp.TOTP(secret, issuer_name="Student Weather Assistant")
        provisioning_url = totp.provisioning_uri(name=username, issuer_name="Student Weather Assistant")

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_bytes = buffer.getvalue()

        return f"data:image/png;base64,{base64.b64encode(qr_bytes).decode()}"

    def verify_totp(self, secret: str, code: str) -> bool:
        totp = pyotp.TOTP(secret)
        # Using valid_window=1 allows for +/- 30 seconds time drift (RFC 6238 compatible)
        return totp.verify(code, valid_window=1)

    def generate_temp_token(self, user_id: str, remember_me: bool = False) -> str:
        return create_access_token(
            subject=user_id,
            expires_delta=timedelta(minutes=5),
            extra_claims={"purpose": "2fa", "remember": remember_me}
        )

    def verify_temp_token(self, token: str) -> tuple[str, bool] | None:
        payload = decode_access_token(token)
        if not payload:
            return None
        if payload.get("purpose") != "2fa":
            return None
        return payload.get("sub"), bool(payload.get("remember"))
