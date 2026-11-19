
import pyotp
import qrcode
from io import BytesIO
import base64


def generate_totp_secret():
    return pyotp.random_base32()


def generate_totp_qr(email: str, secret: str):
    totp = pyotp.TOTP(secret)

    uri = totp.provisioning_uri(
        name=email,
        issuer_name="AI Resume Parser"
    )

    qr = qrcode.make(uri)

    buffer = BytesIO()
    qr.save(buffer, format="PNG")

    return base64.b64encode(
        buffer.getvalue()
    ).decode("utf-8")


def verify_totp_code(secret: str, code: str):
    totp = pyotp.TOTP(secret)
    return totp.verify(code.strip(), valid_window=1)
