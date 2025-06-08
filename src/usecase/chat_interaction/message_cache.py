import time
from collections import OrderedDict
from typing import Optional
from ...domain.entity.message_entity import MessageEntity

class MessageCache:
    def __init__(self, max_size: int = 1000, ttl_seconds: float = 3600) -> None:
        """
        メッセージキャッシュの初期化
        
        Args:
            max_size: 最大キャッシュサイズ（デフォルト: 1000）
            ttl_seconds: TTL秒数（デフォルト: 3600秒 = 1時間）
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._store: OrderedDict[str, tuple[MessageEntity, float]] = OrderedDict()  # (message, timestamp)

    def get(self, uuid: str) -> Optional[MessageEntity]:
        """メッセージを取得（期限切れの場合はNoneを返す）"""
        entry = self._store.get(uuid)
        if entry is None:
            return None
        
        message, timestamp = entry
        current_time = time.time()
        
        # TTLチェック
        if current_time - timestamp > self.ttl_seconds:
            # 期限切れなので削除
            del self._store[uuid]
            return None
        
        # アクセス順序を更新（LRU）
        self._store.move_to_end(uuid)
        return message

    def set(self, message: MessageEntity) -> None:
        """メッセージを設定"""
        uuid_str = str(message.uuid)
        current_time = time.time()
        
        # 既存エントリがある場合は更新
        if uuid_str in self._store:
            self._store[uuid_str] = (message, current_time)
            self._store.move_to_end(uuid_str)
            return
        
        # サイズ制限チェック
        if len(self._store) >= self.max_size:
            # 最古のエントリを削除（LRU）
            self._store.popitem(last=False)
        
        # 新しいエントリを追加
        self._store[uuid_str] = (message, current_time)

    def exists(self, uuid: str) -> bool:
        """メッセージが存在するかチェック（期限切れは存在しない扱い）"""
        return self.get(uuid) is not None
    
    def cleanup_expired(self) -> int:
        """期限切れエントリをクリーンアップし、削除した数を返す"""
        current_time = time.time()
        expired_keys = []
        
        for uuid, (_, timestamp) in self._store.items():
            if current_time - timestamp > self.ttl_seconds:
                expired_keys.append(uuid)
        
        for key in expired_keys:
            del self._store[key]
        
        return len(expired_keys)
    
    def size(self) -> int:
        """現在のキャッシュサイズを返す"""
        return len(self._store)
    
    def clear(self) -> None:
        """キャッシュをクリア"""
        self._store.clear()