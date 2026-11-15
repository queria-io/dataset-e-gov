{# 法令本文を条ごとに分けた行 (data/articles/articles.jsonl、pipelines/articles.py が作る)。取得したままの形 #}

select *
from read_json(
    'data/articles/articles.jsonl',
    format = 'newline_delimited',
    filename = true,
    columns = {
        'law_revision_id': 'VARCHAR',
        'provision': 'VARCHAR',
        'amend_law_num': 'VARCHAR',
        'position': 'INTEGER',
        'url': 'VARCHAR',
        'headings': 'VARCHAR[]',
        'article_num': 'VARCHAR',
        'article_title': 'VARCHAR',
        'caption': 'VARCHAR',
        'text': 'VARCHAR'
    }
)
