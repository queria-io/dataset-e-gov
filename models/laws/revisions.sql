{# 法令履歴一覧取得 API の応答 (data/revisions/revisions.jsonl) を、1 行が 1 法令履歴の表にする。
   法令履歴は、新規制定・改正・廃止のたびにできる法令のその時点の版 #}

with source as (
    select law_info.law_id, unnest(revisions) as revision
    from read_json(
        'data/revisions/revisions.jsonl',
        format = 'newline_delimited',
        maximum_object_size = 268435456
    )
)

select
    revision.law_revision_id,
    law_id,
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
from source
