from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PATCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Token name")
    expires_in_days: int | None = Field(
        default=365,
        description="Expiration in days. Default is 365 days (1 year). Set None for no expiration.",
    )


class PATCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    raw_token: str = Field(..., description="Full token string. Only shown once!")
    token_prefix: str
    expired_at: datetime | None = None
    expires_at: datetime | None = None


class PATResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    token_prefix: str
    last_used_at: datetime | None = None
    expired_at: datetime | None = None
    expires_at: datetime | None = None
    is_revoked: bool
