from ...entity.message_entity import MessageEntity

class MessageCache:
    def __init__(self) -> None:
        self._store: dict[str, MessageEntity] = {}

    def get(self, uuid: str) -> MessageEntity | None:
        return self._store.get(uuid)

    def set(self, message: MessageEntity) -> None:
        self._store[str(message.uuid)] = message

    def exists(self, uuid: str) -> bool:
        return uuid in self._store