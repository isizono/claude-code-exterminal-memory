"""SessionStart hook: コンテキスト取得リマインダー注入"""
import json
import sys

_SESSION_START_MESSAGE = (
    "<system-reminder>"
    "セッションが開始しました。最初の応答を組み立てる前に、過去のコンテキストを取得してください。"
    "手順: (1) get_topics でトピック一覧を確認する。"
    "(2) 関連するトピックがあれば get_by_id で詳細を取得する。"
    "なければ add_topic で新しいトピックを作成する。"
    "(3) 必要に応じて get_decisions / get_logs でさらに詳細を取得する。"
    "この手順を省略すると stop hook にブロックされます。"
    "</system-reminder>"
)


def main() -> None:
    try:
        sys.stdin.read()  # stdinを消費（session_id等が渡されるが今は不使用）
        output = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": _SESSION_START_MESSAGE,
            }
        }
        print(json.dumps(output, ensure_ascii=False))
    except Exception as e:
        print(f"session_start_hook.py error: {e}", file=sys.stderr)
        print("{}")


if __name__ == "__main__":
    main()
