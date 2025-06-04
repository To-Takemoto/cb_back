from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

@dataclass
class UserEntity:
    """
    ユーザーのビジネスドメインモデル
    """
    id: int | None
    uuid: UUID | None
    username: str
    password_hash: str | None
    created_at: datetime | None