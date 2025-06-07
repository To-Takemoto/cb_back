"""
Tortoise ORM configuration
"""

TORTOISE_ORM = {
    "connections": {
        "default": "sqlite://data/chat_app_tortoise.db"
    },
    "apps": {
        "models": {
            "models": ["src.infra.tortoise_client.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}