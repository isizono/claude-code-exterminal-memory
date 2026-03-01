-- Migration 005: decisions.topic_id NOT NULL制約追加とFTS5トリガー簡素化
--
-- 背景:
--   decisions.topic_idは現在NULLableだが、運用上すべてのdecisionはtopicに紐づくべき。
--   NOT NULL制約を追加し、FTS5トリガーのNULLケース分岐を簡素化する。
--
-- 変更内容:
--   1. decisionsテーブルを再作成（SQLiteはALTER COLUMNでNOT NULL追加不可のため）
--      - topic_id IS NULLのデータはfirst_topicに移行
--   2. FTS5トリガーのWHEN条件（NULLチェック）を除去
--   3. UPDATEトリガーを3分割から1つに統合（NULLケース不要）
--
-- depends: 0004_fix_decisions_update_trigger

-- Step 1: topic_id IS NULLのレコードをfirst_topicに移行
UPDATE decisions
SET topic_id = (
  SELECT dt.id
  FROM discussion_topics dt
  WHERE dt.title = 'first_topic'
  LIMIT 1
)
WHERE topic_id IS NULL;

-- Step 2: 旧テーブルをリネーム
ALTER TABLE decisions RENAME TO decisions_old;

-- Step 3: 新テーブル作成（topic_id NOT NULL）
CREATE TABLE decisions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  topic_id INTEGER NOT NULL REFERENCES discussion_topics(id),
  decision TEXT NOT NULL,
  reason TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Step 4: データコピー
INSERT INTO decisions (id, topic_id, decision, reason, created_at)
SELECT id, topic_id, decision, reason, created_at
FROM decisions_old;

-- Step 5: 旧テーブル削除
DROP TABLE decisions_old;

-- Step 6: インデックス再作成
CREATE INDEX IF NOT EXISTS idx_decisions_topic_id ON decisions(topic_id);

-- Step 7: FTS5トリガーの簡素化
-- 既存トリガーを削除
DROP TRIGGER IF EXISTS trg_search_decisions_insert;
DROP TRIGGER IF EXISTS trg_search_decisions_update;
DROP TRIGGER IF EXISTS trg_search_decisions_update_remove;
DROP TRIGGER IF EXISTS trg_search_decisions_update_add;
DROP TRIGGER IF EXISTS trg_search_decisions_delete;

-- INSERTトリガー（WHEN条件なし: topic_idは常にNOT NULL）
CREATE TRIGGER IF NOT EXISTS trg_search_decisions_insert
AFTER INSERT ON decisions
BEGIN
  INSERT INTO search_index (source_type, source_id, subject_id, title)
  VALUES ('decision', NEW.id,
    (SELECT subject_id FROM discussion_topics WHERE id = NEW.topic_id),
    NEW.decision);
  INSERT INTO search_index_fts (rowid, title, body)
  VALUES (last_insert_rowid(), NEW.decision, NEW.reason);
END;

-- UPDATEトリガー（1つに統合: NULLケース不要）
CREATE TRIGGER IF NOT EXISTS trg_search_decisions_update
AFTER UPDATE ON decisions
BEGIN
  INSERT INTO search_index_fts (search_index_fts, rowid, title, body)
  VALUES ('delete',
    (SELECT id FROM search_index WHERE source_type = 'decision' AND source_id = OLD.id),
    OLD.decision, OLD.reason);
  UPDATE search_index
  SET title = NEW.decision,
      subject_id = (SELECT subject_id FROM discussion_topics WHERE id = NEW.topic_id)
  WHERE source_type = 'decision' AND source_id = NEW.id;
  INSERT INTO search_index_fts (rowid, title, body)
  VALUES (
    (SELECT id FROM search_index WHERE source_type = 'decision' AND source_id = NEW.id),
    NEW.decision, NEW.reason);
END;

-- DELETEトリガー（WHEN条件なし: topic_idは常にNOT NULL）
CREATE TRIGGER IF NOT EXISTS trg_search_decisions_delete
AFTER DELETE ON decisions
BEGIN
  INSERT INTO search_index_fts (search_index_fts, rowid, title, body)
  VALUES ('delete',
    (SELECT id FROM search_index WHERE source_type = 'decision' AND source_id = OLD.id),
    OLD.decision, OLD.reason);
  DELETE FROM search_index WHERE source_type = 'decision' AND source_id = OLD.id;
END;
