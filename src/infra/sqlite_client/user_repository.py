from uuid import UUID
from datetime import datetime
from peewee import SqliteDatabase

from ...port.user_repository import UserRepository
from ...port.dto.user_dto import CreateUserDTO
from ...domain.entity.user_entity import UserEntity
from .peewee_models import User as UserModel, db_proxy

class SqliteUserRepository(UserRepository):
    """
    Peewee/SQLite を用いた UserRepository の実装
    """
    def __init__(self, db_path: str = "data/sqlite.db"):
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