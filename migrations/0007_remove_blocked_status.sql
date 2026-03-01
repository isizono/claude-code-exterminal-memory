-- Migration 007: tasksテーブルからblockedステータスを除去
--
-- 背景:
--   blockedステータスは一度も使われたことがなく、TaskStatusListener/TaskStatusManagerImpl
--   パターンと共に廃止する。CHECK制約からblockedを除去する。
--
-- 変更内容:
--   1. tasksテーブルを再作成（CHECK制約からblockedを除去）
--   2. データ移行（blockedをpendingに変換）
--   3. FTS5トリガー（tasks関連3つ）をDROP→再CREATE
--
-- depends: 0006_add_on_delete_cascade

-- ================================================
-- Step 1: 新テーブル作成（blockedなしのCHECK制約）
-- ================================================

CREATE TABLE tasks_new (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
  title VARCHAR(255) NOT NULL,
  description TEXT NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'in_progress', 'completed')),
  topic_id INTEGER REFERENCES discussion_topics(id) ON DELETE SET NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ================================================
-- Step 2: データ移行（blockedをpendingに変換）
-- ================================================

INSERT INTO tasks_new SELECT
  id, subject_id, title, description,
  CASE WHEN status = 'blocked' THEN 'pending' ELSE status END,
  topic_id, created_at, updated_at
FROM tasks;

-- ================================================
-- Step 3: FTS5トリガー一時削除（tasksテーブルを参照しているもの）
-- ================================================

DROP TRIGGER IF EXISTS trg_search_tasks_insert;
DROP TRIGGER IF EXISTS trg_search_tasks_update;
DROP TRIGGER IF EXISTS trg_search_tasks_delete;

-- ================================================
-- Step 4: 旧テーブル削除 + リネーム
-- ================================================

DROP TABLE tasks;
ALTER TABLE tasks_new RENAME TO tasks;

-- ================================================
-- Step 5: インデックス再作成
-- ================================================

CREATE INDEX IF NOT EXISTS idx_tasks_subject_id ON tasks(subject_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);

-- ================================================
-- Step 6: FTS5トリガー再作成
-- 0003_project_to_subject.sql で定義されたトリガーを再作成
-- （subject_idカラム名で定義）
-- ================================================

CREATE TRIGGER IF NOT EXISTS trg_search_tasks_insert
AFTER INSERT ON tasks
BEGIN
  INSERT INTO search_index (source_type, source_id, subject_id, title)
  VALUES ('task', NEW.id, NEW.subject_id, NEW.title);
  INSERT INTO search_index_fts (rowid, title, body)
  VALUES (last_insert_rowid(), NEW.title, NEW.description);
END;

CREATE TRIGGER IF NOT EXISTS trg_search_tasks_update
AFTER UPDATE ON tasks
BEGIN
  INSERT INTO search_index_fts (search_index_fts, rowid, title, body)
  VALUES ('delete',
    (SELECT id FROM search_index WHERE source_type = 'task' AND source_id = OLD.id),
    OLD.title, OLD.description);
  UPDATE search_index
  SET title = NEW.title, subject_id = NEW.subject_id
  WHERE source_type = 'task' AND source_id = NEW.id;
  INSERT INTO search_index_fts (rowid, title, body)
  VALUES (
    (SELECT id FROM search_index WHERE source_type = 'task' AND source_id = NEW.id),
    NEW.title, NEW.description);
END;

CREATE TRIGGER IF NOT EXISTS trg_search_tasks_delete
AFTER DELETE ON tasks
BEGIN
  INSERT INTO search_index_fts (search_index_fts, rowid, title, body)
  VALUES ('delete',
    (SELECT id FROM search_index WHERE source_type = 'task' AND source_id = OLD.id),
    OLD.title, OLD.description);
  DELETE FROM search_index WHERE source_type = 'task' AND source_id = OLD.id;
END;
