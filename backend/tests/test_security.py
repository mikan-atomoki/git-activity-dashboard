"""Tests for ``app.core.security`` — password hashing, JWT, encryption."""

from __future__ import annotations

import pytest
from jose import JWTError

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decrypt_token,
    encrypt_token,
    hash_password,
    verify_password,
    verify_token,
)


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


class TestPasswordHashing:
    """bcrypt hash / verify round-trip."""

    def test_hash_and_verify_correct_password(self) -> None:
        plain = "mysecretpassword"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_verify_wrong_password(self) -> None:
        hashed = hash_password("correct-password")
        assert verify_password("wrong-password", hashed) is False

    def test_hash_produces_different_output_each_time(self) -> None:
        """bcrypt uses a random salt, so two hashes of the same password
        should differ."""
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2

    def test_hash_returns_string(self) -> None:
        hashed = hash_password("abc")
        assert isinstance(hashed, str)
        # bcrypt hashes start with "$2b$"
        assert hashed.startswith("$2b$")


# ---------------------------------------------------------------------------
# JWT tokens
# ---------------------------------------------------------------------------


class TestJWT:
    """JWT creation and verification."""

    def test_access_token_round_trip(self) -> None:
        token = create_access_token(user_id=1)
        payload = verify_token(token, token_type="access")
        assert payload["sub"] == "1"
        assert payload["type"] == "access"

    def test_refresh_token_round_trip(self) -> None:
        token = create_refresh_token(user_id=99)
        payload = verify_token(token, token_type="refresh")
        assert payload["sub"] == "99"
        assert payload["type"] == "refresh"
        # refresh tokens include a jti
        assert "jti" in payload

    def test_verify_wrong_token_type_raises(self) -> None:
        token = create_access_token(user_id=1)
        with pytest.raises(JWTError, match="Invalid token type"):
            verify_token(token, token_type="refresh")

    def test_verify_garbage_token_raises(self) -> None:
        with pytest.raises(JWTError):
            verify_token("not.a.real.token", token_type="access")

    def test_access_token_contains_expected_fields(self) -> None:
        token = create_access_token(user_id=7)
        payload = verify_token(token, token_type="access")
        assert "sub" in payload
        assert "exp" in payload
        assert "iat" in payload
        assert "type" in payload


# ---------------------------------------------------------------------------
# AES-256-GCM encryption
# ---------------------------------------------------------------------------


class TestEncryption:
    """Token encryption / decryption (AES-256-GCM)."""

    def test_encrypt_decrypt_round_trip(self) -> None:
        original = "ghp_someFakeGitHubPAT1234567890"
        encrypted = encrypt_token(original)
        decrypted = decrypt_token(encrypted)
        assert decrypted == original

    def test_encrypted_differs_from_plaintext(self) -> None:
        plaintext = "secret-token"
        encrypted = encrypt_token(plaintext)
        assert encrypted != plaintext

    def test_each_encryption_is_unique(self) -> None:
        """Different nonces should produce different ciphertexts."""
        plaintext = "same-token"
        e1 = encrypt_token(plaintext)
        e2 = encrypt_token(plaintext)
        assert e1 != e2

    def test_decrypt_wrong_ciphertext_raises(self) -> None:
        """Tampered ciphertext should fail decryption."""
        import base64

        encrypted = encrypt_token("hello")
        raw = bytearray(base64.urlsafe_b64decode(encrypted))
        # Flip a byte in the ciphertext portion (after the 12-byte nonce)
        raw[15] ^= 0xFF
        tampered = base64.urlsafe_b64encode(bytes(raw)).decode("ascii")
        with pytest.raises(Exception):
            decrypt_token(tampered)
