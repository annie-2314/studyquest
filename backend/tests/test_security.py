import pytest
from jose import JWTError

from app.core import security


def test_password_hash_roundtrip():
    h = security.hash_password("secret123")
    assert h != "secret123"
    assert security.verify_password("secret123", h) is True
    assert security.verify_password("wrong", h) is False


def test_access_token_roundtrip():
    token = security.create_access_token("user-id-1")
    payload = security.decode_token(token)
    assert payload["sub"] == "user-id-1"
    assert payload["type"] == "access"


def test_decode_invalid_token_raises():
    with pytest.raises(JWTError):
        security.decode_token("not.a.jwt")


def test_refresh_token_hash_is_deterministic():
    raw, h = security.generate_refresh_token()
    assert security.hash_refresh_token(raw) == h
