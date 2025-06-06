"""
ユーザー関連の例外クラス

このモジュールは、ユーザー管理に関する様々な例外を定義します。
認証、登録、データ取得等のユーザー操作で発生する例外を統一的に管理します。
"""

class UserNotFoundError(Exception):
    """指定されたユーザーが見つからない場合の例外"""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

class UsernameAlreadyExistsException(Exception):
    """指定のユーザー名は既に存在しています。"""
    pass

class InvalidPasswordException(Exception):
    """パスワードの形式が不正です。"""
    pass