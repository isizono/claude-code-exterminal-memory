-- depends: 0015_tag_canonical
ALTER TABLE activities ADD COLUMN topic_id INTEGER REFERENCES discussion_topics(id) ON DELETE SET NULL;
CREATE INDEX idx_activities_topic_id ON activities(topic_id);
