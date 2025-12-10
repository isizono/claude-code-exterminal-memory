# SQLite Row Factory

## 概要

`sqlite3.Row`は、SQLiteのクエリ結果を辞書ライクにアクセスできるようにするrow factoryである。デフォルトではタプルとして返される結果を、カラム名でアクセス可能にする。

## 使い方

```python
import sqlite3

conn = sqlite3.connect('example.db')
conn.row_factory = sqlite3.Row  # Row factoryを設定

cursor = conn.execute("SELECT id, name FROM users")
row = cursor.fetchone()

# カラム名でアクセス可能
print(row['id'])    # カラム名でアクセス
print(row['name'])  # カラム名でアクセス

# インデックスでもアクセス可能（後方互換性）
print(row[0])  # id
print(row[1])  # name
```

## メリット

### 1. 可読性の向上

タプルのインデックスアクセスよりも、カラム名でのアクセスのほうが意図が明確である。

```python
# ❌ タプルの場合（わかりにくい）
user = cursor.fetchone()
name = user[1]  # これは何のカラム？

# ✅ Row factoryの場合（わかりやすい）
user = cursor.fetchone()
name = user['name']  # nameカラムだと明確
```

### 2. カラム順序の変更に強い

SELECT文のカラム順序を変更しても、カラム名でアクセスしていれば影響を受けない。

```python
# SELECT文を "SELECT id, name, email" から "SELECT name, id, email" に変更した場合
# タプルアクセスだとバグになるが、カラム名アクセスなら問題なし
```

### 3. 辞書への変換が容易

必要に応じて辞書に変換できる。

```python
row = cursor.fetchone()
user_dict = dict(row)  # 辞書に変換
```

## 本プロジェクトでの使用例

`src/db.py:25`で設定している。

```python
def get_connection() -> sqlite3.Connection:
    """データベース接続を取得する"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # 辞書ライクなアクセスを可能にする
    return conn
```

これにより、以下のような使い方が可能になる。

```python
# プロジェクト情報を取得
rows = execute_query("SELECT * FROM projects WHERE id = ?", (project_id,))
if rows:
    project = rows[0]
    print(project['name'])        # カラム名でアクセス
    print(project['description']) # カラム名でアクセス
```

## 注意点

### パフォーマンス

Row factoryを使うと、わずかなオーバーヘッドが発生する。ただし、本プロジェクトのようなローカルDBでの使用では問題にならない。

### 型の扱い

`sqlite3.Row`は`dict`型ではなく、dict-likeなオブジェクトである。完全な辞書として扱いたい場合は`dict(row)`で変換する。

```python
row = cursor.fetchone()
type(row)        # <class 'sqlite3.Row'>
type(dict(row))  # <class 'dict'>
```

## 参考リンク

- [Python公式ドキュメント - sqlite3.Row](https://docs.python.org/3/library/sqlite3.html#sqlite3.Row)
