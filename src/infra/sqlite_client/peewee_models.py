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
    uuid = CharField(unique=True, default=lambda: str(uuid4()))
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

