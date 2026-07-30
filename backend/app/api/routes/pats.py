from fastapi import APIRouter

from app.core import (
    APIResponse,
    ErrorCode,
    ResponseSuccessSchema,
    build_error_docs,
)
from app.schemas.pat import PATCreateRequest, PATCreateResponse, PATResponse
from app.services.pat_service import PatServiceDep

router = APIRouter(prefix="/user/tokens", tags=["Personal Access Tokens (API Keys)"])


@router.post(
    "",
    response_model=ResponseSuccessSchema[PATCreateResponse],
    responses=build_error_docs(
        ErrorCode.UNAUTHORIZED,
        ErrorCode.BAD_REQUEST,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Create a new Personal Access Token (API Key)",
)
async def create_personal_access_token(
    payload: PATCreateRequest,
    pat_service: PatServiceDep,
) -> APIResponse:
    token_data = await pat_service.create_token(
        name=payload.name,
        expires_in_days=payload.expires_in_days,
    )
    return APIResponse.ok(data=token_data)


@router.get(
    "",
    response_model=ResponseSuccessSchema[list[PATResponse]],
    responses=build_error_docs(
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="List all Personal Access Tokens for current user",
)
async def list_personal_access_tokens(
    pat_service: PatServiceDep,
) -> APIResponse:
    tokens = await pat_service.get_user_tokens()
    return APIResponse.ok(data=tokens)


@router.delete(
    "/{token_id}",
    response_model=ResponseSuccessSchema[None],
    responses=build_error_docs(
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Revoke/Delete a Personal Access Token",
)
async def revoke_personal_access_token(
    token_id: int,
    pat_service: PatServiceDep,
) -> APIResponse:
    await pat_service.revoke_token(token_id=token_id)
    return APIResponse.ok(message="Personal Access Token revoked successfully")
