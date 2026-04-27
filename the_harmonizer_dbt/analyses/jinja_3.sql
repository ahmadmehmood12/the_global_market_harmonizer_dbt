{% set inc_flag = 1 %}

{% set last_load = 3 %}

{% set col_list=["sales_id","date_sk"] %}


SELECT
{% for col in col_list %}
  {{col}}
  {% if not loop.last %},{% endif %}
{% endfor %}
FROM {{ ref('bronze_sales') }}

{% if inc_flag == 1 %}

    where date_sk > {{ last_load }}
  
{% endif %}
