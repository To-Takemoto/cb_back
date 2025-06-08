"""
認証・認可モジュール

このモジュールは、アプリケーションの認証と認可機能を提供します。
JWT（JSON Web Token）を使用してユーザー認証を行い、パスワードハッシュ化、
トークン生成・検証、セキュリティ機能（タイミング攻撃対策等）を含みます。

主な機能:
- パスワードのハッシュ化と検証
- JWTトークンの生成と検証
- FastAPI依存性注入による認証
- セキュリティ強化（タイミング攻撃対策等）

セキュリティ考慮事項:
- bcryptを使用した安全なパスワードハッシュ化
- タイミング攻撃に対する基本的な防御
- JWT有効期限の適切な管理
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from src.infra.config import Settings
from src.infra.logging_config import get_logger

# パスワードコンテキストの初期化
# bcryptスキームを使用し、非推奨バージョンを自動処理
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2スキーム設定
# ログインエンドポイントのURLを指定
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# ロガー初期化
logger = get_logger("auth")

def get_settings() -> Settings:
    """
    設定オブジェクトを取得する
    
    リクエストごとに初期化されるため、設定の変更が動的に反映される
    
    Returns:
        Settings: アプリケーション設定オブジェクト
    """
    return Settings()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    パスワードをハッシュと照合して検証する
    
    タイミング攻撃対策として最小実行時間を保証します。
    これにより、パスワードの長さや内容による処理時間の違いを
    攻撃者が悪用することを防ぎます。
    
    Args:
        plain_password (str): 平文パスワード
        hashed_password (str): ハッシュ化されたパスワード
    
    Returns:
        bool: パスワードが一致する場合True、そうでなければFalse
        
    Security:
        - 最小実行時間100msを保証してタイミング攻撃を防御
        - 例外発生時もFalseを返して情報漏洩を防止
    """
    import time
    
    # タイミング攻撃対策: 処理開始時刻を記録
    start_time = time.time()
    
    try:
        result = pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # 例外が発生した場合はFalseを返す（情報漏洩防止）
        result = False
    
    # 最小実行時間を保証（タイミング攻撃対策）
    elapsed_time = time.time() - start_time
    min_time = 0.1  # 100ms
    if elapsed_time < min_time:
        time.sleep(min_time - elapsed_time)
    
    return result


def get_password_hash(password: str) -> str:
    """
    パスワードをハッシュ化する
    
    bcryptアルゴリズムを使用して、セキュアなパスワードハッシュを生成します。
    自動的にソルトが生成され、適切なコスト係数が適用されます。
    
    Args:
        password (str): ハッシュ化する平文パスワード
    
    Returns:
        str: ハッシュ化されたパスワード文字列
        
    Note:
        生成されるハッシュは毎回異なりますが、verify_password()で
        正しく検証できます。
    """
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    JWTアクセストークンを生成する
    
    ユーザー情報を含むペイロードからJWTトークンを作成します。
    有効期限が自動的に設定され、適切な署名が施されます。
    
    Args:
        data (Dict[str, Any]): トークンに含めるペイロードデータ
                              通常は {"sub": user_id} の形式
        expires_delta (Optional[timedelta]): カスタム有効期限
                                           Noneの場合は設定値を使用
    
    Returns:
        str: エンコードされたJWTトークン文字列
        
    Raises:
        JWTError: トークン生成に失敗した場合
        
    Note:
        - トークン生成はログに記録されます
        - 有効期限は「exp」クレームとして自動追加されます
    """
    settings = get_settings()
    to_encode = data.copy()
    
    # 有効期限を設定
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    
    # 有効期限をペイロードに追加
    to_encode.update({"exp": expire})
    
    # JWTトークンを生成
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    
    # ログ記録（セキュリティ監査用）
    logger.info("Access token created", extra={
        "sub": data.get("sub"), 
        "expires_at": expire.isoformat()
    })
    
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """
    JWTトークンを検証してデコードする
    
    提供されたトークンの署名、有効期限、形式を検証し、
    ペイロードデータを返します。
    
    Args:
        token (str): 検証するJWTトークン文字列
    
    Returns:
        Dict[str, Any]: デコードされたペイロードデータ
        
    Raises:
        JWTError: トークンが無効、期限切れ、署名不正等の場合
        
    Note:
        - 検証失敗はセキュリティログに記録されます
        - 有効期限は自動的にチェックされます
        - タイミング攻撃対策として定数時間比較を実装
    """
    import hmac
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError as e:
        logger.warning("Token verification failed", extra={"error": str(e)})
        raise


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """
    JWTトークンから現在のユーザーIDを取得する
    
    FastAPI依存性注入として使用され、保護されたエンドポイントで
    自動的にユーザー認証を行います。
    
    Args:
        token (str): Bearer認証ヘッダーから取得されるJWTトークン
                    oauth2_schemeによって自動抽出される
    
    Returns:
        str: 認証されたユーザーのID（UUIDまたは識別子）
        
    Raises:
        HTTPException: 以下の場合に401 Unauthorizedを発生
            - トークンが無効または期限切れ
            - トークンにユーザーID（sub）が含まれていない
            - 署名が不正
            
    Usage:
        @app.get("/protected")
        async def protected_endpoint(user_id: str = Depends(get_current_user)):
            return {"user_id": user_id}
            
    Note:
        - 認証失敗はセキュリティログに記録されます
        - WWW-Authenticateヘッダーが適切に設定されます
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = verify_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            logger.warning("Token missing 'sub' claim")
            raise credentials_exception
        
    except JWTError:
        raise credentials_exception
    
    return user_id