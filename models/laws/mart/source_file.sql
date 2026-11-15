{# 取得したファイルの一覧。1 行が 1 つのファイル #}

select * exclude (paths)
from {{ ref('stg_source_file') }}
order by url
