# FastMCP 2.0 リソース機能の実装方法

## 概要

本ドキュメントでは、FastMCP 2.0におけるリソース機能の正しい実装方法について記述する。MCPサーバー開発時に発生したモジュールインポートエラーの原因と解決方法を含む。

## 発生した問題

MCPサーバー（claude-code-exterminal-memory）が起動できなくなる事象が発生した。具体的には、以下のインポート文が原因でモジュールエラーが発生していた。

```python
import mcp.types as types
```

エラーメッセージ:
```
ModuleNotFoundError: No module named 'mcp.types'
```

## 原因

FastMCP 2.0では、`mcp.types`モジュールは存在しない。リソース機能の実装方法がFastMCP 2.0で変更されており、以下の旧実装パターンは不要である：

- `@mcp.list_resources()`デコレータによる手動リソースリスト管理
- `@mcp.read_resource()`デコレータによる手動リソース読み取り処理
- `mcp.types.Resource`クラスのインポート

## 解決方法

### 誤った実装（動作しない）

```python
import mcp.types as types

@mcp.list_resources()
async def list_resources() -> list[types.Resource]:
    return [
        types.Resource(
            uri="docs://workflow",
            name="議論管理ワークフロー",
            mimeType="text/markdown",
            description="MCPツールを使った議論管理の典型的なフロー"
        )
    ]

@mcp.read_resource()
async def read_resource(uri: str) -> str:
    if uri == "docs://workflow":
        return "..."
    return ""
```

### 正しい実装（FastMCP 2.0）

```python
from fastmcp import FastMCP

mcp = FastMCP("server-name")

@mcp.resource("docs://workflow")
def workflow_docs() -> str:
    """MCPツールを使った議論管理の典型的なフロー"""
    return """# 議論管理ワークフロー

## 内容
...
"""
```

## 実装パターン

### 基本的な文字列リソース

```python
@mcp.resource("resource://greeting")
def get_greeting() -> str:
    """シンプルなグリーティングメッセージを提供する"""
    return "Hello from FastMCP Resources!"
```

### JSON形式のリソース

辞書を返すと自動的にJSONにシリアライズされる。

```python
@mcp.resource("data://config")
def get_config() -> dict:
    """アプリケーション設定をJSON形式で提供する"""
    return {
        "theme": "dark",
        "version": "1.2.0",
        "features": ["tools", "resources"],
    }
```

### テンプレートリソース（パラメータ付き）

URIにパラメータを含めることができる。

```python
@mcp.resource("weather://{city}/current")
def get_weather(city: str) -> dict:
    """特定都市の気象情報を提供する"""
    return {
        "city": city.capitalize(),
        "temperature": 22,
        "condition": "Sunny"
    }
```

### メタデータ付きリソース

```python
@mcp.resource(
    uri="data://app-status",
    name="ApplicationStatus",
    description="アプリケーションの現在の状態を提供する",
    mime_type="application/json",
    tags={"monitoring", "status"},
    meta={"version": "2.1", "team": "infrastructure"}
)
def get_application_status() -> dict:
    """アプリケーションステータスを返す"""
    return {"status": "ok", "uptime": 12345}
```

## 重要なポイント

1. **自動登録**: `@mcp.resource()`デコレータを使用すると、リソースは自動的にリソースリストに登録される
2. **遅延評価**: リソースはクライアントからリクエストされた時点で初めて実行される
3. **型の自動変換**: 文字列、辞書、リストなどの戻り値は自動的に適切な形式に変換される
4. **メタデータの推論**: 関数名やドキュメント文字列から名前や説明が自動的に推論される

## 調査手法に関する学び

今回の問題調査において、以下の手法の有効性が確認された。

### 推奨: Context7を使用したドキュメント調査

Context7を使用することで、最新の公式ドキュメントから正確なコード例と実装パターンを取得できる。

```
1. resolve-library-id で "fastmcp" を検索
2. /gofastmcp.com/llmstxt を選択
3. "resources implementation decorator" をトピックに指定
4. 正確な実装例を取得
```

### 非推奨: WebSearchによる調査

WebSearchでは以下の問題が発生する可能性がある：
- 古いバージョンの情報が混在する
- 断片的な情報しか得られない
- 複数の情報源を横断的に確認する必要がある

## 参考情報

- FastMCP 公式ドキュメント: https://gofastmcp.com/
- FastMCP GitHub: https://github.com/jlowin/fastmcp
- Context7 ライブラリID: `/gofastmcp.com/llmstxt`

## 更新履歴

- 2025-12-11: 初版作成（FastMCP 2.0リソース実装エラーの調査結果）
