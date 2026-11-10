-- 条の行は法令履歴の中の並び順 (position) で一意
select law_revision_id, position
from {{ ref('articles') }}
group by all
having count(*) > 1
