{{ config(severity = 'warn') }}
-- 本文のある法令履歴が、法令履歴の一覧にあるか。
-- 施行日が政令で定める日の改正は、XML 一括ダウンロードに仮の施行日 (2117-12-31 など) の
-- 法令履歴で入り、法令履歴一覧取得 API に無いことがある (2026-11 時点で 6 件)。
-- 配信元の差なので止めずに警告にする
select distinct a.law_revision_id
from {{ ref('articles') }} as a
anti join {{ ref('revisions') }} as r using (law_revision_id)
