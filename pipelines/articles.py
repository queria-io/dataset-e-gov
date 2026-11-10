"""e-Gov 法令検索の XML 一括ダウンロードから、法令本文を条ごとの行にする。

すべての法令データ (all_xml.zip) には、現行の法令と、施行日が来ていない改正後の法令が
法令履歴ごとに 1 つの XML で入っている。本則 (MainProvision) と附則 (SupplProvision) の
条 (Article) を 1 行にする。条の無い本則・附則は、項 (Paragraph) をまとめて 1 行にする。

出力: data/articles/articles.jsonl

データソース: e-Gov 法令検索 XML 一括ダウンロード
https://laws.e-gov.go.jp/bulkdownload/
"""

import io
import json
import logging
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Iterator
from pathlib import Path

from shared.fetch import download, replacing

logger = logging.getLogger("pipelines")

URL = "https://laws.e-gov.go.jp/bulkdownload?file_section=1&only_xml_flag=true"
USER_AGENT = "dataset-e-gov (+https://github.com/queria-io/dataset-e-gov)"
ARCHIVE = Path("data/all_xml.zip")
OUTPUT = Path("data/articles/articles.jsonl")

# 編・章・節・款・目。条の見出しの上に並ぶ
HEADINGS = {"Part", "Chapter", "Section", "Subsection", "Division"}
# 項の下の号と細分。号・イロハ・(1)(2)… の順に深くなる
ITEMS = {"Item"} | {f"Subitem{n}" for n in range(1, 11)}
# 本文に入れないもの。目次は条の本文と重なり、ルビは読みが本文に混ざる
SKIP = {"Rt", "TOC"}


def text(element: ET.Element) -> str:
    """要素の文字を、ルビの読みを除いてつなぐ。"""
    if element.tag in SKIP:
        return element.tail or ""
    inner = "".join(text(child) for child in element)
    return (element.text or "") + inner + (element.tail or "")


def direct_text(element: ET.Element, *tags: str) -> str:
    """子のうち tags の要素の文字を空白でつなぐ。"""
    return " ".join(
        value for child in element if child.tag in tags and (value := text(child).strip())
    )


def lines(element: ET.Element, title_tag: str) -> Iterator[str]:
    """項・号・細分を 1 行ずつ返す。行頭に項番号や号名を付ける。"""
    head = direct_text(element, title_tag)
    body = " ".join(
        text(child).strip()
        for child in element
        if child.tag not in ITEMS and child.tag not in (title_tag, "ParagraphCaption")
    )
    line = " ".join(part for part in (head, body) if part)
    if line:
        yield line
    for child in element:
        if child.tag in ITEMS:
            yield from lines(child, f"{child.tag}Title")


def paragraphs_text(paragraphs: list[ET.Element]) -> str:
    return "\n".join(
        line for paragraph in paragraphs for line in lines(paragraph, "ParagraphNum")
    )


def articles(provision: ET.Element, headings: tuple[str, ...] = ()) -> Iterator[dict]:
    """本則・附則の中の条を、上に並ぶ章などの見出しと一緒に返す。"""
    loose = [child for child in provision if child.tag == "Paragraph"]
    if loose:
        yield {"headings": list(headings), "text": paragraphs_text(loose)}
    for child in provision:
        if child.tag in HEADINGS:
            title = direct_text(child, f"{child.tag}Title")
            yield from articles(child, headings + ((title,) if title else ()))
        elif child.tag == "Article":
            yield {
                "headings": list(headings),
                "article_num": child.get("Num"),
                "article_title": direct_text(child, "ArticleTitle") or None,
                "caption": direct_text(child, "ArticleCaption") or None,
                "text": paragraphs_text([p for p in child if p.tag == "Paragraph"]),
            }


def law_rows(law_revision_id: str, root: ET.Element) -> Iterator[dict]:
    body = root.find("LawBody")
    if body is None:
        raise SystemExit(f"LawBody が無い: {law_revision_id}")
    position = 0
    for provision in body:
        if provision.tag == "MainProvision":
            kind, amend_law_num = "main", None
        elif provision.tag == "SupplProvision":
            kind, amend_law_num = "suppl", provision.get("AmendLawNum")
        else:
            continue
        for row in articles(provision):
            position += 1
            yield {
                "law_revision_id": law_revision_id,
                "provision": kind,
                "amend_law_num": amend_law_num,
                "position": position,
                **row,
            }


def write_articles(archive: Path, output: Path) -> int:
    count = 0
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle, replacing(output) as partial:
        with partial.open("w", encoding="utf-8") as handle:
            for member in bundle.namelist():
                if not member.endswith(".xml"):
                    continue
                law_revision_id = Path(member).stem
                root = ET.parse(io.BytesIO(bundle.read(member))).getroot()
                for row in law_rows(law_revision_id, root):
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                    count += 1
        if count == 0:
            raise SystemExit("条が 1 つも取れない")
    return count


def download_articles() -> None:
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    size = download(URL, ARCHIVE, user_agent=USER_AGENT, timeout=600)
    logger.info("  all_xml.zip: %d bytes", size)
    logger.info("  %d 条", write_articles(ARCHIVE, OUTPUT))
