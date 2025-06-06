import os
from pathlib import Path
from peewee import SqliteDatabase
from dotenv import load_dotenv

from .peewee_models import User, Message, LLMDetails, DiscussionStructure, db_proxy
from ...infra.config import Settings

def initialize_database():
    """データベースの初期化を行う"""
    settings = Settings()
    
    # データベースファイルのディレクトリを作成
    db_path = Path(settings.database_url.replace("sqlite:///", ""))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # データベース接続
    db = SqliteDatabase(str(db_path))
    db_proxy.initialize(db)
    
    try:
        db.connect()
        # テーブルの作成（存在しない場合のみ）
        db.create_tables([User, Message, LLMDetails, DiscussionStructure], safe=True)
        print(f"Database initialized successfully at: {db_path}")
        return True
    except Exception as e:
        print(f"Database initialization failed: {e}")
        return False
    finally:
        if not db.is_closed():
            db.close()

def create_test_user_if_not_exists():
    """テスト環境でのみテストユーザーを作成"""
    load_dotenv()
    
    if os.environ.get("ENVIRONMENT") != "development":
        print("Skipping test user creation (not in development mode)")
        return
    
    test_user_pass = os.environ.get("TEST_USER_PASS")
    if not test_user_pass:
        print("TEST_USER_PASS not found in environment variables")
        return
    
    try:
        # 既存のテストユーザーをチェック
        existing_user = User.select().where(User.name == 'test_user').first()
        if existing_user:
            print("Test user already exists")
            return
        
        # テストユーザーを作成
        User.create(name='test_user', password=test_user_pass)
        print("Test user created successfully")
    except Exception as e:
        print(f"Failed to create test user: {e}")

if __name__ == "__main__":
    if initialize_database():
        create_test_user_if_not_exists()

# uv run -m src.infra.sqlite_client.sqlite_db_init