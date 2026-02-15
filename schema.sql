-- プロジェクトテーブル
CREATE TABLE IF NOT EXISTS projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name VARCHAR(255) NOT NULL UNIQUE,
  description TEXT NOT NULL,
  asana_url TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 議論トピックテーブル
CREATE TABLE IF NOT EXISTS discussion_topics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  parent_topic_id INTEGER REFERENCES discussion_topics(id) ON DELETE CASCADE,
  title VARCHAR(255) NOT NULL,
  description TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 議論ログテーブル
CREATE TABLE IF NOT EXISTS discussion_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  topic_id INTEGER NOT NULL REFERENCES discussion_topics(id),
  content TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 決定事項テーブル
CREATE TABLE IF NOT EXISTS decisions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  topic_id INTEGER REFERENCES discussion_topics(id),
  decision TEXT NOT NULL,
  reason TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- タスクテーブル
CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  title VARCHAR(255) NOT NULL,
  description TEXT NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'in_progress', 'blocked', 'completed')), -- pending/in_progress/blocked/completed
  topic_id INTEGER REFERENCES discussion_topics(id) ON DELETE SET NULL, -- blockedの時に関連する議論トピック
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_topics_project_id ON discussion_topics(project_id);
CREATE INDEX IF NOT EXISTS idx_topics_parent_id ON discussion_topics(parent_topic_id);
CREATE INDEX IF NOT EXISTS idx_logs_topic_id ON discussion_logs(topic_id);
CREATE INDEX IF NOT EXISTS idx_decisions_topic_id ON decisions(topic_id);
CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);

-- ============================================
-- FTS5統合検索
-- ============================================

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
