"""取得したファイルの記録 (source_file) を Parquet に書く。

1 行が 1 つの取得ファイル。shared.fetch.fetch_file が返す行に、そのファイルから作った手元のファイル
(paths) と、掲載ページの URL (page_url) を足して書く。dbt の raw が読む。
"""

import json
from pathlib import Path

import duckdb

COLUMNS = {
    "url": "VARCHAR",
    "page_url": "VARCHAR",
    "sha256": "VARCHAR",
    "bytes": "BIGINT",
    "media_type": "VARCHAR",
    "retrieved_at": "VARCHAR",
    "etag": "VARCHAR",
    "last_modified": "VARCHAR",
    "paths": "VARCHAR[]",
}


def write_source_files(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = path.with_suffix(".jsonl")
    lines.write_text("".join(json.dumps({c: r.get(c) for c in COLUMNS}, ensure_ascii=False) + "\n" for r in rows))
    con = duckdb.connect()
    con.execute(f"copy (select * from read_json('{lines}', format = 'newline_delimited', columns = {COLUMNS})) to '{path}'")
    con.close()
    lines.unlink()
