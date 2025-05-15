from pydantic import BaseModel, EmailStr
from typing import List, Optional

# リクエストモデル
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

# レスポンスモデル
class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    
    class Config:
        # ORMモードを有効にすると、ORM（SQLAlchemy）オブジェクトからの変換が容易になる
        orm_mode = True

# 一覧取得用レスポンスモデル
class UsersResponse(BaseModel):
    users: List[UserResponse]
    total: int