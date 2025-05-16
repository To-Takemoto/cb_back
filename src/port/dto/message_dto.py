from dataclasses import dataclass

from ...entity.message_entity import Role


@dataclass
class MessageDTO:
    role: Role
    content: str|None