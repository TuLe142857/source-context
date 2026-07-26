"""API routes for User management and PostgreSQL database testing."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.model.user import User
from app.schemas.user import UserCreate, UserResponse, UserTestDBResponse

router = APIRouter(prefix="/users", tags=["Users"])
DBSession = Annotated[AsyncSession, Depends(get_db)]


@router.get(
    "/test-db",
    response_model=UserTestDBResponse,
    summary="Test PostgreSQL database connectivity and user count",
)
async def test_db_connection(db: DBSession) -> UserTestDBResponse:
    """Executes a test query to verify PostgreSQL async connection.

    Args:
        db (AsyncSession): The async database session.

    Returns:
        UserTestDBResponse: Database connection status and user count.
    """
    try:
        # Test query 1: Execute simple SELECT 1
        result = await db.execute(select(1))
        val = result.scalar()

        if val != 1:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database query returned unexpected result",
            )

        # Test query 2: Count total users
        count_result = await db.execute(select(func.count(User.id)))
        user_count = count_result.scalar() or 0

        return UserTestDBResponse(
            status="healthy",
            database_connected=True,
            user_count=user_count,
            message="Successfully connected to PostgreSQL database via Async Engine!",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection test failed: {exc}",
        ) from exc


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user to test database insertion",
)
async def create_user(
    user_in: UserCreate,
    db: DBSession,
) -> UserResponse:
    """Creates a new user record in PostgreSQL.

    Args:
        user_in (UserCreate): The user creation payload.
        db (AsyncSession): The async database session.

    Returns:
        UserResponse: Created user object.
    """
    existing_user = await db.execute(
        select(User).where(
            (User.email == user_in.email) | (User.username == user_in.username)
        )
    )
    if existing_user.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists.",
        )

    user = User(
        email=user_in.email,
        username=user_in.username,
        full_name=user_in.full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.get(
    "/",
    response_model=list[UserResponse],
    summary="List all users from PostgreSQL",
)
async def list_users(
    db: DBSession,
    skip: int = 0,
    limit: int = 100,
) -> list[UserResponse]:
    """Retrieves a paginated list of users from PostgreSQL.

    Args:
        db (AsyncSession): The async database session.
        skip (int, optional): Number of records to skip. Defaults to 0.
        limit (int, optional): Maximum records to return. Defaults to 100.

    Returns:
        list[UserResponse]: List of user objects.
    """
    result = await db.execute(select(User).offset(skip).limit(limit))
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user details by ID",
)
async def get_user(
    user_id: int,
    db: DBSession,
) -> UserResponse:
    """Retrieves details of a specific user by ID.

    Args:
        user_id (int): The user ID.
        db (AsyncSession): The async database session.

    Returns:
        UserResponse: The requested user object.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found.",
        )
    return UserResponse.model_validate(user)
