from fastapi import Depends, HTTPException, status
from typing import Generator

# データベースセッションの依存関係
def get_db():
    db = None
    try:
        # ここで実際のデータベースセッションを取得
        db = "db_session"  # 例示用
        yield db
    finally:
        # セッションのクローズ処理
        pass

# 認証の依存関係
def get_current_user(db = Depends(get_db)):
    # 認証処理
    user = {"id": 1, "name": "認証済みユーザー"}
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証に失敗しました",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user