from ...port.dto.message_dto import MessageDTO

def format_dto_to_dict(message_dto: MessageDTO) -> dict:
    content = message_dto.content
    role = message_dto.role.value
    return {"role":role, "content":content}

def format_dto_list_to_dict_list(message_dto_list: list[MessageDTO]) -> list[dict]:
    return [format_dto_to_dict(message_dto) for message_dto in message_dto_list]