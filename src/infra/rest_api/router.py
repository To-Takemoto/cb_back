from fastapi import APIRouter

router = APIRouter()

# ユーザーエンドポイント
@router.get("/users/", tags=["users"])
async def get_users():
    # ユースケース層を呼び出す
    return {"users": [{"id": 1, "name": "ユーザー1"}]}

@router.get("/users/{user_id}", tags=["users"])
async def get_user(user_id: int):
    # ユースケース層を呼び出す
    return {"id": user_id, "name": f"ユーザー{user_id}"}

@router.post("/users/", tags=["users"])
async def create_user(user: dict):
    # ユースケース層を呼び出す
    return {"id": 1, **user}

# 商品エンドポイント
@router.get("/items/", tags=["items"])
async def get_items():
    # ユースケース層を呼び出す
    return {"items": [{"id": 1, "name": "商品1"}]}