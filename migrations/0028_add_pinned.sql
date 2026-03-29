-- Migration 028: discussion_logs, decisions, materialsにpinnedカラムを追加
--
-- depends: 0027_add_shelved_status
--
-- 背景:
--   重要なエンティティをpinして重要度を明示するための準備。
--   pin基準: 「これを知らずに着手したら間違った方向に進む」レベルの情報。
--
-- 変更内容:
--   discussion_logs, decisions, materialsの3テーブルにpinned BOOLEAN NOT NULL DEFAULT 0を追加

ALTER TABLE discussion_logs ADD COLUMN pinned BOOLEAN NOT NULL DEFAULT 0;
ALTER TABLE decisions ADD COLUMN pinned BOOLEAN NOT NULL DEFAULT 0;
ALTER TABLE materials ADD COLUMN pinned BOOLEAN NOT NULL DEFAULT 0;
