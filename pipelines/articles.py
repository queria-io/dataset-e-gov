"""e-Gov 法令検索の XML 一括ダウンロードから、法令本文を条ごとの行にする。

すべての法令データ (all_xml.zip) には、現行の法令と、施行日が来ていない改正後の法令が
法令履歴ごとに 1 つの XML で入っている。本則 (MainProvision) と附則 (SupplProvision) の
条 (Article) を 1 行にする。条の無い本則・附則は、項 (Paragraph) をまとめて 1 行にする。

各行には、e-Gov 法令検索でその条を開く URL を付ける。URL は法令履歴のページに、条の要素の
id (例 Mp-Pa_1-Ch_5-Se_1-At_90) をアンカーで付けたもの。附則の id は改正法令の法令 ID で始まるので、
附則の改正法令番号を、法令一覧 (data/laws/laws.json) の法令番号と法令履歴一覧
(data/revisions/revisions.jsonl) の改正法令番号に照合して法令 ID を引く。一部改正法は法令一覧に無く、
法令履歴の改正法令にだけ現れる。どちらにも無い法律・政令は、法令番号から法令 ID を作る。

出力: data/articles/articles.jsonl

データソース: e-Gov 法令検索 XML 一括ダウンロード
https://laws.e-gov.go.jp/bulkdownload/
"""

import io
import json
import logging
import re
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Iterator
from pathlib import Path

from shared.fetch import download, replacing

logger = logging.getLogger("pipelines")

URL = "https://laws.e-gov.go.jp/bulkdownload?file_section=1&only_xml_flag=true"
USER_AGENT = "dataset-e-gov (+https://github.com/queria-io/dataset-e-gov)"
ARCHIVE = Path("data/all_xml.zip")
LAWS = Path("data/laws/laws.json")
REVISIONS = Path("data/revisions/revisions.jsonl")
OUTPUT = Path("data/articles/articles.jsonl")
LAW_URL = "https://laws.e-gov.go.jp/law"

# 編・章・節・款・目。条の見出しの上に並ぶ
# 値は e-Gov 法令検索のページで要素の id に使う略号
HEADINGS = {
    "Part": "Pa",
    "Chapter": "Ch",
    "Section": "Se",
    "Subsection": "Ss",
    "Division": "Di",
}
# 項の下の号と細分。号・イロハ・(1)(2)… の順に深くなる
ITEMS = {"Item"} | {f"Subitem{n}" for n in range(1, 11)}
# 本文に入れないもの。目次は条の本文と重なり、ルビは読みが本文に混ざる
SKIP = {"Rt", "TOC"}

ERAS = {"明治": "1", "大正": "2", "昭和": "3", "平成": "4", "令和": "5"}
DIGITS = {c: i for i, c in enumerate("〇一二三四五六七八九")}
UNITS = {"十": 10, "百": 100, "千": 1000}
NUMERAL = "[元〇一二三四五六七八九十百千]+"
# 法令番号。附則の AmendLawNum は公布日を含む (例 大正一五年四月二四日法律第六九号)
LAW_NUM = re.compile(
    rf"(明治|大正|昭和|平成|令和)({NUMERAL})年(?:{NUMERAL}月{NUMERAL}日)?(.+?)第({NUMERAL})号"
)


def kanji_number(value: str) -> int:
    """漢数字を整数にする。十百千を使う書き方 (十五) と位取りの書き方 (一五) の両方を読む。"""
    if value == "元":
        return 1
    if not any(c in UNITS for c in value):
        return int("".join(str(DIGITS[c]) for c in value))
    total, digit = 0, 0
    for c in value:
        if c in UNITS:
            total += (digit or 1) * UNITS[c]
            digit = 0
        else:
            digit = DIGITS[c]
    return total + digit


def law_num_key(law_num: str) -> tuple[str, int, str, int] | None:
    """法令番号を (元号, 年, 種別, 号) にする。書き方の違う法令番号を照合するため。"""
    match = LAW_NUM.fullmatch(law_num.strip())
    if match is None:
        return None
    era, year, kind, num = match.groups()
    return ERAS[era], kanji_number(year), kind, kanji_number(num)


def law_numbers(laws: Path, revisions: Path) -> Iterator[tuple[str | None, str | None]]:
    """法令一覧の (法令番号, 法令 ID) と、法令履歴の (改正法令番号, 改正法令の法令 ID) を返す。"""
    for law in json.loads(laws.read_text(encoding="utf-8"))["laws"]:
        yield law["law_info"]["law_num"], law["law_info"]["law_id"]
    with revisions.open(encoding="utf-8") as handle:
        for line in handle:
            for revision in json.loads(line)["revisions"]:
                yield revision["amendment_law_num"], revision["amendment_law_id"]


def law_ids_by_num(
    numbers: Iterator[tuple[str | None, str | None]],
) -> dict[tuple, str]:
    """法令番号から法令 ID を引く辞書。同じ法令番号に法令 ID が複数あるものは除く。"""
    found: dict[tuple, set[str]] = {}
    for law_num, law_id in numbers:
        if law_num and law_id and (key := law_num_key(law_num)):
            found.setdefault(key, set()).add(law_id)
    return {key: ids.pop() for key, ids in found.items() if len(ids) == 1}


# 法令 ID の種別の記号。法律と政令の法令 ID は法令番号だけで決まる (例 平成十八年法律第十号は 418AC0000000010)
NUMBERED_KINDS = {"法律": "AC", "政令": "CO"}


def law_id_from_key(key: tuple[str, int, str, int]) -> str | None:
    """法律・政令の法令番号から法令 ID を作る。府省令などは ID に府省の記号が入るので作らない。"""
    era, year, kind, num = key
    code = NUMBERED_KINDS.get(kind)
    return f"{era}{year:02d}{code}{num:010d}" if code else None


def article_url(law_revision_id: str, anchor: str | None) -> str:
    """法令履歴のページの URL。条の id が分かるときはアンカーを付ける。"""
    law_id, rest = law_revision_id.split("_", 1)
    return f"{LAW_URL}/{law_id}/{rest}" + (f"#{anchor}" if anchor else "")


def text(element: ET.Element) -> str:
    """要素の文字を、ルビの読みを除いてつなぐ。"""
    if element.tag in SKIP:
        return element.tail or ""
    inner = "".join(text(child) for child in element)
    return (element.text or "") + inner + (element.tail or "")


def direct_text(element: ET.Element, *tags: str) -> str:
    """子のうち tags の要素の文字を空白でつなぐ。"""
    return " ".join(
        value
        for child in element
        if child.tag in tags and (value := text(child).strip())
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


def articles(
    provision: ET.Element,
    headings: tuple[str, ...] = (),
    path: tuple[str, ...] | None = (),
) -> Iterator[dict]:
    """本則・附則の中の条を、上に並ぶ章などの見出しと、e-Gov のページでの id の経路と一緒に返す。
    path は Num の無い見出しの下では None にする。"""
    loose = [child for child in provision if child.tag == "Paragraph"]
    if loose:
        yield {"path": path, "headings": list(headings), "text": paragraphs_text(loose)}
    for child in provision:
        if child.tag in HEADINGS:
            title = direct_text(child, f"{child.tag}Title")
            num = child.get("Num")
            sub = (
                path + (f"{HEADINGS[child.tag]}_{num}",)
                if path is not None and num
                else None
            )
            yield from articles(child, headings + ((title,) if title else ()), sub)
        elif child.tag == "Article":
            num = child.get("Num")
            yield {
                "path": path + (f"At_{num}",) if path is not None and num else None,
                "headings": list(headings),
                "article_num": child.get("Num"),
                "article_title": direct_text(child, "ArticleTitle") or None,
                "caption": direct_text(child, "ArticleCaption") or None,
                "text": paragraphs_text([p for p in child if p.tag == "Paragraph"]),
            }


def provision_id(
    provision: ET.Element, law_id: str, law_ids: dict[tuple, str]
) -> str | None:
    """本則・附則の要素の e-Gov のページでの id。原始附則は法令自身の、改正附則は改正法令の法令 ID で始まる。"""
    if provision.tag == "MainProvision":
        return "Mp"
    amend_law_num = provision.get("AmendLawNum")
    if amend_law_num is None:
        return f"{law_id}-Sp"
    key = law_num_key(amend_law_num)
    amend_law_id = (law_ids.get(key) or law_id_from_key(key)) if key else None
    return f"{amend_law_id}-Sp" if amend_law_id else None


def law_rows(
    law_revision_id: str, root: ET.Element, law_ids: dict[tuple, str]
) -> Iterator[dict]:
    body = root.find("LawBody")
    if body is None:
        raise SystemExit(f"LawBody が無い: {law_revision_id}")
    law_id = law_revision_id.split("_", 1)[0]
    position = 0
    for provision in body:
        if provision.tag == "MainProvision":
            kind, amend_law_num = "main", None
        elif provision.tag == "SupplProvision":
            kind, amend_law_num = "suppl", provision.get("AmendLawNum")
        else:
            continue
        prefix = provision_id(provision, law_id, law_ids)
        for row in articles(provision):
            position += 1
            path = row.pop("path")
            anchor = "-".join((prefix, *path)) if prefix and path is not None else None
            yield {
                "law_revision_id": law_revision_id,
                "provision": kind,
                "amend_law_num": amend_law_num,
                "position": position,
                "url": article_url(law_revision_id, anchor),
                **row,
            }


def write_articles(archive: Path, laws: Path, revisions: Path, output: Path) -> int:
    law_ids = law_ids_by_num(law_numbers(laws, revisions))
    count = 0
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle, replacing(output) as partial:
        with partial.open("w", encoding="utf-8") as handle:
            for member in bundle.namelist():
                if not member.endswith(".xml"):
                    continue
                law_revision_id = Path(member).stem
                root = ET.parse(io.BytesIO(bundle.read(member))).getroot()
                for row in law_rows(law_revision_id, root, law_ids):
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                    count += 1
        if count == 0:
            raise SystemExit("条が 1 つも取れない")
    return count


def download_articles() -> None:
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    size = download(URL, ARCHIVE, user_agent=USER_AGENT, timeout=600)
    logger.info("  all_xml.zip: %d bytes", size)
    logger.info("  %d 条", write_articles(ARCHIVE, LAWS, REVISIONS, OUTPUT))
