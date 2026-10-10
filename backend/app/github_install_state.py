"""Short-lived, one-time state for connecting GitHub App installations."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import secrets

import jwt
from redis.asyncio import Redis

from app.core.config import settings

STATE_TTL_SECONDS = 900


async def create_install_state(workspace_id: int, redis: Redis) -> str:
    """Create signed state bound to a workspace and store its one-time nonce."""

    nonce = secrets.token_urlsafe(24)
    if not await redis.set(
        f"github-install-state:{nonce}",
        str(workspace_id),
        ex=STATE_TTL_SECONDS,
        nx=True,
    ):
        raise RuntimeError("Could not reserve GitHub installation state.")

    now = datetime.now(UTC)
    return jwt.encode(
        {
            "workspace_id": workspace_id,
            "nonce": nonce,
            "iat": now,
            "exp": now + timedelta(seconds=STATE_TTL_SECONDS),
        },
        settings.SECRET_KEY,
        algorithm="HS256",
        headers={"typ": "JWT"},
    )


async def consume_install_state(state: str, redis: Redis) -> int:
    """Validate and consume a workspace-bound state exactly once."""

    try:
        payload = jwt.decode(
            state,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            options={"require": ["exp", "iat", "workspace_id", "nonce"]},
        )
        workspace_id = int(payload["workspace_id"])
        nonce = str(payload["nonce"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise ValueError("Invalid or expired GitHub installation state.") from exc

    stored_workspace_id = await redis.getdel(f"github-install-state:{nonce}")
    if stored_workspace_id is None or int(stored_workspace_id) != workspace_id:
        raise ValueError("GitHub installation state was already used or expired.")
    return workspace_id
