from fastapi import APIRouter, BackgroundTasks

from app.api.dependencies import CurrentUser
from app.core import (
    APIResponse,
    ErrorCode,
    ResponseSuccessSchema,
    build_error_docs,
)
from app.schemas.auth import (
    CreateCustomTokenRequest,
    CustomTokenResponse,
    RegisterRequest,
    TokenResponse,
    UserLoginRequest,
    RegisterVerifyRequest,
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthServiceDep

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=ResponseSuccessSchema,
    responses=build_error_docs(
        (ErrorCode.RESOURCE_ALREADY_EXISTS, "Email already registered"),
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Register a new user (sends OTP verification email)",
)
async def register_user(
    payload: RegisterRequest, auth_service: AuthServiceDep, bg_task: BackgroundTasks
) -> APIResponse:
    await auth_service.register_user(payload, bg_task)
    return APIResponse.ok(
        message="OTP sent to your email. Please verify to complete registration."
    )


@router.post(
    "/register/verify-otp",
    response_model=ResponseSuccessSchema[TokenResponse],
    responses=build_error_docs(
        ErrorCode.INVALID_CODE,
        ErrorCode.CODE_EXPIRED,
        ErrorCode.BAD_REQUEST,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Verify OTP and create the user account",
)
async def verify_registration_otp(
    payload: RegisterVerifyRequest,
    auth_service: AuthServiceDep,
) -> APIResponse:
    result = await auth_service.verify_registration_otp(payload)
    return APIResponse.ok(data=result)


@router.post(
    "/login",
    response_model=ResponseSuccessSchema[TokenResponse],
    responses=build_error_docs(
        ErrorCode.INVALID_CREDENTIALS,
        ErrorCode.USER_INACTIVE,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Login user",
)
async def login_user(
    payload: UserLoginRequest,
    auth_service: AuthServiceDep,
) -> APIResponse:
    result = await auth_service.login_user(payload)
    return APIResponse.ok(data=result)


@router.get(
    "/me",
    response_model=ResponseSuccessSchema[UserResponse],
    responses=build_error_docs(
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Get profile of currently authenticated user",
)
async def get_me(
    current_user: CurrentUser,
    auth_service: AuthServiceDep,
) -> APIResponse:
    result = await auth_service.get_me(current_user)
    return APIResponse.ok(data=result)


@router.post(
    "/token",
    response_model=ResponseSuccessSchema[CustomTokenResponse],
    responses=build_error_docs(
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Create a custom token",
)
async def create_custom_token(
    payload: CreateCustomTokenRequest,
    current_user: CurrentUser,
    auth_service: AuthServiceDep,
) -> APIResponse:
    result = await auth_service.create_custom_token(current_user, payload)
    return APIResponse.ok(data=result)
