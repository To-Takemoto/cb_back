from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from .schemas import UserCreate, UserResponse, UsersResponse
from .dependencies import get_db, get_current_user

router = APIRouter()

# ユーザー作成エンドポイント - リクエストとレスポンスにスキーマを使用
@router.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate,  # リクエストボディをUserCreateスキーマで検証
    db = Depends(get_db)
):
    # ユースケース層を呼び出す例
    # new_user = user_usecase.create_user(db, user)
    
    # 仮の実装
    new_user = {
        "id": 1,
        "name": user.name,
        "email": user.email
    }
    
    # レスポンスはUserResponseスキーマに自動的に変換される
    return new_user

# ユーザー一覧取得エンドポイント - レスポンスに一覧用スキーマを使用
@router.get("/users/", response_model=UsersResponse)
async def get_users(
    skip: int = 0, 
    limit: int = 10,
    db = Depends(get_db)
):
    # ユースケース層を呼び出す例
    # users = user_usecase.get_users(db, skip=skip, limit=limit)
    # total = user_usecase.count_users(db)
    
    # 仮の実装
    users = [
        {"id": 1, "name": "ユーザー1", "email": "user1@example.com"},
        {"id": 2, "name": "ユーザー2", "email": "user2@example.com"},
    ]
    total = len(users)
    
    # レスポンスはUsersResponseスキーマに自動的に変換される
    return {"users": users, "total": total}

# 特定ユーザー取得エンドポイント - レスポンスにスキーマを使用
@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db = Depends(get_db)
):
    # ユースケース層を呼び出す例
    # user = user_usecase.get_user(db, user_id)
    
    # 仮の実装
    user = {"id": user_id, "name": f"ユーザー{user_id}", "email": f"user{user_id}@example.com"}
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ユーザーID {user_id} は見つかりませんでした"
        )
    
    # レスポンスはUserResponseスキーマに自動的に変換される
    return user

# ユーザー更新エンドポイント - リクエストとレスポンスにスキーマを使用
@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserCreate,  # 更新データもUserCreateスキーマで検証
    db = Depends(get_db),
    current_user = Depends(get_current_user)  # 認証も利用
):
    # ユースケース層を呼び出す例
    # updated_user = user_usecase.update_user(db, user_id, user_update)
    
    # 仮の実装
    updated_user = {
        "id": user_id,
        "name": user_update.name,
        "email": user_update.email
    }
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ユーザーID {user_id} は見つかりませんでした"
        )
    
    # レスポンスはUserResponseスキーマに自動的に変換される
    return updated_user