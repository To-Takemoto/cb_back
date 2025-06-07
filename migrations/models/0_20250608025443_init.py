from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "available_models" (
    "id" VARCHAR(255) NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "description" TEXT,
    "context_length" INT,
    "pricing_prompt" VARCHAR(50),
    "pricing_completion" VARCHAR(50),
    "architecture_data" TEXT,
    "created" INT,
    "last_updated" TIMESTAMP NOT NULL,
    "is_active" INT NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS "user" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "uuid" VARCHAR(255) NOT NULL UNIQUE,
    "name" VARCHAR(255) NOT NULL UNIQUE,
    "password" VARCHAR(255) NOT NULL,
    "created_at" TIMESTAMP NOT NULL
);
CREATE TABLE IF NOT EXISTS "conversationpreset" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "uuid" VARCHAR(255) NOT NULL UNIQUE,
    "name" VARCHAR(255) NOT NULL,
    "description" TEXT,
    "model_id" VARCHAR(255) NOT NULL,
    "temperature" VARCHAR(10) NOT NULL DEFAULT '0.7',
    "max_tokens" INT NOT NULL DEFAULT 1000,
    "system_prompt" TEXT,
    "is_favorite" INT NOT NULL DEFAULT 0,
    "usage_count" INT NOT NULL DEFAULT 0,
    "created_at" TIMESTAMP NOT NULL,
    "updated_at" TIMESTAMP NOT NULL,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "discussionstructure" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "uuid" VARCHAR(255) NOT NULL UNIQUE,
    "title" VARCHAR(255),
    "system_prompt" VARCHAR(1000),
    "serialized_structure" BLOB NOT NULL,
    "created_at" TIMESTAMP NOT NULL,
    "updated_at" TIMESTAMP NOT NULL,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "message" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "uuid" VARCHAR(255) NOT NULL UNIQUE,
    "role" VARCHAR(50) NOT NULL,
    "content" TEXT NOT NULL,
    "created_at" TIMESTAMP NOT NULL,
    "discussion_id" INT NOT NULL REFERENCES "discussionstructure" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "llmdetails" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "model" VARCHAR(255),
    "provider" VARCHAR(255),
    "prompt_tokens" INT,
    "completion_tokens" INT,
    "total_tokens" INT,
    "message_id" INT NOT NULL UNIQUE REFERENCES "message" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "prompttemplate" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "uuid" VARCHAR(255) NOT NULL UNIQUE,
    "name" VARCHAR(255) NOT NULL,
    "description" TEXT,
    "template_content" TEXT NOT NULL,
    "category" VARCHAR(255),
    "variables" TEXT,
    "is_public" INT NOT NULL DEFAULT 0,
    "is_favorite" INT NOT NULL DEFAULT 0,
    "usage_count" INT NOT NULL DEFAULT 0,
    "created_at" TIMESTAMP NOT NULL,
    "updated_at" TIMESTAMP NOT NULL,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSON NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
