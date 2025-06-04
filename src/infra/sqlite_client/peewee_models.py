from peewee import (
    DatabaseProxy,
    Model,
    CharField,
    IntegerField,
    ForeignKeyField,
    DateTimeField,
    BlobField
    )
import bcrypt

from uuid import uuid4
import datetime

db_proxy = DatabaseProxy()

class User(Model):
    name = CharField(unique=True)
    password = CharField()
    created_at = DateTimeField(default=datetime.datetime.now)

    def save(self, *args, **kwargs):
        if self._pk is None:  # 新規作成時のみハッシュ化
            self.password = bcrypt.hashpw(self.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        super().save(*args, **kwargs)

    class Meta:
        database = db_proxy

class DiscussionStructure(Model):
    owner = ForeignKeyField(User, backref='discussions')
    uuid = CharField()
    structure = BlobField()
    created_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = db_proxy

class Message(Model):
    discussion = ForeignKeyField(DiscussionStructure, backref='messages')
    owner = ForeignKeyField(User, backref='user_messages')
    uuid = CharField()
    role = CharField()  # 'user', 'system', 'assistant' など
    content = CharField()
    created_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = db_proxy

class LLMDetails(Model):
    message = ForeignKeyField(Message, backref='llm_details')
    gen_id = CharField() 
    provider = CharField()
    object_ = CharField()
    created = CharField()
    finish_reason = CharField()
    index_ = CharField()
    message_role = CharField()
    #message_refusal = CharField()
    prompt_tokens = IntegerField()
    completion_tokens = IntegerField()
    total_tokens = IntegerField()

    class Meta:
        database = db_proxy

class User(Model):
    uuid = CharField(unique=True, default=lambda: str(uuid4()))  # 新規追加: UUID
    name = CharField(unique=True)
    password = CharField()
    created_at = DateTimeField(default=datetime.datetime.now)

    def save(self, *args, **kwargs):
        # 新規作成時にパスワードをハッシュ化
        if self._pk is None:
            hashed = bcrypt.hashpw(self.password.encode('utf-8'), bcrypt.gensalt())
            self.password = hashed.decode('utf-8')
        return super().save(*args, **kwargs)

    class Meta:
        database = db_proxy