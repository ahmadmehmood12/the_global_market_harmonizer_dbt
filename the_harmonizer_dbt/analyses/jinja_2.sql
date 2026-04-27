{% set apples = ['a','b','c'] %}

{% for i in apples %}
    {% if i != b %}
      {{ i }}
    {% else %}
      {{ i }} is in else
    {% endif %}
{% endfor %}