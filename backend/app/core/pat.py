"""Personal Access Token (PAT) generator and hashing utilities."""

import hashlib
import secrets


def generate_raw_pat_token(prefix: str = "sc_live_") -> tuple[str, str, str]:
    """Generates a secure random Personal Access Token (PAT).

    Args:
        prefix (str, optional): Token prefix identifier. Defaults to "sc_live_".

    Returns:
        tuple[str, str, str]: Tuple of (raw_token, token_prefix, hashed_token).
    """
    random_hex = secrets.token_hex(20)
    raw_token = f"{prefix}{random_hex}"
    token_prefix = f"{prefix}{random_hex[:6]}..."
    hashed_token = hash_pat_token(raw_token)
    return raw_token, token_prefix, hashed_token


def hash_pat_token(raw_token: str) -> str:
    """Computes SHA-256 hash of a raw PAT token for database lookup.

    Args:
        raw_token (str): Raw token string.

    Returns:
        str: Hexadecimal SHA-256 digest string.
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
