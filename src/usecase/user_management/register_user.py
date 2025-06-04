from uuid import uuid4
from datetime import datetime

from ...port.user_repository import UserRepository
from ...port.dto.user_dto import CreateUserDTO
from ...domain.entity.user_entity import UserEntity
from ...domain.exception.user_exceptions import (
    UsernameAlreadyExistsException,
    InvalidPasswordException,
)

class RegisterUserUseCase:
    """
    ユーザー登録のユースケース実装
    """
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def execute(self, user_dto: CreateUserDTO) -> UserEntity:
        if self.user_repository.exists_by_username(user_dto.username):
            raise UsernameAlreadyExistsException(
                f"Username '{user_dto.username}' is already taken"
            )

        if len(user_dto.raw_password) < 8:
            raise InvalidPasswordException("Password must be at least 8 characters long")

        new_user = UserEntity(
            id=None,
            uuid=uuid4(),
            username=user_dto.username,
            password_hash=None,
            created_at=datetime.utcnow(),
        )

        return self.user_repository.save(user_dto)