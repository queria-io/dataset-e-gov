{# 取得したファイルの記録 (data/articles/source_file.parquet、pipelines/source_file.py が書く)。取得したままの形 #}

select * from read_parquet('data/articles/source_file.parquet')
