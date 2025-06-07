from peewee import (
    DatabaseProxy,
    Model,
    CharField,
    IntegerField,
    ForeignKeyField,
    DateTimeField,
    BlobField,
    TextField,
    BooleanField
    )

from uuid import uuid4
import datetime

db_proxy = DatabaseProxy()

class User(Model):
    uuid = CharField(unique=True, default=lambda: str(uuid4()))
    name = CharField(unique=True)
    password = CharField()
    created_at = DateTimeField(default=datetime.datetime.now)

    def save(self, *args, **kwargs):
        # 新規作成時にパスワードをハッシュ化
        if self._pk is None:
            from src.infra.auth import get_password_hash
            self.password = get_password_hash(self.password)
        return super().save(*args, **kwargs)

    class Meta:
        database = db_proxy

class DiscussionStructure(Model):
    user = ForeignKeyField(User, backref='discussionstructure_set')
    uuid = CharField(unique=True)
    title = CharField(null=True)
    system_prompt = CharField(null=True)
    serialized_structure = BlobField()
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = db_proxy

class Message(Model):
    discussion = ForeignKeyField(DiscussionStructure, backref='message_set')
    uuid = CharField(unique=True)
    role = CharField()  # 'user', 'system', 'assistant' など
    content = CharField()
    created_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = db_proxy

class LLMDetails(Model):
    message = ForeignKeyField(Message, backref='llm_details', unique=True)
    model = CharField(null=True)
    provider = CharField(null=True)
    prompt_tokens = IntegerField(null=True)
    completion_tokens = IntegerField(null=True)
    total_tokens = IntegerField(null=True)

    class Meta:
        database = db_proxy


class AvailableModelCache(Model):
    """利用可能なモデルのキャッシュテーブル"""
    
    id = CharField(primary_key=True)  # OpenRouter model ID
    name = CharField()
    description = TextField(null=True)
    context_length = IntegerField(null=True)
    pricing_prompt = CharField(null=True)  # Store as string to preserve decimal precision
    pricing_completion = CharField(null=True)
    architecture_data = TextField(null=True)  # JSON string for architecture details
    created = IntegerField(null=True)  # Unix timestamp from OpenRouter
    last_updated = DateTimeField(default=datetime.datetime.now)
    is_active = BooleanField(default=True)
    
    class Meta:
        database = db_proxy
        table_name = 'available_models'


class PromptTemplate(Model):
    """プロンプトテンプレートを管理するテーブル"""
    
    user = ForeignKeyField(User, backref='templates')
    uuid = CharField(unique=True, default=lambda: str(uuid4()))
    name = CharField()
    description = TextField(null=True)
    template_content = TextField()
    category = CharField(null=True)
    variables = TextField(null=True)  # JSON string for template variables
    is_public = BooleanField(default=False)
    is_favorite = BooleanField(default=False)
    usage_count = IntegerField(default=0)
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(default=datetime.datetime.now)
    
    class Meta:
        database = db_proxy


class ConversationPreset(Model):
    """会話設定のプリセットを管理するテーブル"""
    
    user = ForeignKeyField(User, backref='presets')
    uuid = CharField(unique=True, default=lambda: str(uuid4()))
    name = CharField()
    description = TextField(null=True)
    model_id = CharField()
    temperature = CharField(default="0.7")  # Store as string to preserve precision
    max_tokens = IntegerField(default=1000)
    system_prompt = TextField(null=True)
    is_favorite = BooleanField(default=False)
    usage_count = IntegerField(default=0)
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(default=datetime.datetime.now)
    
    class Meta:
        database = db_proxy

