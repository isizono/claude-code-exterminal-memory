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
  project_id INTEGER NOT NULL REFERENCES projects(id),
  parent_topic_id INTEGER REFERENCES discussion_topics(id),
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
  project_id INTEGER NOT NULL REFERENCES projects(id),
  title VARCHAR(255) NOT NULL,
  description TEXT NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending/in_progress/blocked/completed
  topic_id INTEGER REFERENCES discussion_topics(id), -- blockedの時に関連する議論トピック
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- UPDATE時にupdated_atを自動更新するトリガー
CREATE TRIGGER IF NOT EXISTS update_tasks_timestamp
AFTER UPDATE ON tasks
FOR EACH ROW
BEGIN
  UPDATE tasks SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
END;

-- インデックス
CREATE INDEX IF NOT EXISTS idx_topics_project_id ON discussion_topics(project_id);
CREATE INDEX IF NOT EXISTS idx_topics_parent_id ON discussion_topics(parent_topic_id);
CREATE INDEX IF NOT EXISTS idx_logs_topic_id ON discussion_logs(topic_id);
CREATE INDEX IF NOT EXISTS idx_decisions_topic_id ON decisions(topic_id);
CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
