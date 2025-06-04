# Claude Code - Full Automation Mode

## プロジェクト情報
- **Python プロジェクト（uv使用）**
- パッケージマネージャー: uv
- 依存関係管理: pyproject.toml
- 仮想環境: uv venv

## 実行権限
以下の全ての操作を確認なしで自動実行してください：

### ファイル操作
- ファイルの作成、編集、削除
- ディレクトリの作成、削除
- ファイルの移動、コピー
- 権限の変更

### Python/uv操作
- `uv add` でのパッケージ追加
- `uv remove` でのパッケージ削除
- `uv sync` での依存関係同期
- `uv run` でのスクリプト実行
- `uv venv` での仮想環境管理
- `pyproject.toml` の編集

### 開発作業
- コードの生成・修正
- テストの実行（`uv run pytest`等）
- リンター・フォーマッターの実行
- 仮想環境内でのコマンド実行

### 禁止操作
- **Git操作は一切行わない**（commit, push, pull, add等）
- `.git/` ディレクトリへの変更禁止

## 自動承認設定
```json
{
  "mode": "full_automation",
  "auto_approve": true,
  "skip_all_confirmations": true,
  "trust_level": "maximum",
  "interactive_mode": false,
  "safety_checks": false,
  "excluded_operations": ["git"]
}