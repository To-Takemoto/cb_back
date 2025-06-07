from uuid import UUID
from datetime import datetime
from typing import Optional, List

from ...port.user_repository import UserRepository
from ...port.dto.user_dto import CreateUserDTO, UserDTO
from ...domain.entity.user_entity import UserEntity
from .models import User


class TortoiseUserRepository(UserRepository):
    """
    Tortoise ORM を用いた UserRepository の実装
    """

    async def exists_by_username(self, username: str) -> bool:
        return await User.filter(name=username).exists()

    async def save(self, user_dto: CreateUserDTO) -> UserEntity:
        # パスワードハッシュ化はここで行う（本来はauth層で行うべき）
        from ...infra.auth import get_password_hash
        hashed_password = get_password_hash(user_dto.raw_password)
        
        user = await User.create(
            name=user_dto.username,
            password=hashed_password,
            created_at=datetime.utcnow()
        )
        
        return UserEntity(
            id=user.id,
            uuid=UUID(user.uuid),
            username=user.name,
            password_hash=user.password,
            created_at=user.created_at
        )
    
    async def get_user_by_name(self, username: str) -> Optional[UserDTO]:
        """ユーザー名でユーザーを取得"""
        user = await User.filter(name=username).first()
        if not user:
            return None
            
        return UserDTO(
            id=user.id,
            uuid=user.uuid,
            name=user.name,
            password=user.password
        )
    
    async def get_all_users(self) -> List[UserDTO]:
        """全ユーザーを取得"""
        users = await User.all()
        return [
            UserDTO(
                id=user.id,
                uuid=user.uuid,
                name=user.name,
                password=user.password
            )
            for user in users
        ]