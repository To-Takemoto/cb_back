from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from src.infra.auth import verify_password, create_access_token, get_current_user
from src.infra.di import get_user_repository
from src.infra.logging_config import get_logger
from src.port.user_repository import UserRepository
from src.infra.rest_api.rate_limiter import limiter

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
logger = get_logger("api.auth")


@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_repository: UserRepository = Depends(get_user_repository)
):
    # Get user from database
    user = await user_repository.get_user_by_name(form_data.username)
    
    if not user:
        logger.warning("Login attempt for non-existent user", extra={"username": form_data.username})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    if not verify_password(form_data.password, user.password):
        logger.warning("Login attempt with incorrect password", extra={"username": form_data.username})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.uuid}
    )
    
    logger.info("User logged in successfully", extra={"user_id": user.id, "username": user.name})
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/refresh")
@limiter.limit("10/hour")
async def refresh_token(
    request: Request,
    current_user_id: str = Depends(get_current_user)
):
    """
    トークンをリフレッシュする
    """
    # Create new access token
    access_token = create_access_token(
        data={"sub": current_user_id}
    )
    
    logger.info("Token refreshed", extra={"user_id": current_user_id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/me")
async def get_current_user_info(
    current_user_id: str = Depends(get_current_user),
    user_repository: UserRepository = Depends(get_user_repository)
):
    # Get user from database by UUID (効率的)
    user = await user_repository.get_user_by_uuid(current_user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "id": user.id,
        "uuid": user.uuid,
        "username": user.name
    }