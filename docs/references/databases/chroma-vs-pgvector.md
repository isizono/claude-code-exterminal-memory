---
tags: [vector-database, chroma, pgvector, embedding, research]
category: references/databases
created: 2025-12-10
updated: 2025-12-10
---

# ChromaDB vs pgvector 比較調査

## 概要

ベクトルデータベースとして、ChromaDBとpgvectorの2つの選択肢を調査した。

## 基本的な位置づけ

### ChromaDB
- 専用のベクトルデータベース（独立したシステム）
- オープンソース
- AI/LLMアプリケーション向けに最適化

### pgvector
- PostgreSQLの拡張機能
- 既存のPostgreSQLインスタンスに追加する形で利用
- SQLとベクトル検索を統合

## パフォーマンス比較

### クエリ速度
- **pgvector**: 平均応答時間 9.81秒、最速 3.59秒
- **ChromaDB**: 平均応答時間 23.08秒、最速 4.04秒

pgvectorが約2.4倍高速である。

### インデックス構築速度
- **pgvector**: インデックス構築に時間がかかる（特にHNSWのMパラメータが大きい場合）
- **ChromaDB**: インデックス構築が高速

### パフォーマンス安定性
- **pgvector**: QPS（クエリ毎秒）が安定している
- **ChromaDB**: パフォーマンスのばらつきがある可能性

## 使いやすさ

### ChromaDB
- シンプルなAPI
- セットアップが容易（数行のコードで開始可能）
- 初心者フレンドリー
- スキーマレスで柔軟

### pgvector
- PostgreSQLの知識が必要
- インストールと設定にデータベースの理解が求められる
- 初心者には難易度が高い

## 機能比較

### ChromaDB の主要機能

#### 1. マルチモーダル検索
- ベクトル検索
- 全文検索
- 正規表現検索
- メタデータフィルタリング

これらを組み合わせた複雑な検索が可能。

#### 2. 自動埋め込み機能（Automatic Embedding）

**概要:**
ドキュメントを追加するだけで、自動的にベクトル化を実行する機能。

**対応モデル:**
- OpenAI: `text-embedding-3-small`, `text-embedding-ada-002` など
- HuggingFace: `sentence-transformers/all-MiniLM-L6-v2` など
- Sentence Transformers: デフォルトで利用可能
- カスタムモデル: `EmbeddingFunction` クラスを継承して独自実装可能

**使用例（OpenAI）:**
```python
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

# 1. Embedding functionの設定
embedding_function = OpenAIEmbeddingFunction(
    api_key="YOUR_OPENAI_API_KEY",
    model_name="text-embedding-3-small"
)

# 2. コレクション作成時に指定
collection = chroma_client.create_collection(
    name='my_collection',
    embedding_function=embedding_function
)

# 3. ドキュメント追加で自動ベクトル化
collection.add(
    documents=["これはテストドキュメントです"],
    ids=["doc1"]
)
```

**使用例（HuggingFace）:**
```python
import chromadb.utils.embedding_functions as embedding_functions

huggingface_ef = embedding_functions.HuggingFaceEmbeddingFunction(
    api_key="YOUR_API_KEY",
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)
```

**メリット:**
- ベクトル化コードを自分で書く必要がない
- モデルの切り替えが容易
- ドキュメント追加時に自動処理される

#### 3. 統合機能
- LangChainとの統合
- LlamaIndexとの統合
- 複数のプログラミング言語対応（Python, JavaScript/TypeScript, Ruby, PHP, Java）

#### 4. アーキテクチャ
- **Tenants**: 組織やユーザーごとの論理的なグループ
- **Collections**: 類似した特性を持つドキュメントのグループ
- **Indexing**: HNSW（Hierarchical Navigable Small World）アルゴリズムを使用

#### 5. 2025年のパフォーマンス改善
- Rustコアに書き直し
- GIL（Global Interpreter Lock）のボトルネック解消
- 書き込み・クエリ性能が最大4倍向上

### pgvector の主要機能

#### 1. ハイブリッド検索
SQLのWHERE句とベクトル類似検索を組み合わせた検索が可能。

例: 「特定のカテゴリの中から、クエリベクトルに最も近い項目を探す」

#### 2. インデックスタイプ
- **IVFFlat**: ベクトル空間を分割して検索範囲を限定
- **HNSW**: グラフベース構造、高効率な近似最近傍検索

HNSWが推奨される。

#### 3. PostgreSQLとの統合
- JOINやトランザクションなど、PostgreSQLの既存機能と組み合わせ可能
- ACID準拠
- 既存のPostgreSQLツール・エコシステムが利用可能

#### 4. ユースケース
- 自然言語処理（感情分析、文書分類）
- レコメンデーションシステム
- 画像検索・認識
- 異常検知
- RAG（Retrieval Augmented Generation）

## 推奨ユースケース

### ChromaDB が適している場合
- プロトタイピング
- 小規模アプリケーション
- 純粋なベクトル検索が中心
- 簡単にセットアップして試したい
- LangChain/LlamaIndexとの統合を重視

### pgvector が適している場合
- 通常のSQLクエリとベクトル検索を**同時に**使いたい
- 既存のPostgreSQLデータベースがある
- トランザクション制御やACIDが必要
- 混合データ（構造化データ + ベクトルデータ）の扱い

## 移行パターン

多くのアプリケーションは、以下のような移行パスを取る：

1. **プロトタイプ段階**: ChromaDBまたはpgvectorで開発
2. **本番スケール**: Pinecone、Weaviateなどの商用ソリューションへ移行

## このプロジェクトでの検討事項

### 前提条件
- ローカル環境で動作
- 単一エージェント（現時点）
- knowledgeはmdファイルで管理（環境変数 `KNOWLEDGE_ROOT` で指定）
- tasks、task_logs、decisionsは別のRDB（SQLite or PostgreSQL）で管理

### 選択肢

#### 選択肢A: SQLite + ChromaDB
```
自作API (Python + FastMCP)
    ↓
├── SQLite (tasks, task_logs, decisions)
└── ChromaDB (knowledgeのベクトル化)
```

**メリット:**
- セットアップが最も簡単
- 自動埋め込み機能が使える
- ベクトル検索に特化した機能が豊富
- LangChain/LlamaIndexとの統合が容易

**デメリット:**
- tasksテーブルとknowledgeを結びつけた検索がやや面倒

#### 選択肢B: PostgreSQL + pgvector
```
自作API (Python + FastMCP)
    ↓
└── PostgreSQL (tasks, task_logs, decisions, knowledge)
```

**メリット:**
- すべてのデータが1つのDBに統合
- SQLとベクトル検索を組み合わせやすい
- 例: 「タスクXに関連する知識を探す」がSQLで書ける

**デメリット:**
- PostgreSQLのセットアップが必要
- 自動埋め込み機能がない（自分で実装が必要）
- SQLiteから移行が必要

### 重要な質問

**ベクトル検索と通常のデータを組み合わせた検索が必要か？**

- **不要な場合**: ChromaDBで十分（シンプルで使いやすい）
- **必要な場合**: pgvectorの方が便利

例:
- ❌ 「こういう知識ないかな？」（単純な検索） → ChromaDB
- ✅ 「タスクXに関連する知識を探す」（結合検索） → pgvector

## 参考リンク

- [Chroma vs pgvector | Zilliz](https://zilliz.com/comparison/chroma-vs-pgvector)
- [ChromaDB Embedding Functions](https://docs.trychroma.com/docs/embeddings/embedding-functions)
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [ChromaDB GitHub](https://github.com/chroma-core/chroma)
