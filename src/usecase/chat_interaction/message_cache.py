import time
import asyncio
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
        self._cleanup_task: Optional[asyncio.Task] = None
        self._started = False

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
    
    def start_auto_cleanup(self) -> None:
        """自動クリーンアップを開始"""
        if self._started:
            return
        
        self._started = True
        self._cleanup_task = asyncio.create_task(self._auto_cleanup_loop())
    
    async def stop_auto_cleanup(self) -> None:
        """自動クリーンアップを停止"""
        self._started = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
    
    async def _auto_cleanup_loop(self) -> None:
        """自動クリーンアップのループ処理"""
        try:
            while self._started:
                # 10分間隔でクリーンアップ実行
                await asyncio.sleep(600)  # 10分 = 600秒
                if self._started:  # 停止チェック
                    cleaned_count = self.cleanup_expired()
                    if cleaned_count > 0:
                        # ログはロガーを通じて記録すべき
                        pass  # TODO: logger.info(f"MessageCache: Cleaned {cleaned_count} expired entries")
        except asyncio.CancelledError:
            # 正常な停止処理
            pass
        except Exception as e:
            # エラーログはロガーを通じて記録すべき
            pass  # TODO: logger.error(f"MessageCache auto-cleanup error: {e}")
            # エラーが発生してもクリーンアップは継続
            if self._started:
                self._cleanup_task = asyncio.create_task(self._auto_cleanup_loop())