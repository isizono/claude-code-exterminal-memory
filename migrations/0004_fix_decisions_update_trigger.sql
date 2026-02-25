-- Migration 004: decisions更新トリガーのWHEN条件修正
--
-- 問題:
--   trg_search_decisions_update は WHEN OLD.topic_id IS NOT NULL のみで発火するため、
--   topic_id が非NULL→NULLに変更された場合に search_index のエントリが残り続ける。
--   また topic_id が NULL→非NULLに変更された場合に search_index にエントリが作られない。
--
-- 修正:
--   1つのトリガーを3つに分割し、全ケースを網羅する。
--   - trg_search_decisions_update: 非NULL→非NULL（インデックス更新）
--   - trg_search_decisions_update_remove: 非NULL→NULL（インデックス削除）
--   - trg_search_decisions_update_add: NULL→非NULL（インデックス追加）
--
-- depends: 0003_project_to_subject

-- 既存トリガーを削除
DROP TRIGGER IF EXISTS trg_search_decisions_update;

-- Case 1: topic_id 非NULL→非NULL（既存エントリを更新）
CREATE TRIGGER IF NOT EXISTS trg_search_decisions_update
AFTER UPDATE ON decisions
WHEN OLD.topic_id IS NOT NULL AND NEW.topic_id IS NOT NULL
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

-- Case 2: topic_id 非NULL→NULL（インデックスから削除）
CREATE TRIGGER IF NOT EXISTS trg_search_decisions_update_remove
AFTER UPDATE ON decisions
WHEN OLD.topic_id IS NOT NULL AND NEW.topic_id IS NULL
BEGIN
  INSERT INTO search_index_fts (search_index_fts, rowid, title, body)
  VALUES ('delete',
    (SELECT id FROM search_index WHERE source_type = 'decision' AND source_id = OLD.id),
    OLD.decision, OLD.reason);
  DELETE FROM search_index WHERE source_type = 'decision' AND source_id = OLD.id;
END;

-- Case 3: topic_id NULL→非NULL（インデックスに追加）
CREATE TRIGGER IF NOT EXISTS trg_search_decisions_update_add
AFTER UPDATE ON decisions
WHEN OLD.topic_id IS NULL AND NEW.topic_id IS NOT NULL
BEGIN
  INSERT INTO search_index (source_type, source_id, subject_id, title)
  VALUES ('decision', NEW.id,
    (SELECT subject_id FROM discussion_topics WHERE id = NEW.topic_id),
    NEW.decision);
  INSERT INTO search_index_fts (rowid, title, body)
  VALUES (last_insert_rowid(), NEW.decision, NEW.reason);
END;
