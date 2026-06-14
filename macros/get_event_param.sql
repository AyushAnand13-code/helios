-- macros/get_event_param.sql
{% macro get_event_param(key, type='string') %}
    {%- set slot = {
        'string': 'string_value',
        'int':    'int_value',
        'float':  'float_value',
        'double': 'double_value'
    } -%}
    (
        select ep.value.{{ slot[type] }}
        from unnest(event_params) as ep
        where ep.key = '{{ key }}'
        limit 1
    )
{% endmacro %}
