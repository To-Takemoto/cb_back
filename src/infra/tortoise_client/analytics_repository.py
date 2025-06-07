"""
Tortoise ORM analytics repository
"""
from typing import List, Tuple, Optional, Dict, Any
import datetime
from tortoise.functions import Count, Sum
from tortoise.exceptions import DoesNotExist

from .models import Message, LLMDetails, DiscussionStructure, AvailableModelCache, User


class TortoiseAnalyticsRepository:
    """使用統計分析のTortoise ORMリポジトリ"""
    
    def _parse_period(self, period: str) -> Tuple[datetime.datetime, datetime.datetime]:
        """期間文字列を開始日時と終了日時に変換"""
        now = datetime.datetime.utcnow()
        
        if period == "1d":
            start = now - datetime.timedelta(days=1)
        elif period == "7d":
            start = now - datetime.timedelta(days=7)
        elif period == "30d":
            start = now - datetime.timedelta(days=30)
        elif period == "90d":
            start = now - datetime.timedelta(days=90)
        elif period == "1y":
            start = now - datetime.timedelta(days=365)
        else:
            start = now - datetime.timedelta(days=7)  # デフォルト
        
        return start, now
    
    async def get_usage_overview(
        self, 
        user_id: str, 
        period: str = "7d",
        model_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """使用統計の概要を取得"""
        start_date, end_date = self._parse_period(period)
        
        user = await User.get(uuid=user_id)
        
        # ベースクエリ
        query = Message.filter(
            discussion__user=user,
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        
        if model_filter:
            query = query.filter(llm_details__model=model_filter)
        
        # 集計クエリを実行
        total_messages = await query.count()
        
        # LLMDetailsが存在するメッセージの統計
        llm_query = query.filter(llm_details__isnull=False)
        
        total_tokens = await llm_query.aggregate(
            total=Sum('llm_details__total_tokens')
        )
        prompt_tokens = await llm_query.aggregate(
            total=Sum('llm_details__prompt_tokens')
        )
        completion_tokens = await llm_query.aggregate(
            total=Sum('llm_details__completion_tokens')
        )
        
        # コスト計算
        total_cost = await self._calculate_cost(user_id, start_date, end_date, model_filter)
        
        return {
            "total_messages": total_messages,
            "total_tokens": total_tokens['total'] or 0,
            "prompt_tokens": prompt_tokens['total'] or 0,
            "completion_tokens": completion_tokens['total'] or 0,
            "total_cost": total_cost,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat()
        }
    
    async def get_model_breakdown(
        self, 
        user_id: str, 
        period: str = "7d"
    ) -> List[Dict[str, Any]]:
        """モデル別使用統計を取得"""
        start_date, end_date = self._parse_period(period)
        
        user = await User.get(uuid=user_id)
        
        # 全体のメッセージ数を取得
        total_messages = await Message.filter(
            discussion__user=user,
            created_at__gte=start_date,
            created_at__lte=end_date
        ).count()
        
        if total_messages == 0:
            total_messages = 1  # 0除算を防ぐ
        
        # モデル別の統計を取得
        model_stats = await Message.filter(
            discussion__user=user,
            created_at__gte=start_date,
            created_at__lte=end_date,
            llm_details__model__isnull=False
        ).values('llm_details__model').annotate(
            message_count=Count('id'),
            token_count=Sum('llm_details__total_tokens'),
            prompt_tokens=Sum('llm_details__prompt_tokens'),
            completion_tokens=Sum('llm_details__completion_tokens')
        ).order_by('-message_count')
        
        results = []
        for row in model_stats:
            model_id = row['llm_details__model']
            model_name = await self._get_model_name(model_id)
            cost = await self._calculate_model_cost(
                model_id, 
                row['prompt_tokens'] or 0, 
                row['completion_tokens'] or 0
            )
            
            results.append({
                "model_id": model_id,
                "model_name": model_name,
                "message_count": row['message_count'],
                "token_count": row['token_count'] or 0,
                "cost": cost,
                "percentage": round((row['message_count'] / total_messages) * 100, 2)
            })
        
        return results
    
    async def get_daily_usage(
        self, 
        user_id: str, 
        period: str = "7d"
    ) -> List[Dict[str, Any]]:
        """日別使用統計を取得"""
        start_date, end_date = self._parse_period(period)
        
        user = await User.get(uuid=user_id)
        
        # 各日の統計を初期化
        daily_stats = {}
        current_date = start_date.date()
        end_date_only = end_date.date()
        
        while current_date <= end_date_only:
            daily_stats[current_date.isoformat()] = {
                "date": current_date.isoformat(),
                "message_count": 0,
                "token_count": 0,
                "cost": 0.0
            }
            current_date += datetime.timedelta(days=1)
        
        # 実際のデータを取得
        messages = await Message.filter(
            discussion__user=user,
            created_at__gte=start_date,
            created_at__lte=end_date
        ).prefetch_related('llm_details')
        
        for message in messages:
            date_key = message.created_at.date().isoformat()
            if date_key in daily_stats:
                daily_stats[date_key]["message_count"] += 1
                
                if hasattr(message, 'llm_details') and message.llm_details:
                    daily_stats[date_key]["token_count"] += message.llm_details.total_tokens or 0
                    
                    # コスト計算
                    if (message.llm_details.model and 
                        message.llm_details.prompt_tokens and 
                        message.llm_details.completion_tokens):
                        cost = await self._calculate_model_cost(
                            message.llm_details.model, 
                            message.llm_details.prompt_tokens, 
                            message.llm_details.completion_tokens
                        )
                        daily_stats[date_key]["cost"] += cost
        
        return list(daily_stats.values())
    
    async def get_hourly_pattern(
        self, 
        user_id: str, 
        period: str = "7d"
    ) -> List[Dict[str, Any]]:
        """時間帯別使用パターンを取得"""
        start_date, end_date = self._parse_period(period)
        
        user = await User.get(uuid=user_id)
        
        # 24時間分を初期化
        hourly_stats = []
        for hour in range(24):
            hourly_stats.append({
                "hour": hour,
                "message_count": 0,
                "token_count": 0
            })
        
        messages = await Message.filter(
            discussion__user=user,
            created_at__gte=start_date,
            created_at__lte=end_date
        ).prefetch_related('llm_details')
        
        for message in messages:
            hour = message.created_at.hour
            hourly_stats[hour]["message_count"] += 1
            
            if hasattr(message, 'llm_details') and message.llm_details:
                hourly_stats[hour]["token_count"] += message.llm_details.total_tokens or 0
        
        return hourly_stats
    
    async def get_top_categories(
        self, 
        user_id: str, 
        period: str = "7d", 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """人気カテゴリを取得（仮実装）"""
        # 将来的にテンプレートのカテゴリ使用統計などを実装
        return [
            {"category": "General", "usage_count": 50, "percentage": 45.5},
            {"category": "Programming", "usage_count": 30, "percentage": 27.3},
            {"category": "Writing", "usage_count": 20, "percentage": 18.2},
            {"category": "Analysis", "usage_count": 10, "percentage": 9.1}
        ]
    
    async def get_cost_trends(
        self, 
        user_id: str, 
        period: str = "30d"
    ) -> List[Dict[str, Any]]:
        """コストトレンドを取得"""
        # 日別使用統計からコストトレンドを生成
        daily_usage = await self.get_daily_usage(user_id, period)
        
        cost_trends = []
        cumulative_cost = 0.0
        
        for day in daily_usage:
            cumulative_cost += day["cost"]
            cost_trends.append({
                "date": day["date"],
                "daily_cost": day["cost"],
                "cumulative_cost": round(cumulative_cost, 4)
            })
        
        return cost_trends
    
    async def _get_model_name(self, model_id: str) -> str:
        """モデルIDからモデル名を取得"""
        try:
            model = await AvailableModelCache.get(id=model_id)
            return model.name
        except DoesNotExist:
            return model_id  # フォールバック
    
    async def _calculate_cost(
        self, 
        user_id: str, 
        start_date: datetime.datetime, 
        end_date: datetime.datetime,
        model_filter: Optional[str] = None
    ) -> float:
        """期間内の総コストを計算"""
        user = await User.get(uuid=user_id)
        
        query = Message.filter(
            discussion__user=user,
            created_at__gte=start_date,
            created_at__lte=end_date,
            llm_details__model__isnull=False,
            llm_details__prompt_tokens__isnull=False,
            llm_details__completion_tokens__isnull=False
        )
        
        if model_filter:
            query = query.filter(llm_details__model=model_filter)
        
        messages = await query.prefetch_related('llm_details')
        
        total_cost = 0.0
        for message in messages:
            if hasattr(message, 'llm_details') and message.llm_details:
                cost = await self._calculate_model_cost(
                    message.llm_details.model, 
                    message.llm_details.prompt_tokens, 
                    message.llm_details.completion_tokens
                )
                total_cost += cost
        
        return round(total_cost, 4)
    
    async def _calculate_model_cost(
        self, 
        model_id: str, 
        prompt_tokens: int, 
        completion_tokens: int
    ) -> float:
        """モデル別のコストを計算"""
        try:
            model = await AvailableModelCache.get(id=model_id)
            
            prompt_cost = 0.0
            completion_cost = 0.0
            
            if model.pricing_prompt:
                prompt_price_per_token = float(model.pricing_prompt)
                prompt_cost = (prompt_tokens / 1000000) * prompt_price_per_token
            
            if model.pricing_completion:
                completion_price_per_token = float(model.pricing_completion)
                completion_cost = (completion_tokens / 1000000) * completion_price_per_token
            
            return prompt_cost + completion_cost
        except (DoesNotExist, ValueError):
            # フォールバック: 仮の価格を使用
            return (prompt_tokens * 0.00001) + (completion_tokens * 0.00002)