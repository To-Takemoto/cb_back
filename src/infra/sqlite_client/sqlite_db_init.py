from peewee import SqliteDatabase
from dotenv import load_dotenv

import os

from .peewee_models import User, Message, LLMDetails, DiscussionStructure, db_proxy

# データベース設定
db = SqliteDatabase("data/sqlite.db")
db_proxy.initialize(db)

# テーブルの作成
db.connect()
db.create_tables([User, Message, LLMDetails, DiscussionStructure])
        

load_dotenv()
test_user_pass = os.environ.get("TEST_USER_PASS")
User.create(name='test_user', password=test_user_pass)


db.close()

print("Database initialize success!")

# uv run -m src.infra.sqlite_client.sqlite_db_init