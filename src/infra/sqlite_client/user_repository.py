from uuid import UUID
from datetime import datetime
from peewee import SqliteDatabase, DoesNotExist
from typing import Optional, List

from ...port.user_repository import UserRepository
from ...port.dto.user_dto import CreateUserDTO, UserDTO
from ...domain.entity.user_entity import UserEntity
from .peewee_models import User as UserModel, db_proxy

class SqliteUserRepository(UserRepository):
    """
    Peewee/SQLite を用いた UserRepository の実装
    """
    def __init__(self, db_path: str = "./data/chat_app.db"):
        # データベースプロキシが既に初期化されていない場合のみ初期化
        if not db_proxy.obj:
            import os
            
            # データベースディレクトリが存在しない場合は作成
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            
            db = SqliteDatabase(db_path)
            db_proxy.initialize(db)
            db.connect()
            db.create_tables([UserModel])

    def exists_by_username(self, username: str) -> bool:
        return UserModel.select().where(UserModel.name == username).exists()

    def save(self, user_dto: CreateUserDTO) -> UserEntity:
        user = UserModel.create(
            name=user_dto.username,
            password=user_dto.raw_password,
            created_at=datetime.utcnow()
        )
        return UserEntity(
            id=user.id,
            uuid=UUID(user.uuid),
            username=user.name,
            password_hash=user.password,
            created_at=user.created_at
        )
    
    def get_user_by_name(self, username: str) -> Optional[UserDTO]:
        """ユーザー名でユーザーを取得"""
        try:
            user = UserModel.get(UserModel.name == username)
            return UserDTO(
                id=user.id,
                uuid=user.uuid,
                name=user.name,
                password=user.password
            )
        except DoesNotExist:
            return None
    
    def get_all_users(self) -> List[UserDTO]:
        """全ユーザーを取得"""
        users = UserModel.select()
        return [
            UserDTO(
                id=user.id,
                uuid=user.uuid,
                name=user.name,
                password=user.password
            )
            for user in users
        ]