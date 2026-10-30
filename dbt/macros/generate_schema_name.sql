{# Dùng thẳng tên schema của từng tầng (staging, raw_vault...), không ghép với schema của profile #}
{% macro generate_schema_name(custom_schema_name, node) -%}
  {{ (custom_schema_name or target.schema) | trim }}
{%- endmacro %}
