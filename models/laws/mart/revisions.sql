{# 1 行が 1 法令履歴 #}

select * from {{ ref('stg_revisions') }}
