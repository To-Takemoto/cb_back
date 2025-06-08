"""メッセージキャッシュ制限のテスト"""
import pytest
import time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.usecase.chat_interaction.message_cache import MessageCache
from src.domain.entity.message_entity import MessageEntity, Role


class TestMessageCacheLimits:
    """メッセージキャッシュの制限機能をテスト"""
    
    def test_cache_should_have_max_size_limit(self):
        """キャッシュが最大サイズ制限を持つべき"""
        cache = MessageCache(max_size=3)
        
        # 最大サイズまで要素を追加
        for i in range(3):
            message = MessageEntity(
                id=i,
                uuid=f"test-uuid-{i}",
                role=Role.USER,
                content=f"test message {i}"
            )
            cache.set(message)
        
        # すべての要素が存在することを確認
        assert cache.exists("test-uuid-0")
        assert cache.exists("test-uuid-1")
        assert cache.exists("test-uuid-2")
        
        # 制限を超える要素を追加
        overflow_message = MessageEntity(
            id=3,
            uuid="test-uuid-3",
            role=Role.USER,
            content="overflow message"
        )
        cache.set(overflow_message)
        
        # 最古の要素が削除されることを確認（LRU）
        assert not cache.exists("test-uuid-0")
        assert cache.exists("test-uuid-1")
        assert cache.exists("test-uuid-2")
        assert cache.exists("test-uuid-3")
    
    def test_cache_should_have_ttl_functionality(self):
        """キャッシュがTTL機能を持つべき"""
        cache = MessageCache(ttl_seconds=1)
        
        message = MessageEntity(
            id=1,
            uuid="test-uuid",
            role=Role.USER,
            content="test message"
        )
        cache.set(message)
        
        # 即座に取得可能
        assert cache.exists("test-uuid")
        assert cache.get("test-uuid") is not None
        
        # TTL経過後は取得不可
        time.sleep(1.1)  # TTLより少し長く待機
        assert not cache.exists("test-uuid")
        assert cache.get("test-uuid") is None
    
    def test_cache_should_support_cleanup_method(self):
        """キャッシュが期限切れエントリのクリーンアップメソッドを持つべき"""
        cache = MessageCache(ttl_seconds=1)
        
        # クリーンアップメソッドが存在することを確認
        assert hasattr(cache, 'cleanup_expired'), "cleanup_expired method should exist"
        
        message = MessageEntity(
            id=1,
            uuid="test-uuid",
            role=Role.USER,
            content="test message"
        )
        cache.set(message)
        
        # TTL経過
        time.sleep(1.1)
        
        # 手動クリーンアップ前は物理的に存在
        assert "test-uuid" in cache._store
        
        # 手動クリーンアップ後は物理的に削除
        cache.cleanup_expired()
        assert "test-uuid" not in cache._store
    
    def test_cache_get_should_return_none_for_expired_entries(self):
        """期限切れエントリに対してgetはNoneを返すべき"""
        cache = MessageCache(ttl_seconds=0.5)
        
        message = MessageEntity(
            id=1,
            uuid="test-uuid",
            role=Role.USER,
            content="test message"
        )
        cache.set(message)
        
        # 即座に取得可能
        assert cache.get("test-uuid") is not None
        
        # TTL経過後はNone
        time.sleep(0.6)
        assert cache.get("test-uuid") is None
    
    def test_default_cache_should_have_reasonable_limits(self):
        """デフォルトキャッシュが適切な制限を持つべき"""
        cache = MessageCache()
        
        # デフォルト設定が適切であることを確認
        assert hasattr(cache, 'max_size'), "Default cache should have max_size"
        assert hasattr(cache, 'ttl_seconds'), "Default cache should have ttl_seconds"
        assert cache.max_size > 0, "Default max_size should be positive"
        assert cache.ttl_seconds > 0, "Default TTL should be positive"