class LLMMessage:
    """LLMに送信するメッセージを表すエンティティクラス"""
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content
    
    def to_dict(self) -> dict:
        """メッセージを辞書形式に変換"""
        return {
            "role": self.role,
            "content": self.content
        }