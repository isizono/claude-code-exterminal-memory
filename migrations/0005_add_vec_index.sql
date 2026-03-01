--
-- depends: 0004_fix_decisions_update_trigger

-- ベクトル検索用インデックス（search_indexのrowidに対応するembeddingを保持）
-- 注意: 仮想テーブルのため外部キー制約が使えない。
-- search_index のレコードを削除する際は、アプリケーション層で
-- 対応する vec_index レコードも削除すること（孤児レコード防止）。
CREATE VIRTUAL TABLE IF NOT EXISTS vec_index USING vec0(
  embedding float[384]
);
