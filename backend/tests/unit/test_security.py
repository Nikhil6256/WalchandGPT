"""Unit tests for authentication utilities."""
import pytest
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)


class TestPasswordHashing:
    def test_hash_is_not_plain_text(self):
        hashed = hash_password("mypassword")
        assert hashed != "mypassword"
        assert len(hashed) > 20

    def test_correct_password_verifies(self):
        hashed = hash_password("correct_password")
        assert verify_password("correct_password", hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_same_password_produces_different_hashes(self):
        """bcrypt salts each hash — same input should produce different outputs."""
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2  # Different salts


class TestJWT:
    def test_access_token_is_decodable(self):
        token = create_access_token(subject="user-123")
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"

    def test_refresh_token_type_is_refresh(self):
        token = create_refresh_token(subject="user-456")
        payload = decode_token(token)
        assert payload["type"] == "refresh"

    def test_extra_claims_are_included(self):
        token = create_access_token(subject="user-789", extra_claims={"role": "admin"})
        payload = decode_token(token)
        assert payload["role"] == "admin"

    def test_invalid_token_returns_none(self):
        result = decode_token("not.a.valid.jwt.token")
        assert result is None

    def test_tampered_token_returns_none(self):
        token = create_access_token("user-abc")
        tampered = token[:-5] + "XXXXX"
        assert decode_token(tampered) is None
