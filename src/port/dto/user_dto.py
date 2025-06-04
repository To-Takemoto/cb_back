from dataclasses import dataclass

@dataclass
class CreateUserDTO:
    """
    ユーザー登録用DTO
    """
    username: str
    raw_password: str

@dataclass
class UserDTO:
    """
    ユーザー情報DTO
    """
    id: int
    uuid: str
    name: str
    password: str