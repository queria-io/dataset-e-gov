{# 法令一覧の属性を取り出して型付けする。法令の属性は、今日の時点で施行されている法令履歴 (revision_info) の値 #}

select
    law_info.law_id,
    law_info.law_num,
    law_info.law_type,
    law_info.law_num_era,
    law_info.law_num_year,
    law_info.law_num_type,
    law_info.law_num_num,
    cast(law_info.promulgation_date as date) as promulgation_date,
    revision_info.law_title,
    revision_info.law_title_kana,
    revision_info.abbrev,
    revision_info.category,
    revision_info.law_revision_id,
    cast(revision_info.amendment_enforcement_date as date) as amendment_enforcement_date,
    revision_info.amendment_law_id,
    revision_info.amendment_law_num,
    revision_info.amendment_law_title,
    revision_info.repeal_status,
    cast(revision_info.repeal_date as date) as repeal_date,
    revision_info.current_revision_status,
    cast(revision_info.updated as timestamptz) as updated_at
from {{ ref('raw_laws') }}
