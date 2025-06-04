from typing import Protocol
from ..domain.entity.user_entity import UserEntity
from ..port.dto.user_dto import CreateUserDTO

class UserRepository(Protocol):
    """
    ユーザーデータの永続化インターフェース。
    """

    def exists_by_username(self, username: str) -> bool:
        ...

    def save(self, user_dto: CreateUserDTO) -> UserEntity:
        ...