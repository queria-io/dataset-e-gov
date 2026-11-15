{# 条ごとの行に法令 ID を付ける #}

select
    law_revision_id,
    split_part(law_revision_id, '_', 1) as law_id,
    position,
    provision,
    amend_law_num,
    url,
    headings,
    article_num,
    article_title,
    caption,
    text
from {{ ref('raw_articles') }}
