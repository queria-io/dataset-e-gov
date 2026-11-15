{# 法令本文を条ごとに分けた行。法令履歴と条の順に並べる #}

select s.* exclude (source_path), f.sha256 as source_sha256
from {{ ref('stg_articles') }} as s
left join {{ ref('stg_source_file') }} as f on list_contains(f.paths, s.source_path)
order by s.law_revision_id, s.position
