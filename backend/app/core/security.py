"""JWT認証、パスワードハッシュ、トークン暗号化モジュール。

bcryptによるパスワードハッシュ、python-joseによるJWT生成・検証、
cryptographyによるAES-256-GCMトークン暗号化を提供する。
"""

import base64
import os
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import JWTError, jwt

from app.config import settings

# ---------------------------------------------------------------------------
# パスワードハッシュ (bcrypt)
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """平文パスワードをbcryptでハッシュ化する。

    Args:
        password: 平文パスワード。

    Returns:
        bcryptハッシュ文字列。
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """平文パスワードとハッシュを照合する。

    Args:
        plain: 平文パスワード。
        hashed: bcryptハッシュ文字列。

    Returns:
        一致する場合True。
    """
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ---------------------------------------------------------------------------
# JWT (HS256)
# ---------------------------------------------------------------------------

def create_access_token(user_id: int) -> str:
    """アクセストークンを生成する。

    Args:
        user_id: ユーザーID。

    Returns:
        JWT文字列（HS256署名）。
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict = {
        "sub": str(user_id),
        "type": "access",
        "exp": expire,
        "iat": now,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def create_refresh_token(user_id: int) -> str:
    """リフレッシュトークンを生成する。

    jtiとしてUUID4を含め、トークン無効化に利用可能とする。

    Args:
        user_id: ユーザーID。

    Returns:
        JWT文字列（HS256署名）。
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload: dict = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "exp": expire,
        "iat": now,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def verify_token(token: str, token_type: str = "access") -> dict:
    """JWTトークンを検証しペイロードを返す。

    Args:
        token: JWT文字列。
        token_type: 期待するトークン種別 ("access" | "refresh")。

    Returns:
        デコード済みペイロード辞書。

    Raises:
        JWTError: トークンが無効、期限切れ、または種別が不一致の場合。
    """
    try:
        payload: dict = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )
    except JWTError:
        raise

    if payload.get("type") != token_type:
        raise JWTError(f"Invalid token type: expected {token_type}")

    return payload


# ---------------------------------------------------------------------------
# トークン暗号化 (AES-256-GCM)
# ---------------------------------------------------------------------------

def _get_aes_key() -> bytes:
    """settings.ENCRYPTION_KEY から32バイトのAES鍵を取得する。

    ENCRYPTION_KEY は64文字のhex文字列（32バイト相当）を想定。

    Returns:
        32バイトの鍵。
    """
    return bytes.fromhex(settings.ENCRYPTION_KEY)


def encrypt_token(plaintext: str) -> str:
    """平文トークンをAES-256-GCMで暗号化し、base64エンコードして返す。

    出力形式: base64(nonce + ciphertext + tag)

    Args:
        plaintext: 暗号化する平文文字列。

    Returns:
        base64エンコードされた暗号文。
    """
    key = _get_aes_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 12バイトのnonce
    ciphertext: bytes = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    # nonce(12) + ciphertext+tag を結合してbase64
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def decrypt_token(encrypted: str) -> str:
    """base64エンコードされた暗号文を復号する。

    Args:
        encrypted: encrypt_token() で生成されたbase64文字列。

    Returns:
        復号された平文文字列。

    Raises:
        Exception: 復号に失敗した場合。
    """
    key = _get_aes_key()
    aesgcm = AESGCM(key)
    raw: bytes = base64.urlsafe_b64decode(encrypted)
    nonce = raw[:12]
    ciphertext = raw[12:]
    plaintext_bytes: bytes = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext_bytes.decode("utf-8")
