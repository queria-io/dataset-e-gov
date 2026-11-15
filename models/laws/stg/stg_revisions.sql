{# 法令履歴の属性を取り出して型付けする。
   法令履歴は、新規制定・改正・廃止のたびにできる法令のその時点の版 #}

select
    revision.law_revision_id,
    law_info.law_id,
    revision.law_type,
    revision.law_title,
    revision.law_title_kana,
    revision.abbrev,
    revision.category,
    cast(revision.amendment_promulgate_date as date) as amendment_promulgate_date,
    cast(revision.amendment_enforcement_date as date) as amendment_enforcement_date,
    revision.amendment_enforcement_comment,
    cast(revision.amendment_scheduled_enforcement_date as date) as amendment_scheduled_enforcement_date,
    revision.amendment_law_id,
    revision.amendment_law_num,
    revision.amendment_law_title,
    nullif(revision.amendment_law_title_kana, '') as amendment_law_title_kana,
    revision.amendment_type,
    revision.mission,
    revision.repeal_status,
    cast(revision.repeal_date as date) as repeal_date,
    revision.remain_in_force,
    revision.current_revision_status,
    cast(revision.updated as timestamptz) as updated_at
from {{ ref('raw_revisions') }}
