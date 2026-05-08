import pyotp
import bcrypt
import qrcode
import io
import base64
from flask import current_app

def generate_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def check_password_hash(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def generate_mfa_secret() -> str:
    return pyotp.random_base32()

def get_mfa_uri(secret: str, email: str) -> str:
    issuer = current_app.config.get('OTP_ISSUER', 'DigitalIdentitySystem')
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)

def generate_qr_code_base64(uri: str) -> str:
    qr = qrcode.make(uri)
    buf = io.BytesIO()
    qr.save(buf, format='PNG')
    qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{qr_b64}"

def verify_mfa_token(secret: str, token: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=1)
