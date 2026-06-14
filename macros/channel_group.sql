-- macros/channel_group.sql
{% macro channel_group(source_col='source', medium_col='medium', gclid_col='gclid') %}
  {{ return(channel_group_case(source_col, medium_col, gclid_col)) }}
{% endmacro %}

{% macro channel_group_case(source_col='source', medium_col='medium', gclid_col='gclid') %}
case
    -- Direct: no/(direct)/(none) source and (none)/(not set) medium
    when ( {{ source_col }} is null or lower({{ source_col }}) in ('(direct)','direct') )
         and ( {{ medium_col }} is null or lower({{ medium_col }}) in ('(none)','(not set)') )
        then 'Direct'

    -- Paid Search: gclid present, OR known search source on a paid medium
    when {{ gclid_col }} is not null
         or ( regexp_contains(lower({{ source_col }}), r'google|bing|yahoo|duckduckgo|baidu|yandex|ecosia')
              and regexp_contains(lower({{ medium_col }}), r'^(.*cp.*|ppc|paid|retargeting)$') )
        then 'Paid Search'

    -- Paid Social: known social source on a paid medium
    when regexp_contains(lower({{ source_col }}), r'facebook|instagram|tiktok|twitter|x\.com|linkedin|pinterest|reddit|snapchat')
         and regexp_contains(lower({{ medium_col }}), r'^(.*cp.*|ppc|paid|social-paid|retargeting)$')
        then 'Paid Social'

    -- Display: banner/display/cpm/expandable/interstitial mediums
    when regexp_contains(lower({{ medium_col }}), r'^(display|banner|cpm|expandable|interstitial)$')
        then 'Display'

    -- Organic Search: search engines on organic medium
    when regexp_contains(lower({{ source_col }}), r'google|bing|yahoo|duckduckgo|baidu|yandex|ecosia')
         and lower({{ medium_col }}) = 'organic'
        then 'Organic Search'

    -- Organic Social: social sources, organic/social/referral medium
    when regexp_contains(lower({{ source_col }}), r'facebook|instagram|tiktok|twitter|x\.com|linkedin|pinterest|reddit|snapchat|youtube')
         and lower({{ medium_col }}) in ('social','social-network','social-media','sm','organic','referral')
        then 'Organic Social'

    -- Email
    when lower({{ source_col }}) = 'email'
         or regexp_contains(lower({{ medium_col }}), r'^e?-?mail$')
        then 'Email'

    -- Affiliates
    when lower({{ medium_col }}) = 'affiliate'
        then 'Affiliates'

    -- Referral: any explicit referral medium not caught above
    when lower({{ medium_col }}) in ('referral','link')
        then 'Referral'

    -- Everything else
    else 'Other'
end
{% endmacro %}
