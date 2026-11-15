{# 法令履歴一覧取得 API の応答 (data/revisions/revisions.jsonl)。
   応答の revisions の配列を 1 要素 1 行に開くほかは、取得したままの形 #}

select law_info, unnest(revisions) as revision
from read_json(
    'data/revisions/revisions.jsonl',
    format = 'newline_delimited',
    maximum_object_size = 268435456
)
