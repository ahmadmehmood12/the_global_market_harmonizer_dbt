SELECT 
   *
FROM {{ source('source','exchange_rates') }}


{# we can also write like this but best practice is to get it from source using jinja function  #}
{# select * from dbt_tutorial_dev.source.dim_product #}