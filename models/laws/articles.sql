{# 法令本文を条ごとに分けた行 (data/articles/articles.jsonl、pipelines/articles.py が作る) を型付けする #}

select
    law_revision_id,
    split_part(law_revision_id, '_', 1) as law_id,
    position,
    provision,
    amend_law_num,
    headings,
    article_num,
    article_title,
    caption,
    text
from read_json(
    'data/articles/articles.jsonl',
    format = 'newline_delimited',
    columns = {
        'law_revision_id': 'VARCHAR',
        'provision': 'VARCHAR',
        'amend_law_num': 'VARCHAR',
        'position': 'INTEGER',
        'headings': 'VARCHAR[]',
        'article_num': 'VARCHAR',
        'article_title': 'VARCHAR',
        'caption': 'VARCHAR',
        'text': 'VARCHAR'
    }
)
order by law_revision_id, position
