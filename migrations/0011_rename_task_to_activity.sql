-- Migration 011: task→activityリネーム
--
-- depends: 0010_remove_subjects
--
-- 変更内容:
--   - tasks → activities テーブルリネーム
--   - task_tags → activity_tags テーブルリネーム（task_id → activity_id）
--   - search_index.source_type 'task' → 'activity' 更新
--   - taskトリガー3個をDROP、activityトリガー3個を作成
--   - インデックスリネーム
--   - vec_indexのsource_type更新（search_index経由、rowid不変のためvec_index自体は変更不要）

-- ============================================
-- Step 1: 既存taskトリガー3個をDROP
-- ============================================

DROP TRIGGER IF EXISTS trg_search_tasks_insert;
DROP TRIGGER IF EXISTS trg_search_tasks_update;
DROP TRIGGER IF EXISTS trg_search_tasks_delete;

-- ============================================
-- Step 2: tasks → activities テーブルリネーム
-- ============================================

ALTER TABLE tasks RENAME TO activities;

-- ============================================
-- Step 3: task_tags → activity_tags テーブルリネーム
-- ============================================

ALTER TABLE task_tags RENAME TO activity_tags;

-- ============================================
-- Step 4: activity_tags.task_id → activity_id カラムリネーム
-- ============================================

ALTER TABLE activity_tags RENAME COLUMN task_id TO activity_id;

-- ============================================
-- Step 5: search_index.source_type 'task' → 'activity' 更新
-- ============================================

UPDATE search_index SET source_type = 'activity' WHERE source_type = 'task';

-- ============================================
-- Step 6: インデックスリネーム
-- ============================================

DROP INDEX IF EXISTS idx_tasks_status;
CREATE INDEX idx_activities_status ON activities(status);

-- ============================================
-- Step 7: 新トリガー3個を作成（source_type='activity'、テーブル名=activities）
-- ============================================

CREATE TRIGGER IF NOT EXISTS trg_search_activities_insert
AFTER INSERT ON activities
BEGIN
  INSERT INTO search_index (source_type, source_id, title)
  VALUES ('activity', NEW.id, NEW.title);
  INSERT INTO search_index_fts (rowid, title, body)
  VALUES (last_insert_rowid(), NEW.title, NEW.description);
END;

CREATE TRIGGER IF NOT EXISTS trg_search_activities_update
AFTER UPDATE ON activities
BEGIN
  INSERT INTO search_index_fts (search_index_fts, rowid, title, body)
  VALUES ('delete',
    (SELECT id FROM search_index WHERE source_type = 'activity' AND source_id = OLD.id),
    OLD.title, OLD.description);
  UPDATE search_index
  SET title = NEW.title
  WHERE source_type = 'activity' AND source_id = NEW.id;
  INSERT INTO search_index_fts (rowid, title, body)
  VALUES (
    (SELECT id FROM search_index WHERE source_type = 'activity' AND source_id = NEW.id),
    NEW.title, NEW.description);
END;

CREATE TRIGGER IF NOT EXISTS trg_search_activities_delete
AFTER DELETE ON activities
BEGIN
  INSERT INTO search_index_fts (search_index_fts, rowid, title, body)
  VALUES ('delete',
    (SELECT id FROM search_index WHERE source_type = 'activity' AND source_id = OLD.id),
    OLD.title, OLD.description);
  DELETE FROM search_index WHERE source_type = 'activity' AND source_id = OLD.id;
END;

-- ============================================
-- Step 8: vec_index
-- vec_indexはsearch_index.idをrowidとして参照する。
-- search_indexのrowid自体は変わらない（source_typeの値が変わるだけ）ので、
-- vec_indexの変更は不要。
-- ============================================
