"""Embeddingサービス: ruri-v3-70mモデルによるベクトル生成とvec_index操作"""
import logging
from typing import Optional

from sqlite_vec import serialize_float32

from src.db import execute_query, get_connection

logger = logging.getLogger(__name__)

# 定数
DOC_PREFIX = "検索文書: "
QUERY_PREFIX = "検索クエリ: "
MODEL_NAME = "cl-nagoya/ruri-v3-70m"

# グローバル状態（遅延ロード用）
_model = None
_model_load_failed = False
_backfill_done = False


def _load_model():
    """モデルを遅延ロードする。失敗時はフラグを立てて以降Noneを返す。"""
    global _model, _model_load_failed
    if _model is not None:
        return _model
    if _model_load_failed:
        return None
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
        logger.info(f"Embedding model loaded: {MODEL_NAME}")
        return _model
    except Exception as e:
        _model_load_failed = True
        logger.warning(f"Failed to load embedding model: {e}")
        return None


def _ensure_initialized():
    """モデルのロードとバックフィルを一度だけ実行する。"""
    global _backfill_done
    model = _load_model()
    if model is not None and not _backfill_done:
        backfill_embeddings()
        _backfill_done = True
    return model


def encode_document(text: str) -> Optional[list[float]]:
    """ドキュメント用embedding生成。prefix付き。"""
    model = _ensure_initialized()
    if model is None:
        return None
    prefixed = DOC_PREFIX + text
    embedding = model.encode(prefixed)
    return embedding.tolist()


def encode_query(text: str) -> Optional[list[float]]:
    """クエリ用embedding生成。prefix付き。"""
    model = _ensure_initialized()
    if model is None:
        return None
    prefixed = QUERY_PREFIX + text
    embedding = model.encode(prefixed)
    return embedding.tolist()


def generate_and_store_embedding(source_type: str, source_id: int, text: str) -> None:
    """search_indexからIDを取得してembeddingを生成・保存する。失敗してもraiseしない。"""
    try:
        rows = execute_query(
            "SELECT id FROM search_index WHERE source_type = ? AND source_id = ?",
            (source_type, source_id),
        )
        if rows:
            search_index_id = rows[0]["id"]
            embedding = encode_document(text)
            if embedding is not None:
                insert_embedding(search_index_id, embedding)
    except Exception as e:
        logger.warning(f"Failed to generate embedding for {source_type} {source_id}: {e}")


def _insert_embedding_row(conn, search_index_id: int, embedding: list[float]) -> None:
    """vec_indexに1行INSERTする（コミットは呼び出し側の責任）。"""
    blob = serialize_float32(embedding)
    conn.execute(
        "INSERT INTO vec_index(rowid, embedding) VALUES (?, ?)",
        (search_index_id, blob),
    )


def insert_embedding(search_index_id: int, embedding: list[float]) -> None:
    """vec_indexにembeddingをINSERTする。"""
    conn = get_connection()
    try:
        _insert_embedding_row(conn, search_index_id, embedding)
        conn.commit()
    except Exception as e:
        logger.warning(f"Failed to insert embedding for search_index_id={search_index_id}: {e}")
    finally:
        conn.close()


def update_embedding(search_index_id: int, embedding: list[float]) -> None:
    """vec_indexのembeddingを更新する（DELETE+INSERT）。"""
    conn = get_connection()
    try:
        blob = serialize_float32(embedding)
        conn.execute("DELETE FROM vec_index WHERE rowid = ?", (search_index_id,))
        conn.execute(
            "INSERT INTO vec_index(rowid, embedding) VALUES (?, ?)",
            (search_index_id, blob),
        )
        conn.commit()
    except Exception as e:
        logger.warning(f"Failed to update embedding for search_index_id={search_index_id}: {e}")
    finally:
        conn.close()


def delete_embedding(search_index_id: int) -> None:
    """vec_indexからembeddingを削除する。"""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM vec_index WHERE rowid = ?", (search_index_id,))
        conn.commit()
    except Exception as e:
        logger.warning(f"Failed to delete embedding for search_index_id={search_index_id}: {e}")
    finally:
        conn.close()


def _get_source_text(conn, source_type: str, source_id: int) -> Optional[str]:
    """ソーステーブルからembedding対象テキストを取得する。"""
    if source_type == "topic":
        row = conn.execute(
            "SELECT title, description FROM discussion_topics WHERE id = ?",
            (source_id,)
        ).fetchone()
        if row:
            return row[0] + " " + (row[1] or "")
    elif source_type == "decision":
        row = conn.execute(
            "SELECT decision, reason FROM decisions WHERE id = ?",
            (source_id,)
        ).fetchone()
        if row:
            return row[0] + " " + (row[1] or "")
    elif source_type == "task":
        row = conn.execute(
            "SELECT title, description FROM tasks WHERE id = ?",
            (source_id,)
        ).fetchone()
        if row:
            return row[0] + " " + (row[1] or "")
    return None


def backfill_embeddings() -> int:
    """search_indexにあってvec_indexにないレコードのembeddingを一括生成する。

    Returns: 生成したembedding数
    """
    model = _load_model()
    if model is None:
        return 0

    conn = get_connection()
    try:
        # vec_indexに存在しないsearch_indexレコードを取得
        rows = conn.execute("""
            SELECT si.id, si.source_type, si.source_id, si.title
            FROM search_index si
            LEFT JOIN vec_index vi ON si.id = vi.rowid
            WHERE vi.rowid IS NULL
        """).fetchall()

        if not rows:
            return 0

        count = 0
        for row in rows:
            search_index_id = row[0]
            source_type = row[1]
            source_id = row[2]

            # ソーステーブルから本文テキストを取得
            text = _get_source_text(conn, source_type, source_id)
            if text is None:
                continue

            try:
                prefixed = DOC_PREFIX + text
                embedding = model.encode(prefixed).tolist()
                _insert_embedding_row(conn, search_index_id, embedding)
                count += 1
            except Exception as e:
                logger.warning(f"Failed to backfill embedding for search_index_id={search_index_id}: {e}")
                continue

        conn.commit()
        logger.info(f"Backfilled {count} embeddings")
        return count
    except Exception as e:
        logger.warning(f"Embedding backfill failed: {e}")
        return 0
    finally:
        conn.close()
