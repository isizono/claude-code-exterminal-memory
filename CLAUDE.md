## 開発フロー

- 実装前に関連トピックのget_decisionsを取得し、ユーザーに仕様確認を取ってから着手する

## コミット規約

Conventional Commits形式（scopeなし）。typeは英語、subjectは日本語。

- `feat:` / `fix:` / `docs:` / `refactor:` / `test:` / `chore:`
- 例: `feat: tasksテーブルのスキーマを実装`
- bodyは変更理由が自明でない場合のみ

## ブランチ戦略

- main直push禁止（pre-pushフックで防止）
- ブランチは必ずorigin/mainの最新から切る
- worktreeは`.trees/`配下に作成する
- 命名: `feature/<要約>`, `fix/<要約>`, `docs/<要約>`（英語ケバブケース）
