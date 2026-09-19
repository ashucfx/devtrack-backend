from datetime import timedelta

import pytest

from app.core.exceptions import UnauthorizedException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hashing_and_verification() -> None:
    raw_password = "SecurePassword123!"
    hashed = hash_password(raw_password)

    assert hashed != raw_password
    assert hashed.startswith("$argon2")
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_access_token_creation_and_decoding() -> None:
    user_id = "123e4567-e89b-12d3-a456-426614174000"
    token = create_access_token(subject=user_id, extra_claims={"role": "user"})

    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == user_id
    assert payload["type"] == "access"
    assert payload["role"] == "user"
    assert "exp" in payload
    assert "iat" in payload


def test_refresh_token_creation_and_decoding() -> None:
    user_id = "123e4567-e89b-12d3-a456-426614174000"
    token = create_refresh_token(subject=user_id)

    payload = decode_token(token, expected_type="refresh")
    assert payload["sub"] == user_id
    assert payload["type"] == "refresh"


def test_token_type_mismatch() -> None:
    user_id = "123e4567-e89b-12d3-a456-426614174000"
    token = create_access_token(subject=user_id)

    with pytest.raises(UnauthorizedException, match="Invalid token type"):
        decode_token(token, expected_type="refresh")


def test_expired_token() -> None:
    user_id = "123e4567-e89b-12d3-a456-426614174000"
    token = create_access_token(subject=user_id, expires_delta=timedelta(seconds=-10))

    with pytest.raises(UnauthorizedException, match="Token has expired"):
        decode_token(token)


def test_invalid_token_string() -> None:
    with pytest.raises(UnauthorizedException, match="Invalid token"):
        decode_token("not-a-valid-jwt-token")
