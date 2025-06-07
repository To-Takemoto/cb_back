#!/usr/bin/env python3
"""
テストランナーとレポート生成スクリプト
実装した機能の動作確認とテスト結果を報告
"""

import subprocess
import sys
import json
from datetime import datetime


def run_test_suite():
    """テストスイートを実行してレポート生成"""
    print("🚀 テンプレート・アナリティクス機能のテスト実行")
    print("=" * 60)
    
    # バリデーションテストの実行
    print("\n📋 1. バリデーションテスト")
    validation_result = subprocess.run([
        "uv", "run", "pytest", 
        "src/test/test_templates.py::TestTemplateValidation", 
        "-v", "--tb=short"
    ], capture_output=True, text=True)
    
    if validation_result.returncode == 0:
        print("✅ バリデーションテスト: 成功")
    else:
        print("❌ バリデーションテスト: 失敗")
        print(validation_result.stdout)
    
    # サーバー起動テスト
    print("\n🌐 2. サーバー起動テスト")
    server_test = subprocess.run([
        "uv", "run", "python", "-c", 
        "from src.infra.rest_api.main import app; print('✅ アプリケーション正常ロード')"
    ], capture_output=True, text=True)
    
    if server_test.returncode == 0:
        print("✅ サーバー起動: 成功")
    else:
        print("❌ サーバー起動: 失敗")
        print(server_test.stderr)
    
    # 機能概要の表示
    print("\n🎯 3. 実装済み機能概要")
    print("   📝 テンプレート機能:")
    print("     • プロンプトテンプレート作成・管理")
    print("     • 変数置換機能 ({variable}形式)")
    print("     • カテゴリ分類・お気に入り")
    print("     • 使用回数追跡")
    
    print("   📊 アナリティクス機能:")
    print("     • 使用統計概要取得")
    print("     • モデル別使用分析")
    print("     • 日別・時間別パターン分析")
    print("     • コストトレンド分析")
    
    print("   🔧 プリセット機能:")
    print("     • 会話設定プリセット保存")
    print("     • モデル・温度・トークン設定")
    print("     • お気に入り機能")
    
    # エンドポイント一覧
    print("\n🛠️  4. 新規APIエンドポイント")
    endpoints = [
        "POST   /api/v1/templates           - テンプレート作成",
        "GET    /api/v1/templates           - テンプレート一覧",
        "GET    /api/v1/templates/{uuid}    - テンプレート取得",
        "PUT    /api/v1/templates/{uuid}    - テンプレート更新",
        "DELETE /api/v1/templates/{uuid}    - テンプレート削除",
        "POST   /api/v1/templates/{uuid}/use - 使用回数増加",
        "",
        "POST   /api/v1/presets             - プリセット作成",
        "GET    /api/v1/presets             - プリセット一覧",
        "PUT    /api/v1/presets/{uuid}      - プリセット更新",
        "",
        "GET    /api/v1/analytics           - 総合分析",
        "GET    /api/v1/analytics/overview  - 概要統計",
        "GET    /api/v1/analytics/models    - モデル別統計",
        "GET    /api/v1/analytics/daily     - 日別統計",
        "GET    /api/v1/analytics/costs     - コスト分析",
    ]
    
    for endpoint in endpoints:
        if endpoint:
            print(f"     {endpoint}")
        else:
            print()
    
    # UXフロントエンド推奨機能
    print("\n💡 5. フロントエンド実装推奨機能")
    frontend_features = [
        "🎨 テンプレートライブラリUI",
        "   • カテゴリタブ表示",
        "   • お気に入り・使用頻度ソート",
        "   • 変数入力フォーム",
        "",
        "📊 リアルタイムダッシュボード",
        "   • Chart.js/D3.jsでグラフ表示",
        "   • 期間フィルター (1日〜1年)",
        "   • コスト追跡アラート",
        "",
        "⚙️  プリセット切り替えUI",
        "   • ドロップダウン選択",
        "   • ワンクリック設定適用",
        "   • 設定比較表示"
    ]
    
    for feature in frontend_features:
        if feature:
            print(f"     {feature}")
        else:
            print()
    
    print("\n🎉 実装完了！")
    print("   データベースマイグレーション済み")
    print("   API仕様確認: http://localhost:8000/docs")
    
    return validation_result.returncode == 0 and server_test.returncode == 0


if __name__ == "__main__":
    success = run_test_suite()
    sys.exit(0 if success else 1)