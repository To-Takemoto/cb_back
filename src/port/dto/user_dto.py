from dataclasses import dataclass

@dataclass
class CreateUserDTO:
    """
    ユーザー登録用DTO
    """
    username: str
    raw_password: str