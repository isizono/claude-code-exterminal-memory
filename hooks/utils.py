#!/usr/bin/env python3
"""
hooks共通ユーティリティ
"""
from __future__ import annotations

import json
import re


def extract_json_from_text(text: str) -> dict | list | None:
    """
    テキストからJSONオブジェクトまたは配列を抽出する。

    対応パターン:
    1. ```json ... ``` で囲まれたJSON
    2. テキスト中の { ... } または [ ... ]

    ネストされたJSONにも対応。

    Args:
        text: JSONを含む可能性のあるテキスト

    Returns:
        パースされたJSONオブジェクト/配列、または None（抽出失敗時）
    """
    if not text:
        return None

    text = text.strip()

    # 1. ```json ... ``` ブロックを探す
    code_block_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if code_block_match:
        json_str = code_block_match.group(1).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass  # フォールバックへ

    # 2. JSONDecoder.raw_decode() でテキスト中のJSONを探す
    decoder = json.JSONDecoder()

    # { または [ の位置を探す
    for i, char in enumerate(text):
        if char in '{[':
            try:
                obj, _ = decoder.raw_decode(text, i)
                return obj
            except json.JSONDecodeError:
                continue  # 次の候補を探す

    return None
