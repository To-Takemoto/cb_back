from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from ..dependencies import get_current_user
from ..schemas import AnalyticsResponse, AnalyticsParams
from ...tortoise_client.analytics_repository import TortoiseAnalyticsRepository as AnalyticsRepository

router = APIRouter()
analytics_repo = AnalyticsRepository()


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    params: AnalyticsParams = Depends(),
    current_user_id: str = Depends(get_current_user)
):
    """使用統計の総合分析データを取得"""
    try:
        # 各種統計データを並行取得
        overview = await analytics_repo.get_usage_overview(
            user_id=current_user_id,
            period=params.period,
            model_filter=params.model_filter
        )
        
        model_breakdown = await analytics_repo.get_model_breakdown(
            user_id=current_user_id,
            period=params.period
        )
        
        daily_usage = await analytics_repo.get_daily_usage(
            user_id=current_user_id,
            period=params.period
        )
        
        hourly_pattern = await analytics_repo.get_hourly_pattern(
            user_id=current_user_id,
            period=params.period
        )
        
        top_categories = await analytics_repo.get_top_categories(
            user_id=current_user_id,
            period=params.period
        )
        
        cost_trends = await analytics_repo.get_cost_trends(
            user_id=current_user_id,
            period=params.period
        )
        
        return AnalyticsResponse(
            overview={
                "total_messages": overview["total_messages"],
                "total_tokens": overview["total_tokens"],
                "total_cost": overview["total_cost"],
                "period_start": overview["period_start"],
                "period_end": overview["period_end"]
            },
            model_breakdown=model_breakdown,
            daily_usage=daily_usage,
            hourly_pattern=hourly_pattern,
            top_categories=top_categories,
            cost_trends=cost_trends
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics retrieval failed: {str(e)}")


@router.get("/analytics/overview")
async def get_usage_overview(
    params: AnalyticsParams = Depends(),
    current_user_id: str = Depends(get_current_user)
):
    """使用統計の概要のみを取得"""
    try:
        overview = await analytics_repo.get_usage_overview(
            user_id=current_user_id,
            period=params.period,
            model_filter=params.model_filter
        )
        return overview
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Overview retrieval failed: {str(e)}")


@router.get("/analytics/models")
async def get_model_breakdown(
    params: AnalyticsParams = Depends(),
    current_user_id: str = Depends(get_current_user)
):
    """モデル別使用統計を取得"""
    try:
        model_stats = await analytics_repo.get_model_breakdown(
            user_id=current_user_id,
            period=params.period
        )
        return {"models": model_stats}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model breakdown retrieval failed: {str(e)}")


@router.get("/analytics/daily")
async def get_daily_usage(
    params: AnalyticsParams = Depends(),
    current_user_id: str = Depends(get_current_user)
):
    """日別使用統計を取得"""
    try:
        daily_stats = await analytics_repo.get_daily_usage(
            user_id=current_user_id,
            period=params.period
        )
        return {"daily_usage": daily_stats}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Daily usage retrieval failed: {str(e)}")


@router.get("/analytics/hourly")
async def get_hourly_pattern(
    params: AnalyticsParams = Depends(),
    current_user_id: str = Depends(get_current_user)
):
    """時間帯別使用パターンを取得"""
    try:
        hourly_stats = await analytics_repo.get_hourly_pattern(
            user_id=current_user_id,
            period=params.period
        )
        return {"hourly_pattern": hourly_stats}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hourly pattern retrieval failed: {str(e)}")


@router.get("/analytics/costs")
async def get_cost_analysis(
    params: AnalyticsParams = Depends(),
    current_user_id: str = Depends(get_current_user)
):
    """コスト分析を取得"""
    try:
        cost_trends = await analytics_repo.get_cost_trends(
            user_id=current_user_id,
            period=params.period
        )
        
        overview = await analytics_repo.get_usage_overview(
            user_id=current_user_id,
            period=params.period
        )
        
        return {
            "cost_trends": cost_trends,
            "total_cost": overview["total_cost"],
            "average_cost_per_message": round(
                overview["total_cost"] / max(overview["total_messages"], 1), 4
            ),
            "average_cost_per_token": round(
                overview["total_cost"] / max(overview["total_tokens"], 1), 6
            )
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cost analysis retrieval failed: {str(e)}")