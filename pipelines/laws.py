"""e-Gov 法令 API (Version 2) から、法令の一覧と法令ごとの履歴を取り出す。

1. 法令一覧取得 API (/laws) で、廃止したものも含むすべての法令を 1 回で取る
2. 法令履歴一覧取得 API (/law_revisions/{law_id}) を法令ごとに呼び、改正の履歴を取る

出力:
- data/laws/laws.json: 法令一覧取得 API の応答
- data/revisions/revisions.jsonl: 1 行が 1 法令の法令履歴一覧取得 API の応答

データソース: e-Gov 法令 API Version 2
https://laws.e-gov.go.jp/api/2/swagger-ui
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from shared.fetch import fetch, replacing, write_atomic

logger = logging.getLogger("pipelines")

API = "https://laws.e-gov.go.jp/api/2"
USER_AGENT = "dataset-e-gov (+https://github.com/queria-io/dataset-e-gov)"
LAWS = Path("data/laws/laws.json")
REVISIONS = Path("data/revisions/revisions.jsonl")
# 法令は 1 万件ほど。limit を全件より大きくして 1 回で取る
LIMIT = 100_000
# 履歴は法令ごとに 1 回呼ぶ。配信元に負荷をかけないよう同時に 4 本まで
WORKERS = 4


def get_json(path: str) -> dict:
    return json.loads(fetch(f"{API}{path}", user_agent=USER_AGENT))


def download_laws() -> list[str]:
    """法令の一覧を書き、法令 ID の一覧を返す。"""
    body = get_json(f"/laws?limit={LIMIT}")
    if body["count"] != body["total_count"] or body["count"] == 0:
        raise SystemExit(f"法令一覧が全件取れていない: {body['count']} / {body['total_count']}")
    LAWS.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(LAWS, json.dumps(body, ensure_ascii=False))
    logger.info("  %d 法令", body["count"])
    return [law["law_info"]["law_id"] for law in body["laws"]]


def download_revisions(law_ids: list[str]) -> None:
    REVISIONS.parent.mkdir(parents=True, exist_ok=True)
    with (
        replacing(REVISIONS) as partial,
        partial.open("w", encoding="utf-8") as handle,
        ThreadPoolExecutor(WORKERS) as pool,
    ):
        for done, body in enumerate(pool.map(lambda i: get_json(f"/law_revisions/{i}"), law_ids), 1):
            handle.write(json.dumps(body, ensure_ascii=False) + "\n")
            if done % 1000 == 0:
                logger.info("  %d / %d", done, len(law_ids))
