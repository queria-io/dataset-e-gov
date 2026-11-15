{# 取得したファイルの記録を型付けする。paths はそのファイルから作った手元のファイルで、各テーブルの行と結び付けるのに使う #}

select
    url,
    page_url,
    sha256,
    bytes,
    media_type,
    cast(retrieved_at as timestamptz) as retrieved_at,
    etag,
    last_modified,
    paths
from {{ ref('raw_source_file') }}
