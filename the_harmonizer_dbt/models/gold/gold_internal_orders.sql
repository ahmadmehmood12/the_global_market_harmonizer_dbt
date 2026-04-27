SELECT 
   *
FROM {{ source('source','dim_date') }}


{# we can also write like this but best practice is to get it from source using jinja function  #}
{# select * from dbt_tutorial_dev.source.dim_date #}