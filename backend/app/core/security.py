"""Security utilities for password hashing and JWT token management."""

from datetime import UTC, datetime, timedelta
import hashlib
import secrets
from typing import Any

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Hashes a plain text password using bcrypt.

    Args:
        password (str): Plain text password.

    Returns:
        str: Hashed password string.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain text password against a hashed password.

    Args:
        plain_password (str): Plain text password to check.
        hashed_password (str): Hashed password from database.

    Returns:
        bool: True if password matches, False otherwise.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def create_access_token(
    subject: str | int,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Generates a signed JWT access token with an expiration time.

    Args:
        subject (str | int): Subject identifier (e.g. user ID or email).
        expires_delta (timedelta | None, optional): Custom expiration duration. Defaults to None.
        extra_claims (dict[str, Any] | None, optional): Additional payload data. Defaults to None.

    Returns:
        str: Encoded JWT token string.
    """
    now = datetime.now(UTC)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if extra_claims:
        to_encode.update(extra_claims)

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decodes and validates a JWT access token.

    Args:
        token (str): JWT token string.

    Returns:
        dict[str, Any] | None: Decoded payload dictionary if valid, None otherwise.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except (jwt.PyJWTError, ValueError):
        return None


def generate_otp(length: int = 6) -> str:
    """Generates a random numeric OTP code.

    Args:
        length (int, optional): Number of digits. Defaults to 6.

    Returns:
        str: Zero-padded numeric OTP string.
    """
    return f"{secrets.randbelow(10**length):0{length}d}"


def hash_otp(otp: str) -> str:
    """Computes SHA-256 hash of an OTP code for storage/lookup.

    Args:
        otp (str): Raw OTP string.

    Returns:
        str: Hexadecimal SHA-256 digest string.
    """
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()
