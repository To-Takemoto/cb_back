"""
Tortoise ORM models for the chat application
"""
from tortoise.models import Model
from tortoise import fields
from datetime import datetime
from uuid import uuid4


class User(Model):
    id = fields.IntField(pk=True)
    uuid = fields.CharField(max_length=255, unique=True, default=lambda: str(uuid4()))
    name = fields.CharField(max_length=255, unique=True)
    password = fields.CharField(max_length=255)
    created_at = fields.DatetimeField(default=datetime.utcnow)

    class Meta:
        table = "user"


class DiscussionStructure(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="discussion_structures")
    uuid = fields.CharField(max_length=255, unique=True)
    title = fields.CharField(max_length=255, null=True)
    system_prompt = fields.CharField(max_length=1000, null=True)
    serialized_structure = fields.BinaryField()
    created_at = fields.DatetimeField(default=datetime.utcnow)
    updated_at = fields.DatetimeField(default=datetime.utcnow)

    class Meta:
        table = "discussionstructure"


class Message(Model):
    id = fields.IntField(pk=True)
    discussion = fields.ForeignKeyField("models.DiscussionStructure", related_name="messages")
    uuid = fields.CharField(max_length=255, unique=True)
    role = fields.CharField(max_length=50)  # 'user', 'system', 'assistant'
    content = fields.TextField()
    created_at = fields.DatetimeField(default=datetime.utcnow)

    class Meta:
        table = "message"


class LLMDetails(Model):
    id = fields.IntField(pk=True)
    message = fields.OneToOneField("models.Message", related_name="llm_details")
    model = fields.CharField(max_length=255, null=True)
    provider = fields.CharField(max_length=255, null=True)
    prompt_tokens = fields.IntField(null=True)
    completion_tokens = fields.IntField(null=True)
    total_tokens = fields.IntField(null=True)

    class Meta:
        table = "llmdetails"


class AvailableModelCache(Model):
    id = fields.CharField(max_length=255, pk=True)  # OpenRouter model ID
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    context_length = fields.IntField(null=True)
    pricing_prompt = fields.CharField(max_length=50, null=True)
    pricing_completion = fields.CharField(max_length=50, null=True)
    architecture_data = fields.TextField(null=True)  # JSON string
    created = fields.IntField(null=True)  # Unix timestamp
    last_updated = fields.DatetimeField(default=datetime.utcnow)
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "available_models"


class PromptTemplate(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="templates")
    uuid = fields.CharField(max_length=255, unique=True, default=lambda: str(uuid4()))
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    template_content = fields.TextField()
    category = fields.CharField(max_length=255, null=True)
    variables = fields.TextField(null=True)  # JSON string
    is_public = fields.BooleanField(default=False)
    is_favorite = fields.BooleanField(default=False)
    usage_count = fields.IntField(default=0)
    created_at = fields.DatetimeField(default=datetime.utcnow)
    updated_at = fields.DatetimeField(default=datetime.utcnow)

    class Meta:
        table = "prompttemplate"


class ConversationPreset(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="presets")
    uuid = fields.CharField(max_length=255, unique=True, default=lambda: str(uuid4()))
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    model_id = fields.CharField(max_length=255)
    temperature = fields.CharField(max_length=10, default="0.7")
    max_tokens = fields.IntField(default=1000)
    system_prompt = fields.TextField(null=True)
    is_favorite = fields.BooleanField(default=False)
    usage_count = fields.IntField(default=0)
    created_at = fields.DatetimeField(default=datetime.utcnow)
    updated_at = fields.DatetimeField(default=datetime.utcnow)

    class Meta:
        table = "conversationpreset"