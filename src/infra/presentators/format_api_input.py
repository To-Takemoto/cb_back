from ...domain.entity.message_entity import MessageEntity

def format_entity_to_dict(message_entity: MessageEntity) -> dict:
    content = message_entity.content
    role = message_entity.role.value
    return {"role":role, "content":content}

def format_entity_list_to_dict_list(message_entity_list: list[MessageEntity]) -> list[dict]:
    return [format_entity_to_dict(message_entity) for message_entity in message_entity_list]