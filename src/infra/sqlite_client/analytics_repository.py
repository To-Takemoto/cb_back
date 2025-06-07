from typing import List, Tuple, Optional, Dict, Any
import datetime
from peewee import fn, JOIN
from decimal import Decimal

from .peewee_models import Message, LLMDetails, DiscussionStructure, AvailableModelCache


class AnalyticsRepository:
    """使用統計分析のリポジトリ"""
    
    def _parse_period(self, period: str) -> Tuple[datetime.datetime, datetime.datetime]:
        """期間文字列を開始日時と終了日時に変換"""
        now = datetime.datetime.now()
        
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
        
        # ベースクエリ
        query = (Message
                .select(
                    fn.COUNT(Message.id).alias('total_messages'),
                    fn.SUM(LLMDetails.total_tokens).alias('total_tokens'),
                    fn.SUM(LLMDetails.prompt_tokens).alias('prompt_tokens'),
                    fn.SUM(LLMDetails.completion_tokens).alias('completion_tokens')
                )
                .join(DiscussionStructure)
                .join(LLMDetails, JOIN.LEFT_OUTER)
                .where(
                    (DiscussionStructure.user == user_id) &
                    (Message.created_at >= start_date) &
                    (Message.created_at <= end_date)
                ))
        
        if model_filter:
            query = query.where(LLMDetails.model == model_filter)
        
        result = query.first()
        
        # コスト計算（仮の実装、実際の価格データが必要）
        total_cost = await self._calculate_cost(user_id, start_date, end_date, model_filter)
        
        if result:
            return {
                "total_messages": result.total_messages or 0,
                "total_tokens": result.total_tokens or 0,
                "prompt_tokens": result.prompt_tokens or 0,
                "completion_tokens": result.completion_tokens or 0,
                "total_cost": total_cost,
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat()
            }
        else:
            return {
                "total_messages": 0,
                "total_tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_cost": 0.0,
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
        
        query = (Message
                .select(
                    LLMDetails.model,
                    fn.COUNT(Message.id).alias('message_count'),
                    fn.SUM(LLMDetails.total_tokens).alias('token_count'),
                    fn.SUM(LLMDetails.prompt_tokens).alias('prompt_tokens'),
                    fn.SUM(LLMDetails.completion_tokens).alias('completion_tokens')
                )
                .join(DiscussionStructure)
                .join(LLMDetails, JOIN.LEFT_OUTER)
                .where(
                    (DiscussionStructure.user == user_id) &
                    (Message.created_at >= start_date) &
                    (Message.created_at <= end_date) &
                    (LLMDetails.model.is_null(False))
                )
                .group_by(LLMDetails.model)
                .order_by(fn.COUNT(Message.id).desc()))
        
        results = []
        total_messages = 0
        
        # 全体のメッセージ数を先に計算
        total_query = (Message
                      .select(fn.COUNT(Message.id))
                      .join(DiscussionStructure)
                      .where(
                          (DiscussionStructure.user == user_id) &
                          (Message.created_at >= start_date) &
                          (Message.created_at <= end_date)
                      ))
        total_messages = total_query.scalar() or 1
        
        for row in query:
            model_name = await self._get_model_name(row.model)
            cost = await self._calculate_model_cost(row.model, row.prompt_tokens or 0, row.completion_tokens or 0)
            
            results.append({
                "model_id": row.model,
                "model_name": model_name,
                "message_count": row.message_count,
                "token_count": row.token_count or 0,
                "cost": cost,
                "percentage": round((row.message_count / total_messages) * 100, 2)
            })
        
        return results
    
    async def get_daily_usage(
        self, 
        user_id: str, 
        period: str = "7d"
    ) -> List[Dict[str, Any]]:
        """日別使用統計を取得"""
        start_date, end_date = self._parse_period(period)
        
        # SQLiteでは日付関数が限定的なので、Pythonで日付を生成
        daily_stats = {}
        current_date = start_date.date()
        end_date_only = end_date.date()
        
        # 各日の統計を初期化
        while current_date <= end_date_only:
            daily_stats[current_date.isoformat()] = {
                "date": current_date.isoformat(),
                "message_count": 0,
                "token_count": 0,
                "cost": 0.0
            }
            current_date += datetime.timedelta(days=1)
        
        # 実際のデータを取得
        query = (Message
                .select(
                    Message.created_at,
                    LLMDetails.total_tokens,
                    LLMDetails.prompt_tokens,
                    LLMDetails.completion_tokens,
                    LLMDetails.model
                )
                .join(DiscussionStructure)
                .join(LLMDetails, JOIN.LEFT_OUTER)
                .where(
                    (DiscussionStructure.user == user_id) &
                    (Message.created_at >= start_date) &
                    (Message.created_at <= end_date)
                ))
        
        for row in query:
            date_key = row.created_at.date().isoformat()
            if date_key in daily_stats:
                daily_stats[date_key]["message_count"] += 1
                daily_stats[date_key]["token_count"] += row.total_tokens or 0
                
                # コスト計算
                if row.model and row.prompt_tokens and row.completion_tokens:
                    cost = await self._calculate_model_cost(
                        row.model, 
                        row.prompt_tokens, 
                        row.completion_tokens
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
        
        # 24時間分を初期化
        hourly_stats = []
        for hour in range(24):
            hourly_stats.append({
                "hour": hour,
                "message_count": 0,
                "token_count": 0
            })
        
        query = (Message
                .select(
                    Message.created_at,
                    LLMDetails.total_tokens
                )
                .join(DiscussionStructure)
                .join(LLMDetails, JOIN.LEFT_OUTER)
                .where(
                    (DiscussionStructure.user == user_id) &
                    (Message.created_at >= start_date) &
                    (Message.created_at <= end_date)
                ))
        
        for row in query:
            hour = row.created_at.hour
            hourly_stats[hour]["message_count"] += 1
            hourly_stats[hour]["token_count"] += row.total_tokens or 0
        
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
            model = AvailableModelCache.get(AvailableModelCache.id == model_id)
            return model.name
        except:
            return model_id  # フォールバック
    
    async def _calculate_cost(
        self, 
        user_id: str, 
        start_date: datetime.datetime, 
        end_date: datetime.datetime,
        model_filter: Optional[str] = None
    ) -> float:
        """期間内の総コストを計算"""
        query = (Message
                .select(
                    LLMDetails.model,
                    LLMDetails.prompt_tokens,
                    LLMDetails.completion_tokens
                )
                .join(DiscussionStructure)
                .join(LLMDetails, JOIN.LEFT_OUTER)
                .where(
                    (DiscussionStructure.user == user_id) &
                    (Message.created_at >= start_date) &
                    (Message.created_at <= end_date) &
                    (LLMDetails.model.is_null(False)) &
                    (LLMDetails.prompt_tokens.is_null(False)) &
                    (LLMDetails.completion_tokens.is_null(False))
                ))
        
        if model_filter:
            query = query.where(LLMDetails.model == model_filter)
        
        total_cost = 0.0
        for row in query:
            cost = await self._calculate_model_cost(
                row.model, 
                row.prompt_tokens, 
                row.completion_tokens
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
            model = AvailableModelCache.get(AvailableModelCache.id == model_id)
            
            prompt_cost = 0.0
            completion_cost = 0.0
            
            if model.pricing_prompt:
                prompt_price_per_token = float(model.pricing_prompt)
                prompt_cost = (prompt_tokens / 1000000) * prompt_price_per_token
            
            if model.pricing_completion:
                completion_price_per_token = float(model.pricing_completion)
                completion_cost = (completion_tokens / 1000000) * completion_price_per_token
            
            return prompt_cost + completion_cost
        except:
            # フォールバック: 仮の価格を使用
            return (prompt_tokens * 0.00001) + (completion_tokens * 0.00002)