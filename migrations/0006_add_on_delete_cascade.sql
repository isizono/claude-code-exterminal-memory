-- Migration 006: discussion_logsとdecisionsにON DELETE CASCADE追加
--
-- 背景:
--   discussion_logs.topic_idとdecisions.topic_idにON DELETE句がない。
--   トピック削除時に孤児レコードが残る問題を修正する。
--   両テーブルともtopic_idはNOT NULLなのでON DELETE CASCADEが適切。
--
-- 変更内容:
--   1. discussion_logsテーブルを再作成（ON DELETE CASCADE追加）
--   2. decisionsテーブルを再作成（ON DELETE CASCADE追加）
--   3. decisionsテーブルのDROP→再CREATEに伴い、FTS5トリガーを再作成
--
-- depends: 0005_decisions_topic_id_not_null

-- ================================================
-- Step 1: discussion_logs テーブル再作成
-- ================================================

ALTER TABLE discussion_logs RENAME TO discussion_logs_old;

CREATE TABLE discussion_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  topic_id INTEGER NOT NULL REFERENCES discussion_topics(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO discussion_logs (id, topic_id, content, created_at)
SELECT id, topic_id, content, created_at
FROM discussion_logs_old;

DROP TABLE discussion_logs_old;

CREATE INDEX IF NOT EXISTS idx_logs_topic_id ON discussion_logs(topic_id);

-- ================================================
-- Step 2: decisions テーブル再作成
-- ================================================

ALTER TABLE decisions RENAME TO decisions_old;

CREATE TABLE decisions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  topic_id INTEGER NOT NULL REFERENCES discussion_topics(id) ON DELETE CASCADE,
  decision TEXT NOT NULL,
  reason TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO decisions (id, topic_id, decision, reason, created_at)
SELECT id, topic_id, decision, reason, created_at
FROM decisions_old;

DROP TABLE decisions_old;

CREATE INDEX IF NOT EXISTS idx_decisions_topic_id ON decisions(topic_id);

-- ================================================
-- Step 3: FTS5トリガー再作成
-- decisionsテーブルのDROP→再CREATEにより、紐づくトリガーも自動削除される。
-- 0005で作成した簡素化版トリガー3つをそのまま再作成する。
-- ================================================

DROP TRIGGER IF EXISTS trg_search_decisions_insert;
DROP TRIGGER IF EXISTS trg_search_decisions_update;
DROP TRIGGER IF EXISTS trg_search_decisions_delete;

-- INSERTトリガー（topic_idは常にNOT NULL）
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

-- DELETEトリガー（topic_idは常にNOT NULL）
CREATE TRIGGER IF NOT EXISTS trg_search_decisions_delete
AFTER DELETE ON decisions
BEGIN
  INSERT INTO search_index_fts (search_index_fts, rowid, title, body)
  VALUES ('delete',
    (SELECT id FROM search_index WHERE source_type = 'decision' AND source_id = OLD.id),
    OLD.decision, OLD.reason);
  DELETE FROM search_index WHERE source_type = 'decision' AND source_id = OLD.id;
END;
