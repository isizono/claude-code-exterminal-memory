-- Migration 003: projects → subjects リネーム + asana_url カラム削除
--
-- 必要な SQLite バージョン: 3.35.0 以上
--   - RENAME COLUMN: 3.25.0+
--   - DROP COLUMN:   3.35.0+
--
-- 変更内容:
--   - テーブル名 projects → subjects
--   - discussion_topics.project_id → subject_id
--   - tasks.project_id → subject_id
--   - search_index.project_id → subject_id
--   - subjects.asana_url カラム削除
--   - インデックス名変更（idx_topics_project_id → idx_topics_subject_id 等）
--   - トリガー9個を DROP → 新カラム名で再 CREATE
--
-- depends: 0002_add_fts5_search

-- 注: ALTER TABLE RENAME / RENAME COLUMN / DROP COLUMN は FK チェックを
-- トリガーしないため、PRAGMA foreign_keys = OFF は不要。
-- yoyo はマイグレーションをトランザクション内で実行するため、
-- PRAGMA foreign_keys はトランザクション中に変更できない点にも留意。

-- ============================================
-- Step 1: 既存トリガーをDROP
-- ============================================

DROP TRIGGER IF EXISTS trg_search_topics_insert;
DROP TRIGGER IF EXISTS trg_search_topics_update;
DROP TRIGGER IF EXISTS trg_search_topics_delete;
DROP TRIGGER IF EXISTS trg_search_decisions_insert;
DROP TRIGGER IF EXISTS trg_search_decisions_update;
DROP TRIGGER IF EXISTS trg_search_decisions_delete;
DROP TRIGGER IF EXISTS trg_search_tasks_insert;
DROP TRIGGER IF EXISTS trg_search_tasks_update;
DROP TRIGGER IF EXISTS trg_search_tasks_delete;

-- ============================================
-- Step 2: テーブル名リネーム
-- ============================================

ALTER TABLE projects RENAME TO subjects;

-- ============================================
-- Step 3: カラム名リネーム
-- ============================================

ALTER TABLE discussion_topics RENAME COLUMN project_id TO subject_id;
ALTER TABLE tasks RENAME COLUMN project_id TO subject_id;
ALTER TABLE search_index RENAME COLUMN project_id TO subject_id;

-- ============================================
-- Step 4: asana_url カラム削除
-- SQLite 3.35.0+ の ALTER TABLE ... DROP COLUMN を使用
-- ============================================

ALTER TABLE subjects DROP COLUMN asana_url;

-- ============================================
-- Step 5: インデックスを DROP → 新名前で再 CREATE
-- ============================================

DROP INDEX IF EXISTS idx_topics_project_id;
DROP INDEX IF EXISTS idx_tasks_project_id;
DROP INDEX IF EXISTS idx_search_index_project;

CREATE INDEX IF NOT EXISTS idx_topics_subject_id ON discussion_topics(subject_id);
CREATE INDEX IF NOT EXISTS idx_tasks_subject_id ON tasks(subject_id);
CREATE INDEX IF NOT EXISTS idx_search_index_subject ON search_index(subject_id);

-- ============================================
-- Step 6: トリガーを新カラム名で再 CREATE
-- ============================================

-- discussion_topics
CREATE TRIGGER IF NOT EXISTS trg_search_topics_insert
AFTER INSERT ON discussion_topics
BEGIN
  INSERT INTO search_index (source_type, source_id, subject_id, title)
  VALUES ('topic', NEW.id, NEW.subject_id, NEW.title);
  INSERT INTO search_index_fts (rowid, title, body)
  VALUES (last_insert_rowid(), NEW.title, NEW.description);
END;

CREATE TRIGGER IF NOT EXISTS trg_search_topics_update
AFTER UPDATE ON discussion_topics
BEGIN
  INSERT INTO search_index_fts (search_index_fts, rowid, title, body)
  VALUES ('delete',
    (SELECT id FROM search_index WHERE source_type = 'topic' AND source_id = OLD.id),
    OLD.title, OLD.description);
  UPDATE search_index
  SET title = NEW.title, subject_id = NEW.subject_id
  WHERE source_type = 'topic' AND source_id = NEW.id;
  INSERT INTO search_index_fts (rowid, title, body)
  VALUES (
    (SELECT id FROM search_index WHERE source_type = 'topic' AND source_id = NEW.id),
    NEW.title, NEW.description);
END;

CREATE TRIGGER IF NOT EXISTS trg_search_topics_delete
AFTER DELETE ON discussion_topics
BEGIN
  INSERT INTO search_index_fts (search_index_fts, rowid, title, body)
  VALUES ('delete',
    (SELECT id FROM search_index WHERE source_type = 'topic' AND source_id = OLD.id),
    OLD.title, OLD.description);
  DELETE FROM search_index WHERE source_type = 'topic' AND source_id = OLD.id;
END;

-- decisions
CREATE TRIGGER IF NOT EXISTS trg_search_decisions_insert
AFTER INSERT ON decisions
WHEN NEW.topic_id IS NOT NULL
BEGIN
  INSERT INTO search_index (source_type, source_id, subject_id, title)
  VALUES ('decision', NEW.id,
    (SELECT subject_id FROM discussion_topics WHERE id = NEW.topic_id),
    NEW.decision);
  INSERT INTO search_index_fts (rowid, title, body)
  VALUES (last_insert_rowid(), NEW.decision, NEW.reason);
END;

CREATE TRIGGER IF NOT EXISTS trg_search_decisions_update
AFTER UPDATE ON decisions
WHEN OLD.topic_id IS NOT NULL
BEGIN
  INSERT INTO search_index_fts (search_index_fts, rowid, title, body)
  VALUES ('delete',
    (SELECT id FROM search_index WHERE source_type = 'decision' AND source_id = OLD.id),
    OLD.decision, OLD.reason);
  UPDATE search_index
  SET title = NEW.decision,
      subject_id = COALESCE(
        (SELECT subject_id FROM discussion_topics WHERE id = NEW.topic_id),
        subject_id)
  WHERE source_type = 'decision' AND source_id = NEW.id;
  INSERT INTO search_index_fts (rowid, title, body)
  VALUES (
    (SELECT id FROM search_index WHERE source_type = 'decision' AND source_id = NEW.id),
    NEW.decision, NEW.reason);
END;

CREATE TRIGGER IF NOT EXISTS trg_search_decisions_delete
AFTER DELETE ON decisions
WHEN OLD.topic_id IS NOT NULL
BEGIN
  INSERT INTO search_index_fts (search_index_fts, rowid, title, body)
  VALUES ('delete',
    (SELECT id FROM search_index WHERE source_type = 'decision' AND source_id = OLD.id),
    OLD.decision, OLD.reason);
  DELETE FROM search_index WHERE source_type = 'decision' AND source_id = OLD.id;
END;

-- tasks
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

