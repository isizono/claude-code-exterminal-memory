"""ナレッジ管理サービス"""
import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class KnowledgeCategory(str, Enum):
    """ナレッジのカテゴリ"""
    REFERENCES = "references"  # 外部情報（web検索結果、公式ドキュメント等）
    FACTS = "facts"  # コードベース情報


def get_knowledge_root() -> Path:
    """
    KNOWLEDGE_ROOT環境変数からナレッジ保存先を取得
    未設定の場合は ~/.claude/knowledge/ をデフォルトとする
    """
    root = os.environ.get("KNOWLEDGE_ROOT")
    if root:
        return Path(root).expanduser()
    return Path.home() / ".claude" / "knowledge"


def ensure_directories(root: Path) -> None:
    """
    ナレッジディレクトリ構造を初期化
    - root/references/
    - root/facts/
    """
    for category in KnowledgeCategory:
        (root / category.value).mkdir(parents=True, exist_ok=True)


def generate_filename(title: str) -> str:
    """
    タイトルからファイル名を生成
    日本語そのままでOK（決定事項: ID:80）
    """
    # 危険な文字を除去（ファイルシステムで問題になる文字）
    unsafe_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\n', '\r']
    filename = title
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    return filename.strip()


def get_unique_filepath(directory: Path, base_name: str) -> Path:
    """
    衝突しないファイルパスを取得
    同名ファイルが存在する場合は連番を付与（例: タイトル_1.md）
    """
    filepath = directory / f"{base_name}.md"
    if not filepath.exists():
        return filepath

    counter = 1
    while True:
        filepath = directory / f"{base_name}_{counter}.md"
        if not filepath.exists():
            return filepath
        counter += 1


def create_frontmatter(tags: list[str], created_at: Optional[datetime] = None) -> str:
    """
    YAMLフロントマターを生成
    """
    if created_at is None:
        created_at = datetime.now()

    tags_yaml = "\n".join(f"  - {tag}" for tag in tags) if tags else ""
    tags_section = f"tags:\n{tags_yaml}" if tags else "tags: []"

    return f"""---
{tags_section}
created_at: {created_at.strftime("%Y-%m-%d %H:%M:%S")}
---
"""


def add_knowledge(
    title: str,
    content: str,
    tags: list[str],
    category: str,
) -> dict:
    """
    ナレッジをmdファイルとして保存

    Args:
        title: ナレッジのタイトル（ファイル名になる）
        content: 本文（マークダウン）
        tags: タグ一覧
        category: カテゴリ（"references" または "facts"）

    Returns:
        保存結果（file_path を含む）
    """
    try:
        # カテゴリのバリデーション
        try:
            cat = KnowledgeCategory(category)
        except ValueError:
            return {
                "error": {
                    "code": "INVALID_CATEGORY",
                    "message": f"Invalid category: {category}. Must be one of {[c.value for c in KnowledgeCategory]}",
                }
            }

        # ディレクトリ構造を確保
        root = get_knowledge_root()
        ensure_directories(root)

        # ファイル名生成
        base_name = generate_filename(title)
        if not base_name:
            return {
                "error": {
                    "code": "INVALID_TITLE",
                    "message": "Title cannot be empty or contain only special characters",
                }
            }

        # 保存先ディレクトリ
        target_dir = root / cat.value

        # 衝突しないファイルパスを取得
        filepath = get_unique_filepath(target_dir, base_name)

        # フロントマター + コンテンツを作成
        frontmatter = create_frontmatter(tags)
        full_content = frontmatter + "\n" + content

        # ファイル書き込み
        filepath.write_text(full_content, encoding="utf-8")

        return {
            "file_path": str(filepath),
            "title": title,
            "category": cat.value,
            "tags": tags,
        }

    except Exception as e:
        return {
            "error": {
                "code": "FILE_SYSTEM_ERROR",
                "message": str(e),
            }
        }
