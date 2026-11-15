{# 法令一覧取得 API の応答 (data/laws/laws.json)。応答の laws の配列を 1 要素 1 行に開くほかは、取得したままの形 #}

select unnest(laws, max_depth := 2)
from read_json('data/laws/laws.json', maximum_object_size = 1073741824)
