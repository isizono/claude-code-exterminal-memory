"""knowledge_service のユニットテスト"""
import os
import tempfile
import pytest
from pathlib import Path
from src.services.knowledge_service import (
    get_knowledge_root,
    ensure_directories,
    generate_filename,
    get_unique_filepath,
    create_frontmatter,
    add_knowledge,
    KnowledgeCategory,
)


@pytest.fixture
def temp_knowledge_root():
    """テスト用の一時的なKNOWLEDGE_ROOTを作成する"""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["KNOWLEDGE_ROOT"] = tmpdir
        yield Path(tmpdir)
        # クリーンアップ
        if "KNOWLEDGE_ROOT" in os.environ:
            del os.environ["KNOWLEDGE_ROOT"]


# ========================================
# get_knowledge_root のテスト
# ========================================


def test_get_knowledge_root_from_env():
    """環境変数からKNOWLEDGE_ROOTを取得できる"""
    os.environ["KNOWLEDGE_ROOT"] = "/custom/path"
    try:
        result = get_knowledge_root()
        assert result == Path("/custom/path")
    finally:
        del os.environ["KNOWLEDGE_ROOT"]


def test_get_knowledge_root_default():
    """環境変数未設定時はデフォルトパスを返す"""
    if "KNOWLEDGE_ROOT" in os.environ:
        del os.environ["KNOWLEDGE_ROOT"]
    result = get_knowledge_root()
    assert result == Path.home() / ".claude" / "knowledge"


def test_get_knowledge_root_expands_tilde():
    """チルダ展開ができる"""
    os.environ["KNOWLEDGE_ROOT"] = "~/my-knowledge"
    try:
        result = get_knowledge_root()
        assert result == Path.home() / "my-knowledge"
    finally:
        del os.environ["KNOWLEDGE_ROOT"]


# ========================================
# ensure_directories のテスト
# ========================================


def test_ensure_directories_creates_structure(temp_knowledge_root):
    """ディレクトリ構造を作成できる"""
    ensure_directories(temp_knowledge_root)

    assert (temp_knowledge_root / "references").exists()
    assert (temp_knowledge_root / "facts").exists()
    assert (temp_knowledge_root / "references").is_dir()
    assert (temp_knowledge_root / "facts").is_dir()


def test_ensure_directories_idempotent(temp_knowledge_root):
    """ディレクトリが既に存在していてもエラーにならない"""
    ensure_directories(temp_knowledge_root)
    # 2回目の呼び出しでもエラーにならない
    ensure_directories(temp_knowledge_root)

    assert (temp_knowledge_root / "references").exists()
    assert (temp_knowledge_root / "facts").exists()


# ========================================
# generate_filename のテスト
# ========================================


def test_generate_filename_japanese():
    """日本語タイトルがそのままファイル名になる"""
    result = generate_filename("テストナレッジ")
    assert result == "テストナレッジ"


def test_generate_filename_english():
    """英語タイトルがそのままファイル名になる"""
    result = generate_filename("Test Knowledge")
    assert result == "Test Knowledge"


def test_generate_filename_removes_unsafe_chars():
    """危険な文字が除去される"""
    result = generate_filename("test/path:file*name?\"<>|")
    assert "/" not in result
    assert ":" not in result
    assert "*" not in result
    assert "?" not in result
    assert '"' not in result
    assert "<" not in result
    assert ">" not in result
    assert "|" not in result


def test_generate_filename_replaces_with_underscore():
    """危険な文字がアンダースコアに置換される"""
    result = generate_filename("test/file")
    assert result == "test_file"


def test_generate_filename_removes_newlines():
    """改行文字が除去される"""
    result = generate_filename("test\ntitle\r\n")
    assert "\n" not in result
    assert "\r" not in result


def test_generate_filename_strips_whitespace():
    """前後の空白がトリムされる"""
    result = generate_filename("  test title  ")
    assert result == "test title"


# ========================================
# get_unique_filepath のテスト
# ========================================


def test_get_unique_filepath_no_conflict(temp_knowledge_root):
    """衝突がない場合はそのままのファイル名を返す"""
    directory = temp_knowledge_root / "references"
    directory.mkdir(parents=True, exist_ok=True)

    result = get_unique_filepath(directory, "test")
    assert result == directory / "test.md"


def test_get_unique_filepath_with_conflict(temp_knowledge_root):
    """衝突がある場合は連番を付与する"""
    directory = temp_knowledge_root / "references"
    directory.mkdir(parents=True, exist_ok=True)

    # 既存ファイルを作成
    (directory / "test.md").write_text("existing")

    result = get_unique_filepath(directory, "test")
    assert result == directory / "test_1.md"


def test_get_unique_filepath_multiple_conflicts(temp_knowledge_root):
    """複数の衝突がある場合は適切な連番を付与する"""
    directory = temp_knowledge_root / "references"
    directory.mkdir(parents=True, exist_ok=True)

    # 既存ファイルを複数作成
    (directory / "test.md").write_text("existing")
    (directory / "test_1.md").write_text("existing")
    (directory / "test_2.md").write_text("existing")

    result = get_unique_filepath(directory, "test")
    assert result == directory / "test_3.md"


# ========================================
# create_frontmatter のテスト
# ========================================


def test_create_frontmatter_with_tags():
    """タグ付きのフロントマターを生成できる"""
    result = create_frontmatter(["tag1", "tag2"])

    assert "---" in result
    assert "tags:" in result
    assert "  - tag1" in result
    assert "  - tag2" in result
    assert "created_at:" in result


def test_create_frontmatter_empty_tags():
    """空のタグでもフロントマターを生成できる"""
    result = create_frontmatter([])

    assert "---" in result
    assert "tags: []" in result
    assert "created_at:" in result


def test_create_frontmatter_format():
    """YAMLフロントマターの形式が正しい"""
    result = create_frontmatter(["test"])

    lines = result.strip().split("\n")
    assert lines[0] == "---"
    assert lines[-1] == "---"


# ========================================
# add_knowledge のテスト
# ========================================


def test_add_knowledge_creates_file(temp_knowledge_root):
    """ナレッジファイルを作成できる"""
    result = add_knowledge(
        title="テストナレッジ",
        content="# テスト\n\nこれはテストです。",
        tags=["test", "sample"],
        category="references",
    )

    assert "error" not in result
    assert "file_path" in result
    assert result["title"] == "テストナレッジ"
    assert result["category"] == "references"
    assert result["tags"] == ["test", "sample"]

    # ファイルが実際に存在することを確認
    filepath = Path(result["file_path"])
    assert filepath.exists()


def test_add_knowledge_file_content(temp_knowledge_root):
    """ファイル内容が正しい"""
    result = add_knowledge(
        title="テスト",
        content="# 内容\n\n本文です。",
        tags=["tag1"],
        category="references",
    )

    filepath = Path(result["file_path"])
    content = filepath.read_text(encoding="utf-8")

    # フロントマターがある
    assert content.startswith("---")
    assert "tags:" in content
    assert "  - tag1" in content
    assert "created_at:" in content

    # 本文がある
    assert "# 内容" in content
    assert "本文です。" in content


def test_add_knowledge_references_category(temp_knowledge_root):
    """referencesカテゴリで正しいディレクトリに保存される"""
    result = add_knowledge(
        title="外部情報",
        content="content",
        tags=[],
        category="references",
    )

    assert "references" in result["file_path"]


def test_add_knowledge_facts_category(temp_knowledge_root):
    """factsカテゴリで正しいディレクトリに保存される"""
    result = add_knowledge(
        title="コードベース情報",
        content="content",
        tags=[],
        category="facts",
    )

    assert "facts" in result["file_path"]


def test_add_knowledge_invalid_category(temp_knowledge_root):
    """無効なカテゴリでエラーを返す"""
    result = add_knowledge(
        title="test",
        content="content",
        tags=[],
        category="invalid",
    )

    assert "error" in result
    assert result["error"]["code"] == "INVALID_CATEGORY"


def test_add_knowledge_empty_title(temp_knowledge_root):
    """空のタイトルでエラーを返す"""
    result = add_knowledge(
        title="",
        content="content",
        tags=[],
        category="references",
    )

    assert "error" in result
    assert result["error"]["code"] == "INVALID_TITLE"


def test_add_knowledge_special_chars_converted_to_underscores(temp_knowledge_root):
    """特殊文字のみのタイトルはアンダースコアに変換されてファイルが作成される"""
    result = add_knowledge(
        title="///",
        content="content",
        tags=[],
        category="references",
    )

    # アンダースコアに変換されてファイルが作成される
    assert "error" not in result
    assert "___.md" in result["file_path"]


def test_add_knowledge_filename_collision(temp_knowledge_root):
    """同名ファイルが存在する場合は連番が付く"""
    # 1つ目を作成
    result1 = add_knowledge(
        title="重複テスト",
        content="content1",
        tags=[],
        category="references",
    )

    # 2つ目を作成（同名）
    result2 = add_knowledge(
        title="重複テスト",
        content="content2",
        tags=[],
        category="references",
    )

    assert "error" not in result1
    assert "error" not in result2
    assert result1["file_path"] != result2["file_path"]
    assert "_1.md" in result2["file_path"]


def test_add_knowledge_japanese_filename(temp_knowledge_root):
    """日本語タイトルでファイルが作成される"""
    result = add_knowledge(
        title="日本語タイトルのナレッジ",
        content="content",
        tags=[],
        category="references",
    )

    assert "error" not in result
    assert "日本語タイトルのナレッジ.md" in result["file_path"]


# ========================================
# KnowledgeCategory のテスト
# ========================================


def test_knowledge_category_values():
    """カテゴリの値が正しい"""
    assert KnowledgeCategory.REFERENCES.value == "references"
    assert KnowledgeCategory.FACTS.value == "facts"


def test_knowledge_category_from_string():
    """文字列からカテゴリを取得できる"""
    assert KnowledgeCategory("references") == KnowledgeCategory.REFERENCES
    assert KnowledgeCategory("facts") == KnowledgeCategory.FACTS
