-- macros/sessionize.sql
{% macro sessionize(user_col='user_pseudo_id', session_id_col='ga_session_id') %}
    to_hex(md5(concat(
        {{ user_col }}, '-', cast({{ session_id_col }} as string)
    )))
{% endmacro %}
