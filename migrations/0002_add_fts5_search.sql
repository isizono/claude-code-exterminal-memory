--
-- depends: 0001_initial_schema

-- 統合検索用の中間テーブル（メタ情報 + title のみ保持。bodyは持たない）
CREATE TABLE IF NOT EXISTS search_index (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_type TEXT NOT NULL,
  source_id INTEGER NOT NULL,
  project_id INTEGER NOT NULL,
  title TEXT NOT NULL DEFAULT '',
  UNIQUE(source_type, source_id)
);

CREATE INDEX IF NOT EXISTS idx_search_index_project
  ON search_index(project_id);
CREATE INDEX IF NOT EXISTS idx_search_index_source
  ON search_index(source_type, source_id);

-- FTS5仮想テーブル（contentless方式）
CREATE VIRTUAL TABLE IF NOT EXISTS search_index_fts USING fts5(
  title,
  body,
  content='',
  tokenize='trigram'
);

-- === トリガー定義（topics, decisions, tasks の3テーブル） ===

-- discussion_topics
CREATE TRIGGER IF NOT EXISTS trg_search_topics_insert
AFTER INSERT ON discussion_topics
BEGIN
  INSERT INTO search_index (source_type, source_id, project_id, title)
  VALUES ('topic', NEW.id, NEW.project_id, NEW.title);
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
  SET title = NEW.title, project_id = NEW.project_id
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
  INSERT INTO search_index (source_type, source_id, project_id, title)
  VALUES ('decision', NEW.id,
    (SELECT project_id FROM discussion_topics WHERE id = NEW.topic_id),
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
      project_id = COALESCE(
        (SELECT project_id FROM discussion_topics WHERE id = NEW.topic_id),
        project_id)
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
  INSERT INTO search_index (source_type, source_id, project_id, title)
  VALUES ('task', NEW.id, NEW.project_id, NEW.title);
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
  SET title = NEW.title, project_id = NEW.project_id
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
