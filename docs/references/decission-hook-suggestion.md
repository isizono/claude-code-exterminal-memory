# 決定事項自動検出システムの実装

## 背景
Claude Codeの外部メモリシステム（claude-code-exterminal-memory）を開発中。
作業記録（task_logs）とは別に、「決定事項」（decisions）の自動検出・記録を実装したい。

## 決定事項の定義
- エージェントが認識合わせ（「これであってる？」「この方針でいい？」等）を行い
- ユーザーが承認（「OK」「それでいこう」「合意」等）した場合
- decisionsテーブルに記録すべき内容が発生したとみなす

## 採用するアプローチ: Prompt-Based Hooks

Claude CodeのStop hookで `type: "prompt"` を使用。
- 内蔵のHaikuが自動で呼び出される（APIキー管理不要）
- 決定事項を検出したら `decision: "block"` + `reason` でメインのClaude Codeに伝える
- Claude Code自身がreasonを見てMCPツール（decisions記録）を呼び出す

## 実装する設定
```json
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "prompt",
        "prompt": "以下の会話で「決定事項」があったか評価してください。\n\n決定事項の定義:\n- エージェントが認識合わせ（「これであってる？」等）を行い\n- ユーザーが承認（「OK」「それでいこう」等）した場合\n\n決定事項があれば:\n{\"decision\": \"block\", \"reason\": \"決定事項を検出しました。MCPツールでdecisionsテーブルに記録してください:\\n- matter: [何を決めたか]\\n- decision: [決定内容]\\n- reason: [理由]\"}\n\n決定事項がなければ:\n{\"decision\": \"approve\"}",
        "timeout": 30
      }]
    }]
  }
}
```

## フロー
```
ユーザー: 「OK、それでいこう」
    ↓
Claude Code: 応答完了 → Stopフック発火
    ↓
Hook (Haiku): $ARGUMENTSで会話評価
    ↓ 決定事項あり
Hook → {"decision": "block", "reason": "決定事項検出: ...を記録して"}
    ↓
Claude Code: 止まらずに続行、reasonを受け取る
    ↓
Claude Code: MCPツール呼び出し（decisions記録）
```

## 懸念事項: 文脈の制限

Stop hookの$ARGUMENTSに含まれるのは:
- session_id
- transcript_path（会話履歴ファイルのパス）
- stop_hook_active
- 等のメタデータのみ

**会話内容そのものは含まれない可能性がある。**
→ Prompt-Based Hooksで実際に何が渡されるか要検証

## 関連ファイル
- プロジェクト: /Users/babajunichi/workspace/claude-code-exterminal-memory/
- 設計ドキュメント: docs/project-context.md
- decisionsテーブル設計は既存ドキュメントに記載済み

## 参考ドキュメント
- Hooks公式リファレンス: https://code.claude.com/docs/en/hooks
- Hooksガイド: https://code.claude.com/docs/en/hooks-guide
- Agent Skills: https://code.claude.com/docs/en/skills
- Skillsベストプラクティス: https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices