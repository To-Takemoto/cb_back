# デプロイ前セキュリティチェックリスト

## 🔴 クリティカル（必須対応）

### 1. 環境変数とシークレット管理
- [x] `.env`ファイルが`.gitignore`に含まれている
- [x] Git履歴に秘密情報が含まれていない
- [ ] 本番環境用の環境変数管理システムの設定（AWS Secrets Manager、Vault等）
- [ ] すべてのAPIキーとシークレットの再生成
- [ ] `SECRET_KEY`は十分に強力（32文字以上のランダム文字列）

### 2. HTTPS設定
- [ ] SSL/TLS証明書の設定
- [ ] HTTPからHTTPSへの自動リダイレクト
- [ ] HSTSヘッダーの有効化

### 3. 認証・認可
- [x] JWT実装の確認
- [x] パスワードハッシュ化（bcrypt）
- [x] タイミング攻撃対策
- [ ] リフレッシュトークンの実装検討
- [ ] セッション管理の強化

## 🟡 重要（強く推奨）

### 4. セキュリティヘッダー
実装済みのヘッダー（`security_config.py`）：
- [x] X-Content-Type-Options: nosniff
- [x] X-Frame-Options: DENY
- [x] X-XSS-Protection: 1; mode=block
- [x] Strict-Transport-Security
- [x] Referrer-Policy
- [x] Permissions-Policy
- [x] Content-Security-Policy

### 5. CORS設定
- [ ] 本番環境のドメインのみ許可
- [ ] 不要なメソッド・ヘッダーの制限
- [ ] 資格情報の適切な管理

### 6. レート制限
現在の設定：
- ログイン: 5回/分
- API: 20回/分
- 登録: 3回/分

- [ ] Redis等を使用した分散環境対応
- [ ] IPベースの制限追加

### 7. ログとモニタリング
- [x] セキュリティイベントのログ記録
- [x] センシティブ情報のマスキング
- [ ] 異常検知アラートの設定
- [ ] ログの外部保存（改ざん防止）

## 🟢 推奨事項

### 8. 入力検証
- [x] Pydanticによる包括的なバリデーション
- [x] SQLインジェクション対策（ORM使用）
- [ ] XSS対策の追加検証
- [ ] ファイルアップロード時の検証

### 9. エラーハンドリング
- [x] 詳細なエラー情報の隠蔽
- [x] 適切なHTTPステータスコード
- [ ] 本番環境でのスタックトレース無効化

### 10. データ保護
- [ ] データベース接続の暗号化
- [ ] バックアップの暗号化
- [ ] PII（個人識別情報）の適切な管理

### 11. 依存関係管理
- [x] 定期的な脆弱性スキャン
- [ ] 自動セキュリティアップデート
- [ ] ライセンスコンプライアンス確認

### 12. インフラセキュリティ
- [ ] ファイアウォール設定
- [ ] 不要なポートの閉鎖
- [ ] DDoS対策
- [ ] WAF（Web Application Firewall）の導入

## 📋 デプロイ前の最終確認

### 環境設定
```bash
# 本番環境の環境変数例
ENVIRONMENT=production
SECRET_KEY=<32文字以上のランダム文字列>
OPENROUTER_API_KEY=<本番用APIキー>
DATABASE_URL=<暗号化された接続文字列>
CORS_ORIGINS=https://yourdomain.com
LOG_LEVEL=INFO
DEBUG=False
```

### セキュリティミドルウェアの有効化
```python
# main.pyに追加
from src.infra.security_config import SecuritySettings, get_security_middleware_config
from src.infra.rest_api.security_middleware import setup_security_middleware

security_settings = SecuritySettings()
security_config = get_security_middleware_config(security_settings)

if settings.environment == "production":
    setup_security_middleware(
        app,
        security_headers=security_config["headers"],
        force_https=security_settings.force_https,
        trusted_hosts=["yourdomain.com", "www.yourdomain.com"],
        log_security_events=security_settings.log_security_events
    )
```

### 監査ログの設定
- APIアクセスログ
- 認証試行ログ
- エラーログ
- セキュリティイベントログ

## 🚨 緊急時対応計画

### インシデント対応
1. セキュリティ侵害検知時の連絡先
2. ログの保全手順
3. サービス停止・復旧手順
4. 顧客への通知プロセス

### バックアップとリカバリ
1. 定期的なバックアップ（暗号化）
2. リストア手順のテスト
3. 災害復旧計画

## 追加リソース

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
- [Python Security Guidelines](https://python.readthedocs.io/en/latest/library/security_warnings.html)