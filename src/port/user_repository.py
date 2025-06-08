from typing import Protocol, Optional, List
from ..domain.entity.user_entity import UserEntity
from ..port.dto.user_dto import CreateUserDTO, UserDTO

class UserRepository(Protocol):
    """
    ユーザーデータの永続化インターフェース。
    """

    async def exists_by_username(self, username: str) -> bool:
        ...

    async def save(self, user_dto: CreateUserDTO) -> UserEntity:
        ...
    
    async def get_user_by_name(self, username: str) -> Optional[UserDTO]:
        ...
    
    async def get_user_by_uuid(self, uuid: str) -> Optional[UserDTO]:
        ...
    
    async def get_all_users(self) -> List[UserDTO]:
        ...