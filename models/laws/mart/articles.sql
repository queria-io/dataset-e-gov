{# 法令本文を条ごとに分けた行。法令履歴と条の順に並べる #}

select * from {{ ref('stg_articles') }}
order by law_revision_id, position
