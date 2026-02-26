--
-- depends: 0004_fix_decisions_update_trigger

-- ベクトル検索用インデックス（search_indexのrowidに対応するembeddingを保持）
CREATE VIRTUAL TABLE IF NOT EXISTS vec_index USING vec0(
  embedding float[384]
);
