{# 1 行が 1 法令 #}

select * from {{ ref('stg_laws') }}
