{# Block Level Configuration  #}

{{
  config(
    materialized = 'view',
    )
}}

SELECT 
   *
FROM {{ source('source','fact_sales') }}


{# we can also write like this but best practice is to get it from source using jinja function  #}
{# select * from dbt_tutorial_dev.source.fact_sales #}