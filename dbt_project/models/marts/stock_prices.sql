{{
  config(
    materialized = 'table',
  )
}}

-- Deduplicate staging.stock_prices by (date, symbol); keep one row per day per symbol.
-- Incremental loads can create duplicates; this table is the single source of truth for analytics.
with source_data as (
    select * from {{ source('staging', 'stock_prices') }}
),

deduped as (
    select
        date,
        symbol,
        open,
        high,
        low,
        close,
        adj_close,
        volume,
        row_number() over (partition by date, symbol order by date, symbol) as rn
    from source_data
)

select
    date,
    symbol,
    open,
    high,
    low,
    close,
    adj_close,
    volume
from deduped
where rn = 1
order by date desc, symbol
