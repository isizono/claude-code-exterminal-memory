-- depends: 0018_add_material_search_index
CREATE TABLE rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

INSERT INTO rules (content) VALUES
('IDを指示語代わりにしない。ユーザーにIDで言及するときは必ずタイトルや要約を添える');
