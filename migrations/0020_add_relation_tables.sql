-- depends: 0019_add_reminders

-- topic-topic リレーション
CREATE TABLE topic_relations (
    topic_id_1 INTEGER NOT NULL REFERENCES discussion_topics(id) ON DELETE CASCADE,
    topic_id_2 INTEGER NOT NULL REFERENCES discussion_topics(id) ON DELETE CASCADE,
    created_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (topic_id_1, topic_id_2),
    CHECK (topic_id_1 < topic_id_2)
);

-- topic-activity リレーション
CREATE TABLE topic_activity_relations (
    topic_id INTEGER NOT NULL REFERENCES discussion_topics(id) ON DELETE CASCADE,
    activity_id INTEGER NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    created_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (topic_id, activity_id)
);

-- activity-activity リレーション
CREATE TABLE activity_relations (
    activity_id_1 INTEGER NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    activity_id_2 INTEGER NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    created_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (activity_id_1, activity_id_2),
    CHECK (activity_id_1 < activity_id_2)
);

-- 逆方向参照用インデックス
CREATE INDEX idx_topic_relations_id2 ON topic_relations(topic_id_2);
CREATE INDEX idx_topic_activity_relations_activity ON topic_activity_relations(activity_id);
CREATE INDEX idx_activity_relations_id2 ON activity_relations(activity_id_2);

-- 双方向VIEW
CREATE VIEW relations_view AS
  SELECT topic_id_1 AS source_id, 'topic' AS source_type,
         topic_id_2 AS target_id, 'topic' AS target_type, created_at
  FROM topic_relations
  UNION ALL
  SELECT topic_id_2, 'topic', topic_id_1, 'topic', created_at
  FROM topic_relations
  UNION ALL
  SELECT topic_id, 'topic', activity_id, 'activity', created_at
  FROM topic_activity_relations
  UNION ALL
  SELECT activity_id, 'activity', topic_id, 'topic', created_at
  FROM topic_activity_relations
  UNION ALL
  SELECT activity_id_1, 'activity', activity_id_2, 'activity', created_at
  FROM activity_relations
  UNION ALL
  SELECT activity_id_2, 'activity', activity_id_1, 'activity', created_at
  FROM activity_relations;
