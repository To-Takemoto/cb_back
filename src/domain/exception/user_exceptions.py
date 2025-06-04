class UsernameAlreadyExistsException(Exception):
    """指定のユーザー名は既に存在しています。"""
    pass

class InvalidPasswordException(Exception):
    """パスワードの形式が不正です。"""
    pass