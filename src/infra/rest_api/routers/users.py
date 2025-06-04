from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime

from ..dependencies import get_register_user_usecase
from ....port.dto.user_dto import CreateUserDTO
from ....domain.exception.user_exceptions import (
    UsernameAlreadyExistsException,
    InvalidPasswordException
)
from ....usecase.user_management.register_user import RegisterUserUseCase

router = APIRouter(
    prefix="/api/v1/users",
    tags=["users"]
)

class UserRegisterRequest(BaseModel):
    username: str
    password: str

class UserRegisterResponse(BaseModel):
    uuid: str
    username: str
    created_at: datetime

@router.post("", response_model=UserRegisterResponse)
def register_user(
    req: UserRegisterRequest,
    usecase: RegisterUserUseCase = Depends(get_register_user_usecase)
):
    """
    新規ユーザー登録
    """
    dto = CreateUserDTO(username=req.username, raw_password=req.password)
    try:
        user = usecase.execute(dto)
        return UserRegisterResponse(
            uuid=str(user.uuid),
            username=user.username,
            created_at=user.created_at
        )
    except UsernameAlreadyExistsException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InvalidPasswordException as e:
        raise HTTPException(status_code=400, detail=str(e))