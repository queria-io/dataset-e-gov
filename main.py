"""e-Gov 法令検索の法令データのパイプライン。

1. laws: 法令一覧と、法令ごとの改正の履歴を法令 API から取り出す
2. articles: XML 一括ダウンロードから法令本文を条ごとの行にする
3. dbt: dbt ビルド
"""

import logging

from dbt.cli.main import dbtRunner

from pipelines.articles import download_articles
from pipelines.laws import download_laws, download_revisions

# dbt を読み込むとルートロガーが先に設定されるので、force で上書きする
logging.basicConfig(level=logging.INFO, format="%(message)s", force=True)
logger = logging.getLogger("pipelines")


def dbt_build():
    dbt = dbtRunner()
    for command in (["deps"], ["build"], ["docs", "generate"]):
        if not dbt.invoke(command).success:
            raise SystemExit(f"dbt {' '.join(command)} failed")


def download() -> None:
    logger.info("1/3: laws (法令一覧と改正の履歴)")
    download_revisions(download_laws())

    logger.info("2/3: articles (法令本文)")
    download_articles()


def main():
    download()
    logger.info("3/3: dbt build")
    dbt_build()


if __name__ == "__main__":
    main()
